import asyncio, json, time, uuid
from datetime import timedelta
from typing import Optional
import jwt, redis, socketio
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select
from .auth import (check_password, current_user, hash_password, make_purpose_token,
                   make_token, read_purpose_token, require_role)
from .config import settings
from .db import get_session, init_db
from .dispatch import OFFER_SECS, RADIUS_M, dispatch_loop, dispatch_ride
from .maps import calc_fare, distance_time
from .models import Driver, Payment, Review, Ride, RideOffer, User, utcnow
from . import payments
from .realtime import sio
from .tasks import build_receipt, dispatch_receipt, queue_email

# ---------- rate limiting (Redis if available, else in memory) ----------
r = None
if settings.redis_url:
    try:
        r = redis.from_url(settings.redis_url); r.ping()
    except Exception:
        r = None
        print("Redis not reachable - using in-memory rate limiting")
_hits: dict = {}

def rate_limit(request: Request):
    host = request.client.host if request.client else "local"
    minute = int(time.time() // 60)
    if r:
        n = r.incr(f"rl:{host}:{minute}"); r.expire(f"rl:{host}:{minute}", 60)
    else:
        m, n = _hits.get(host, (minute, 0))
        n = n + 1 if m == minute else 1
        _hits[host] = (minute, n)
    if n > 600:
        raise HTTPException(429, "Too many requests")

app = FastAPI(title="Cab Booking API", dependencies=[Depends(rate_limit)])
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(dispatch_loop())     # re-dispatch + expiry worker

ACTIVE = ("requested", "accepted", "arrived", "started", "completed")
IN_TRIP = ("accepted", "arrived", "started")

# ---------- helpers ----------
def public(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "rating_avg": u.rating_avg,
            "phone": u.phone, "profile_pic": u.profile_pic, "email_verified": bool(u.email_verified)}

def ride_dict(s: Session, ride: Ride) -> dict:
    d = ride.model_dump()
    rider = s.get(User, ride.rider_id)
    d["rider_name"] = rider.name if rider else ""
    d["rider_rating"] = rider.rating_avg if rider else None
    d.update(driver_name=None, driver_phone=None, driver_rating=None, driver_vehicle=None)
    if ride.driver_id:
        du, dr = s.get(User, ride.driver_id), s.get(Driver, ride.driver_id)
        if du:
            d.update(driver_name=du.name, driver_phone=du.phone, driver_rating=du.rating_avg,
                     driver_vehicle=f"{dr.vehicle_info} {dr.vehicle_number}".strip() if dr else "")
    return d

async def notify(ride: Ride, **extra):
    payload = {"ride_id": ride.id, "status": ride.status, **extra}
    await sio.emit("ride_update", payload, room=f"user:{ride.rider_id}")
    if ride.driver_id:
        await sio.emit("ride_update", payload, room=f"user:{ride.driver_id}")

def _own_ride(s: Session, ride_id: int, user: User) -> Ride:
    ride = s.get(Ride, ride_id)
    if not ride or user.id not in (ride.rider_id, ride.driver_id):
        raise HTTPException(404, "Ride not found")
    return ride

def _driver_ride(s: Session, ride_id: int, d: User, *statuses: str) -> Ride:
    ride = s.get(Ride, ride_id)
    if not ride or ride.driver_id != d.id:
        raise HTTPException(404, "Ride not found")
    if ride.status not in statuses:
        raise HTTPException(400, f"Ride is '{ride.status}', expected {' or '.join(statuses)}")
    return ride

def free_driver(s: Session, driver_id: str):
    drv = s.get(Driver, driver_id)
    if drv and drv.status == "busy":
        drv.status = "active"; s.add(drv)

def close_offers(s: Session, ride_id: int, keep: Optional[str] = None) -> list:
    closed = []
    for o in s.exec(select(RideOffer).where(RideOffer.ride_id == ride_id,
                                            RideOffer.status == "offered")).all():
        if o.driver_id != keep:
            o.status = "expired"; s.add(o); closed.append(o.driver_id)
    return closed

# ---------- Auth ----------
class RegisterIn(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=100)
    name: str = Field(default="", max_length=80)
    role: str = Field(pattern="^(rider|driver)$")
    vehicle_info: str = Field(default="", max_length=80)
    vehicle_number: str = Field(default="", max_length=20)
    license_no: str = Field(default="", max_length=30)

class LoginIn(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
def register(b: RegisterIn, s: Session = Depends(get_session)):
    email = b.email.lower().strip()
    if "@" not in email:
        raise HTTPException(422, "Enter a valid email")
    if s.exec(select(User).where(User.email == email)).first():
        raise HTTPException(409, "Email already registered")
    u = User(id=uuid.uuid4().hex, email=email, name=b.name.strip() or email.split("@")[0],
             role=b.role, password_hash=hash_password(b.password))
    s.add(u); s.commit()
    if b.role == "driver":
        s.add(Driver(user_id=u.id, vehicle_info=b.vehicle_info, vehicle_number=b.vehicle_number,
                     license_no=b.license_no, verified=True))
        s.commit()
    link = f"{settings.frontend_url}/verify?token={make_purpose_token(u.id, 'verify', 2880)}"
    queue_email(email, "Verify your CabGo email", f"Open this link to verify your email:\n{link}")
    return {"token": make_token(u.id), "user": public(u)}

@app.post("/api/auth/login")
def login(b: LoginIn, s: Session = Depends(get_session)):
    u = s.exec(select(User).where(User.email == b.email.lower().strip())).first()
    if not u or not check_password(b.password, u.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(u.id), "user": public(u)}

@app.get("/api/auth/me")
def me(u: User = Depends(current_user)):
    return public(u)

class ForgotIn(BaseModel):
    email: str

@app.post("/api/auth/forgot")
def forgot(b: ForgotIn, s: Session = Depends(get_session)):
    u = s.exec(select(User).where(User.email == b.email.lower().strip())).first()
    if u:   # same answer either way, so nobody can probe which emails exist
        token = make_purpose_token(u.id, "reset", 30, {"pwh": u.password_hash[-12:]})
        queue_email(u.email, "Reset your CabGo password",
                    f"Open this link to choose a new password (valid 30 minutes):\n{settings.frontend_url}/reset?token={token}")
    return {"ok": True}

class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=6, max_length=100)

@app.post("/api/auth/reset")
def reset(b: ResetIn, s: Session = Depends(get_session)):
    try:
        claims = read_purpose_token(b.token, "reset")
    except jwt.PyJWTError:
        raise HTTPException(400, "Reset link is invalid or expired")
    u = s.get(User, claims["sub"])
    if not u or u.password_hash[-12:] != claims.get("pwh"):
        raise HTTPException(400, "Reset link was already used or is invalid")
    u.password_hash = hash_password(b.password)
    s.add(u); s.commit()
    return {"ok": True}

class TokenIn(BaseModel):
    token: str

@app.post("/api/auth/verify")
def verify_email(b: TokenIn, s: Session = Depends(get_session)):
    try:
        claims = read_purpose_token(b.token, "verify")
    except jwt.PyJWTError:
        raise HTTPException(400, "Verification link is invalid or expired")
    u = s.get(User, claims["sub"])
    if not u:
        raise HTTPException(404, "User not found")
    u.email_verified = True
    s.add(u); s.commit()
    return {"ok": True}

@app.post("/api/auth/send-verification")
def send_verification(u: User = Depends(current_user)):
    link = f"{settings.frontend_url}/verify?token={make_purpose_token(u.id, 'verify', 2880)}"
    queue_email(u.email, "Verify your CabGo email", f"Open this link to verify your email:\n{link}")
    return {"ok": True}

# ---------- Profile ----------
class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=20)
    profile_pic: Optional[str] = Field(default=None, max_length=500)
    vehicle_info: Optional[str] = Field(default=None, max_length=80)
    vehicle_number: Optional[str] = Field(default=None, max_length=20)
    license_no: Optional[str] = Field(default=None, max_length=30)

@app.get("/api/profile")
def get_profile(u: User = Depends(current_user), s: Session = Depends(get_session)):
    out = public(u)
    out["review_count"] = s.exec(select(func.count(Review.id)).where(Review.rated_id == u.id)).one()
    drv = s.get(Driver, u.id)
    if drv:
        out["driver"] = {"vehicle_info": drv.vehicle_info, "vehicle_number": drv.vehicle_number,
                         "license_no": drv.license_no, "verified": drv.verified, "status": drv.status}
    return out

@app.put("/api/profile")
def update_profile(b: ProfileIn, u: User = Depends(current_user), s: Session = Depends(get_session)):
    if b.profile_pic and not b.profile_pic.startswith(("http://", "https://")):
        raise HTTPException(422, "Photo must be an http(s) link")
    u.name, u.phone, u.profile_pic = b.name.strip(), b.phone or None, b.profile_pic or None
    s.add(u)
    drv = s.get(Driver, u.id)
    if drv:
        if b.vehicle_info is not None: drv.vehicle_info = b.vehicle_info
        if b.vehicle_number is not None: drv.vehicle_number = b.vehicle_number
        if b.license_no is not None: drv.license_no = b.license_no
        s.add(drv)
    s.commit()
    return get_profile(u, s)

# ---------- Rides: estimate, nearby, request ----------
@app.get("/api/rides/estimate")
def estimate(olat: float, olng: float, dlat: float, dlng: float, _=Depends(current_user)):
    m, sec = distance_time((olat, olng), (dlat, dlng))
    return {"distance_meters": m, "duration_secs": sec, "fare": calc_fare(m, sec)}

@app.get("/api/drivers/nearby")
def nearby_drivers(lat: float, lng: float, _=Depends(current_user), s: Session = Depends(get_session)):
    rows = s.execute(text("""
        SELECT ST_Y(location) AS lat, ST_X(location) AS lng FROM drivers
        WHERE status='active' AND verified AND location IS NOT NULL
          AND ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography, :r)
        LIMIT 20"""), {"lat": lat, "lng": lng, "r": RADIUS_M}).all()
    return [{"lat": x.lat, "lng": x.lng} for x in rows]

class RideIn(BaseModel):
    pickup_lat: float = Field(ge=-90, le=90)
    pickup_lng: float = Field(ge=-180, le=180)
    drop_lat: float = Field(ge=-90, le=90)
    drop_lng: float = Field(ge=-180, le=180)

@app.post("/api/rides/request")
async def request_ride(body: RideIn, user: User = Depends(require_role("rider")),
                       s: Session = Depends(get_session)):
    open_ride = s.exec(select(Ride).where(Ride.rider_id == user.id,
                                          col(Ride.status).in_(ACTIVE))).first()
    if open_ride:
        raise HTTPException(409, f"You already have an active ride (#{open_ride.id})")
    m, sec = distance_time((body.pickup_lat, body.pickup_lng), (body.drop_lat, body.drop_lng))
    ride = Ride(rider_id=user.id, **body.model_dump(), distance_meters=m, duration_secs=sec,
                fare_estimate=calc_fare(m, sec), requested_at=utcnow())
    s.add(ride); s.commit(); s.refresh(ride)
    n = await dispatch_ride(s, ride)
    return {"ride_id": ride.id, "fare": ride.fare_estimate, "drivers_notified": n}

@app.get("/api/rides/active")
def active_ride(user: User = Depends(current_user), s: Session = Depends(get_session)):
    if user.role == "driver":
        q = select(Ride).where(Ride.driver_id == user.id, col(Ride.status).in_(IN_TRIP))
    else:
        q = select(Ride).where(Ride.rider_id == user.id, col(Ride.status).in_(ACTIVE))
    ride = s.exec(q.order_by(col(Ride.id).desc())).first()
    return {"ride": ride_dict(s, ride) if ride else None}

@app.get("/api/rides/history")
def history(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50),
            user: User = Depends(current_user), s: Session = Depends(get_session)):
    who = Ride.rider_id if user.role == "rider" else Ride.driver_id
    total = s.exec(select(func.count(Ride.id)).where(who == user.id)).one()
    rows = s.exec(select(Ride).where(who == user.id).order_by(col(Ride.id).desc())
                  .offset((page - 1) * size).limit(size)).all()
    items = [ride_dict(s, x) for x in rows]
    mine = {}
    if rows:
        mine = {rv.ride_id: rv for rv in s.exec(select(Review).where(
            Review.rater_id == user.id, col(Review.ride_id).in_([x.id for x in rows]))).all()}
    for it in items:
        rv = mine.get(it["id"])
        it["my_review"] = {"rating": rv.rating, "comment": rv.comment} if rv else None
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // size))}

@app.get("/api/rides/{ride_id}/status")
def ride_status(ride_id: int, user: User = Depends(current_user), s: Session = Depends(get_session)):
    return ride_dict(s, _own_ride(s, ride_id, user))

# ---------- Driver actions ----------
class StatusIn(BaseModel):
    status: str = Field(pattern="^(active|offline)$")

@app.post("/api/driver/status")
def driver_status(b: StatusIn, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    drv = s.get(Driver, d.id)
    if drv.status == "busy":
        raise HTTPException(409, "Finish your current ride first")
    drv.status = b.status
    s.add(drv); s.commit()
    return {"status": drv.status}

class LocIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

@app.post("/api/driver/location")
def set_driver_location(b: LocIn, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    s.execute(text("UPDATE drivers SET location=ST_SetSRID(ST_MakePoint(:lng,:lat),4326) WHERE user_id=:u"),
              {"lng": b.lng, "lat": b.lat, "u": d.id})
    s.commit()
    return {"ok": True}

@app.get("/api/driver/requests")
def driver_requests(d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    """Offers this driver can still accept (not expired, not declined)."""
    cutoff = utcnow() - timedelta(seconds=OFFER_SECS)
    rows = s.exec(select(Ride, RideOffer).where(
        RideOffer.ride_id == Ride.id, RideOffer.driver_id == d.id, RideOffer.status == "offered",
        Ride.status == "requested", RideOffer.offered_at > cutoff)).all()
    out = []
    for ride, o in rows:
        left = max(1, OFFER_SECS - int((utcnow() - o.offered_at).total_seconds()))
        out.append({"ride_id": ride.id, "pickup": [ride.pickup_lat, ride.pickup_lng],
                    "drop": [ride.drop_lat, ride.drop_lng], "fare": ride.fare_estimate,
                    "distance_km": round(ride.distance_meters / 1000, 1), "expires_in": left})
    return out

@app.get("/api/driver/earnings")
def earnings(d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    now = utcnow()
    today, week = now.replace(hour=0, minute=0, second=0, microsecond=0), now - timedelta(days=7)

    def total(since=None):
        q = select(func.coalesce(func.sum(Ride.fare_actual), 0), func.count(Ride.id)).where(
            Ride.driver_id == d.id, Ride.status == "paid")
        if since:
            q = q.where(col(Ride.completed_at) >= since)
        amount, trips = s.exec(q).one()
        return {"amount": round(float(amount), 2), "trips": trips}
    return {"today": total(today), "week": total(week), "all": total(), "rating": d.rating_avg}

@app.post("/api/rides/{ride_id}/accept")
async def accept(ride_id: int, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    drv = s.get(Driver, d.id)
    if drv.status != "active":
        raise HTTPException(409, "You must be online and free to accept rides")
    offer = s.exec(select(RideOffer).where(RideOffer.ride_id == ride_id, RideOffer.driver_id == d.id,
                                           RideOffer.status == "offered")).first()
    if not offer:
        raise HTTPException(409, "This request expired or was taken")
    res = s.execute(text("UPDATE rides SET status='accepted', driver_id=:d, accepted_at=:t "
                         "WHERE id=:i AND status='requested'"), {"d": d.id, "t": utcnow(), "i": ride_id})
    if res.rowcount == 0:                       # atomic: only one driver wins
        s.rollback()
        raise HTTPException(409, "Ride already taken")
    offer.status = "accepted"; s.add(offer)
    drv.status = "busy"; s.add(drv)
    closed = close_offers(s, ride_id, keep=d.id)
    s.commit()
    for uid in closed:
        await sio.emit("offer_closed", {"ride_id": ride_id}, room=f"user:{uid}")
    ride = s.get(Ride, ride_id)
    await notify(ride)
    return ride_dict(s, ride)

@app.post("/api/rides/{ride_id}/decline")
async def decline(ride_id: int, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    offer = s.exec(select(RideOffer).where(RideOffer.ride_id == ride_id, RideOffer.driver_id == d.id,
                                           RideOffer.status == "offered")).first()
    if offer:
        offer.status = "declined"; s.add(offer); s.commit()
    ride = s.get(Ride, ride_id)
    if ride and ride.status == "requested":
        await dispatch_ride(s, ride)            # try the next drivers right away
    return {"ok": True}

@app.post("/api/rides/{ride_id}/arrived")
async def arrived(ride_id: int, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    ride = _driver_ride(s, ride_id, d, "accepted")
    ride.status, ride.arrived_at = "arrived", utcnow()
    s.add(ride); s.commit()
    await notify(ride)
    return ride_dict(s, ride)

@app.post("/api/rides/{ride_id}/start")
async def start(ride_id: int, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    ride = _driver_ride(s, ride_id, d, "arrived")
    ride.status, ride.started_at = "started", utcnow()
    s.add(ride); s.commit()
    await notify(ride)
    return ride_dict(s, ride)

@app.post("/api/rides/{ride_id}/complete")
async def complete(ride_id: int, d: User = Depends(require_role("driver")), s: Session = Depends(get_session)):
    ride = _driver_ride(s, ride_id, d, "started")
    ride.status, ride.completed_at, ride.fare_actual = "completed", utcnow(), ride.fare_estimate
    free_driver(s, d.id)
    s.add(ride); s.commit()
    await notify(ride, fare=ride.fare_actual)
    return ride_dict(s, ride)

class CancelIn(BaseModel):
    reason: str = Field(default="", max_length=200)

@app.post("/api/rides/{ride_id}/cancel")
async def cancel(ride_id: int, b: CancelIn, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ride = _own_ride(s, ride_id, u)
    if u.id == ride.rider_id:
        if ride.status not in ("requested", "accepted", "arrived"):
            raise HTTPException(400, "This ride can't be cancelled now")
        if ride.driver_id:
            free_driver(s, ride.driver_id)
        closed = close_offers(s, ride.id)
        ride.status, ride.cancelled_at, ride.cancelled_by, ride.cancel_reason = \
            "cancelled", utcnow(), "rider", b.reason
        s.add(ride); s.commit()
        for uid in closed:
            await sio.emit("offer_closed", {"ride_id": ride_id}, room=f"user:{uid}")
        await notify(ride)
        return {"status": "cancelled"}
    # driver cancels: the ride goes back to the pool for other drivers
    if ride.status not in ("accepted", "arrived"):
        raise HTTPException(400, "You can only cancel before the trip starts")
    offer = s.exec(select(RideOffer).where(RideOffer.ride_id == ride.id,
                                           RideOffer.driver_id == u.id)).first()
    if offer:
        offer.status = "declined"; s.add(offer)
    free_driver(s, u.id)
    ride.status, ride.driver_id, ride.accepted_at, ride.arrived_at = "requested", None, None, None
    ride.requested_at = utcnow()
    s.add(ride); s.commit()
    await sio.emit("ride_update", {"ride_id": ride_id, "status": "requested",
                                   "message": "Driver cancelled - finding another driver"},
                   room=f"user:{ride.rider_id}")
    await sio.emit("ride_update", {"ride_id": ride_id, "status": "cancelled"}, room=f"user:{u.id}")
    await dispatch_ride(s, ride)
    return {"status": "re-dispatched"}

# ---------- Payments (Razorpay + cash) ----------
def _receipt(ride: Ride, pay: Payment) -> dict:
    return {"status": "paid", "ride_id": ride.id, "method": pay.method, "amount": pay.amount,
            "reference": pay.razorpay_payment_id or f"CASH-{ride.id}-{pay.id}",
            "distance_km": round(ride.distance_meters / 1000, 1)}

def _mark_paid(s: Session, ride_id: int, pay: Payment) -> dict:
    """Atomic + idempotent: only one 'completed -> paid' transition can ever succeed."""
    res = s.execute(text("UPDATE rides SET status='paid' WHERE id=:i AND status='completed'"), {"i": ride_id})
    if res.rowcount == 0:
        s.rollback()
        done = s.exec(select(Payment).where(Payment.ride_id == ride_id, Payment.status == "paid")).first()
        if done:
            return _receipt(s.get(Ride, ride_id), done)
        raise HTTPException(409, "This ride can't be paid right now")
    pay.status = "paid"; s.add(pay)
    try:
        s.commit()
    except IntegrityError:                      # unique index: already paid by a parallel request
        s.rollback()
        done = s.exec(select(Payment).where(Payment.ride_id == ride_id, Payment.status == "paid")).first()
        return _receipt(s.get(Ride, ride_id), done)
    dispatch_receipt(ride_id)
    return _receipt(s.get(Ride, ride_id), pay)

async def announce(s: Session, ride_id: int):
    ride = s.get(Ride, ride_id)
    if ride:
        await notify(ride)

@app.post("/api/payments/create-order/{ride_id}")
def create_order(ride_id: int, u: User = Depends(require_role("rider")), s: Session = Depends(get_session)):
    ride = _own_ride(s, ride_id, u)
    if s.exec(select(Payment).where(Payment.ride_id == ride.id, Payment.status == "paid")).first():
        raise HTTPException(409, "This ride is already paid")
    if ride.status != "completed":
        raise HTTPException(400, "Ride not completed")
    pay = s.exec(select(Payment).where(Payment.ride_id == ride.id, Payment.method == "online",
                                       Payment.status == "created")).first()
    if not pay:                                 # reuse an open order, so clicking twice is safe
        try:
            order = payments.create_order(ride.fare_actual, f"ride_{ride.id}")
        except Exception as e:
            raise HTTPException(502, f"Razorpay error: {e}")
        pay = Payment(ride_id=ride.id, razorpay_order_id=order["id"], amount=ride.fare_actual)
        s.add(pay); s.commit(); s.refresh(pay)
    return {"order_id": pay.razorpay_order_id, "amount": int(round(pay.amount * 100)),
            "key": settings.razorpay_key_id}

class VerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@app.post("/api/payments/verify")
async def verify(b: VerifyIn, u: User = Depends(require_role("rider")), s: Session = Depends(get_session)):
    if not payments.verify_payment(b.razorpay_order_id, b.razorpay_payment_id, b.razorpay_signature):
        raise HTTPException(400, "Bad signature")
    pay = s.exec(select(Payment).where(Payment.razorpay_order_id == b.razorpay_order_id)).first()
    if not pay:
        raise HTTPException(404, "Order not found")
    ride = _own_ride(s, pay.ride_id, u)
    if pay.status == "paid":
        return _receipt(ride, pay)
    pay.razorpay_payment_id = b.razorpay_payment_id
    out = _mark_paid(s, ride.id, pay)
    await announce(s, ride.id)
    return out

class FailedIn(BaseModel):
    razorpay_order_id: str
    reason: str = ""
# ---------- Demo Payment Gateway (no Razorpay credentials required) ----------
@app.post("/api/payments/failed")
class DemoPaymentIn(BaseModel):
    method: str = Field(pattern="^(upi|card|netbanking)$")
    outcome: str = Field(pattern="^(success|failure)$")


@app.post("/api/payments/demo/{ride_id}")
async def demo_payment(
    ride_id: int,
    body: DemoPaymentIn,
    u: User = Depends(require_role("rider")),
    s: Session = Depends(get_session)
):
    ride = _own_ride(s, ride_id, u)

    # Prevent duplicate payments
    done = s.exec(
        select(Payment).where(
            Payment.ride_id == ride.id,
            Payment.status == "paid"
        )
    ).first()

    if done:
        return _receipt(ride, done)

    if ride.status != "completed":
        raise HTTPException(400, "Ride not completed")

    # Simulate a declined payment
    if body.outcome == "failure":
        failed_payment = Payment(
            ride_id=ride.id,
            method=f"demo_{body.method}",
            amount=ride.fare_actual,
            status="failed",
            failure_reason="Demo payment declined"
        )

        s.add(failed_payment)
        s.commit()

        return {
            "status": "failed",
            "message": "Demo payment failed. You can try again."
        }

    # Generate a simulated transaction reference
    demo_reference = f"DEMO-{uuid.uuid4().hex[:12].upper()}"

    payment = Payment(
        ride_id=ride.id,
        method=f"demo_{body.method}",
        razorpay_payment_id=demo_reference,
        amount=ride.fare_actual
    )

    s.add(payment)
    s.commit()
    s.refresh(payment)

    # Reuse the existing payment and receipt logic
    result = _mark_paid(s, ride.id, payment)

    await announce(s, ride.id)

    return result
                        # rider can retry: a new order is created

@app.post("/api/payments/cash/{ride_id}")
async def pay_cash(ride_id: int, u: User = Depends(require_role("rider")), s: Session = Depends(get_session)):
    ride = _own_ride(s, ride_id, u)
    done = s.exec(select(Payment).where(Payment.ride_id == ride.id, Payment.status == "paid")).first()
    if done:
        return _receipt(ride, done)
    if ride.status != "completed":
        raise HTTPException(400, "Ride not completed")
    out = _mark_paid(s, ride.id, Payment(ride_id=ride.id, method="cash", amount=ride.fare_actual))
    await announce(s, ride.id)
    return out

@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request, s: Session = Depends(get_session)):
    body = (await request.body()).decode()
    if not payments.verify_webhook(body, request.headers.get("X-Razorpay-Signature", "")):
        raise HTTPException(400, "Bad signature")
    event = json.loads(body)
    ent = event.get("payload", {}).get("payment", {}).get("entity", {})
    pay = s.exec(select(Payment).where(Payment.razorpay_order_id == ent.get("order_id"))).first() if ent else None
    if pay:
        if event["event"] == "payment.captured" and pay.status != "paid":
            pay.razorpay_payment_id = ent["id"]
            try:
                _mark_paid(s, pay.ride_id, pay)
                await announce(s, pay.ride_id)
            except HTTPException:
                pass
        elif event["event"] == "payment.failed" and pay.status == "created":
            pay.status, pay.failure_reason = "failed", (ent.get("error_description") or "")[:200]
            s.add(pay); s.commit()
    return {"ok": True}

# ---------- Receipts & Reviews ----------
@app.get("/api/rides/{ride_id}/receipt")
def receipt(ride_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ride = _own_ride(s, ride_id, u)
    if ride.status != "paid":
        raise HTTPException(400, "Ride not paid yet")
    return FileResponse(build_receipt(ride_id))

class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=300)

def _recalc_rating(s: Session, user_id: str):
    avg, n = s.exec(select(func.avg(Review.rating), func.count(Review.id))
                    .where(Review.rated_id == user_id)).one()
    target = s.get(User, user_id)
    target.rating_avg = round(float(avg), 2) if avg is not None else 0
    s.add(target); s.commit()
    return target.rating_avg, n

@app.post("/api/rides/{ride_id}/review")
def review(ride_id: int, body: ReviewIn, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ride = _own_ride(s, ride_id, u)
    if ride.status != "paid":
        raise HTTPException(400, "You can review a ride after it is paid")
    if not ride.driver_id:
        raise HTTPException(400, "This ride has no driver to review")
    if s.exec(select(Review).where(Review.ride_id == ride.id, Review.rater_id == u.id)).first():
        raise HTTPException(409, "You already reviewed this ride")
    rated = ride.driver_id if u.id == ride.rider_id else ride.rider_id
    s.add(Review(ride_id=ride.id, rater_id=u.id, rated_id=rated,
                 rating=body.rating, comment=body.comment.strip()))
    try:
        s.commit()
    except IntegrityError:
        s.rollback()
        raise HTTPException(409, "You already reviewed this ride")
    avg, n = _recalc_rating(s, rated)
    return {"rated_id": rated, "rating_avg": avg, "review_count": n}

@app.get("/api/rides/{ride_id}/review")
def ride_review(ride_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ride = _own_ride(s, ride_id, u)
    mine = s.exec(select(Review).where(Review.ride_id == ride.id, Review.rater_id == u.id)).first()
    got = s.exec(select(Review).where(Review.ride_id == ride.id, Review.rated_id == u.id)).first()
    f = lambda x: {"rating": x.rating, "comment": x.comment} if x else None
    return {"mine": f(mine), "received": f(got)}

@app.get("/api/users/{user_id}/reviews")
def user_reviews(user_id: str, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50),
                 _=Depends(current_user), s: Session = Depends(get_session)):
    target = s.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    total = s.exec(select(func.count(Review.id)).where(Review.rated_id == user_id)).one()
    dist = {str(i): 0 for i in range(1, 6)}
    for rating, c in s.exec(select(Review.rating, func.count(Review.id))
                            .where(Review.rated_id == user_id).group_by(Review.rating)).all():
        dist[str(rating)] = c
    rows = s.exec(select(Review, User).where(Review.rated_id == user_id, User.id == Review.rater_id)
                  .order_by(col(Review.id).desc()).offset((page - 1) * size).limit(size)).all()
    return {"user": {"id": target.id, "name": target.name, "role": target.role,
                     "rating_avg": target.rating_avg},
            "count": total, "distribution": dist, "page": page, "pages": max(1, -(-total // size)),
            "items": [{"rating": rv.rating, "comment": rv.comment, "ride_id": rv.ride_id,
                       "rater_name": ((usr.name or "User").split(" ")[0]), "created_at": rv.created_at}
                      for rv, usr in rows]}

# Socket.IO wraps FastAPI. Run:  python -m uvicorn app.main:asgi --reload --port 8000
asgi = socketio.ASGIApp(sio, other_asgi_app=app)