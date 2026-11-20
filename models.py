from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import NaiveDatetime
from sqlalchemy import Column, DateTime
from geoalchemy2 import Geometry
from sqlmodel import Field, SQLModel

def utcnow() -> datetime:
    """Current UTC time without timezone info (matches the 'timestamp' columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(primary_key=True)
    name: str = ""
    email: str = Field(default="", index=True)
    password_hash: str = ""
    phone: Optional[str] = None
    role: str = "rider"                       # rider | driver
    profile_pic: Optional[str] = None
    rating_avg: float = 0
    email_verified: bool = False

class Driver(SQLModel, table=True):
    __tablename__ = "drivers"
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    vehicle_info: str = ""
    vehicle_number: str = ""
    license_no: str = ""
    verified: bool = True                     # auto-approved (admin was removed)
    status: str = "offline"                   # active | busy | offline
    location: Any = Field(default=None, sa_column=Column(Geometry("POINT", srid=4326)))

class Ride(SQLModel, table=True):
    __tablename__ = "rides"
    id: Optional[int] = Field(default=None, primary_key=True)
    rider_id: str = Field(foreign_key="users.id", index=True)
    driver_id: Optional[str] = Field(default=None, foreign_key="users.id")
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    # requested | accepted | arrived | started | completed | paid | cancelled | expired | refunded
    status: str = "requested"
    fare_estimate: float = 0
    fare_actual: Optional[float] = None
    distance_meters: int = 0
    duration_secs: int = 0
    created_at: NaiveDatetime = Field(default_factory=utcnow)
    requested_at: Optional[datetime] = Field(default_factory=utcnow, sa_column=Column(DateTime))
    accepted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    arrived_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    started_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    cancelled_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    cancelled_by: Optional[str] = None
    cancel_reason: str = ""

class RideOffer(SQLModel, table=True):
    """One row per (ride, driver) that the ride was offered to."""
    __tablename__ = "ride_offers"
    id: Optional[int] = Field(default=None, primary_key=True)
    ride_id: int = Field(foreign_key="rides.id", index=True)
    driver_id: str = Field(foreign_key="users.id", index=True)
    status: str = "offered"                   # offered | accepted | declined | expired
    offered_at: Optional[datetime] = Field(default_factory=utcnow, sa_column=Column(DateTime))

class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    id: Optional[int] = Field(default=None, primary_key=True)
    ride_id: int = Field(foreign_key="rides.id", index=True)
    method: str = "online"                    # online (Razorpay) | cash
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount: float = 0
    status: str = "created"                   # created | paid | failed | refunded
    failure_reason: Optional[str] = None
    refund_id: Optional[str] = None

class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    id: Optional[int] = Field(default=None, primary_key=True)
    ride_id: int = Field(foreign_key="rides.id", index=True)
    rater_id: str
    rated_id: str
    rating: int
    comment: str = ""
    created_at: Optional[datetime] = Field(default_factory=utcnow, sa_column=Column(DateTime))