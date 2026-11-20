import socketio
from sqlalchemy import text
from sqlmodel import Session
from .auth import decode_token
from .config import settings
from .db import engine
from .models import Ride

sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins="*",
    client_manager=socketio.AsyncRedisManager(settings.redis_url) if settings.redis_url else None)

@sio.event
async def connect(sid, environ, auth):
    try:
        uid = decode_token((auth or {})["token"])["sub"]
    except Exception:
        raise ConnectionRefusedError("unauthorized")
    await sio.save_session(sid, {"uid": uid})
    await sio.enter_room(sid, f"user:{uid}")

@sio.event
async def join_ride(sid, data):
    uid = (await sio.get_session(sid))["uid"]
    with Session(engine) as s:
        ride = s.get(Ride, data["ride_id"])
    if ride and uid in (ride.rider_id, ride.driver_id):
        await sio.enter_room(sid, f"ride:{ride.id}")

@sio.event
async def driver_location(sid, data):
    uid = (await sio.get_session(sid))["uid"]
    with engine.begin() as c:
        c.execute(text("UPDATE drivers SET location=ST_SetSRID(ST_MakePoint(:lng,:lat),4326) "
                       "WHERE user_id=:u"), {"lng": data["lng"], "lat": data["lat"], "u": uid})
    if data.get("ride_id"):
        await sio.emit("driver_location", {"lat": data["lat"], "lng": data["lng"]},
                       room=f"ride:{data['ride_id']}")