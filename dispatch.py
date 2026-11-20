import asyncio
from datetime import timedelta
from sqlalchemy import text
from sqlmodel import Session, select
from .db import engine
from .models import Ride, RideOffer, utcnow
from .realtime import sio

OFFER_SECS = 20        # a driver has 20 s to answer an offer
MAX_WAIT_SECS = 120    # ride expires if nobody accepts within 2 minutes
BATCH = 3              # offer to the 3 nearest free drivers at a time
RADIUS_M = 5000

ELIGIBLE_SQL = text("""
  SELECT d.user_id FROM drivers d
  WHERE d.status = 'active' AND d.verified AND d.location IS NOT NULL
    AND ST_DWithin(d.location::geography,
                   ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography, :radius)
    AND NOT EXISTS (SELECT 1 FROM ride_offers o WHERE o.ride_id = :rid AND o.driver_id = d.user_id)
  ORDER BY ST_Distance(d.location::geography,
                   ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography)
  LIMIT :n""")

def offer_payload(r: Ride) -> dict:
    return {"ride_id": r.id, "pickup": [r.pickup_lat, r.pickup_lng], "drop": [r.drop_lat, r.drop_lng],
            "fare": r.fare_estimate, "distance_km": round(r.distance_meters / 1000, 1),
            "expires_in": OFFER_SECS}

async def dispatch_ride(s: Session, ride: Ride) -> int:
    """Offer the ride to the next nearest free drivers (skips drivers already asked)."""
    pending = s.exec(select(RideOffer).where(RideOffer.ride_id == ride.id,
                                             RideOffer.status == "offered")).first()
    if pending:
        return 0
    rows = s.execute(ELIGIBLE_SQL, {"lat": ride.pickup_lat, "lng": ride.pickup_lng,
                                    "radius": RADIUS_M, "rid": ride.id, "n": BATCH}).all()
    ids = [r[0] for r in rows]
    for uid in ids:
        s.add(RideOffer(ride_id=ride.id, driver_id=uid, status="offered", offered_at=utcnow()))
    s.commit()
    payload = offer_payload(ride)
    for uid in ids:
        await sio.emit("ride_request", payload, room=f"user:{uid}")
    return len(ids)

async def dispatch_tick():
    now = utcnow()
    with Session(engine) as s:
        stale = s.exec(select(RideOffer).where(
            RideOffer.status == "offered",
            RideOffer.offered_at < now - timedelta(seconds=OFFER_SECS))).all()
        closed = [(o.ride_id, o.driver_id) for o in stale]
        for o in stale:
            o.status = "expired"; s.add(o)
        s.commit()
        for rid, uid in closed:
            await sio.emit("offer_closed", {"ride_id": rid}, room=f"user:{uid}")

        for ride in s.exec(select(Ride).where(Ride.status == "requested")).all():
            started = ride.requested_at or now
            if (now - started).total_seconds() > MAX_WAIT_SECS:
                rid, rider = ride.id, ride.rider_id
                ride.status = "expired"; s.add(ride)
                for o in s.exec(select(RideOffer).where(RideOffer.ride_id == rid,
                                                        RideOffer.status == "offered")).all():
                    o.status = "expired"; s.add(o)
                s.commit()
                await sio.emit("ride_update", {"ride_id": rid, "status": "expired"}, room=f"user:{rider}")
                continue
            await dispatch_ride(s, ride)

async def dispatch_loop():
    while True:
        try:
            await dispatch_tick()
        except Exception as e:
            print("dispatch error:", e)
        await asyncio.sleep(5)