from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

# Adds new columns/indexes to tables that already exist (keeps your data).
# Every line is safe to run again and again.
MIGRATIONS = [
    # users / drivers
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified boolean DEFAULT false",
    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS vehicle_number text DEFAULT ''",
    "ALTER TABLE drivers ADD COLUMN IF NOT EXISTS license_no text DEFAULT ''",
    # rides: lifecycle timestamps
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS requested_at timestamp",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS accepted_at timestamp",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS arrived_at timestamp",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS started_at timestamp",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS completed_at timestamp",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS cancelled_at timestamp",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS cancelled_by text",
    "ALTER TABLE rides ADD COLUMN IF NOT EXISTS cancel_reason text DEFAULT ''",
    # payments
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS failure_reason text",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS refund_id text",
    # reviews
    "ALTER TABLE reviews ADD COLUMN IF NOT EXISTS created_at timestamp",
    # indexes
    "CREATE INDEX IF NOT EXISTS idx_drivers_location ON drivers USING GIST (location)",
    "CREATE INDEX IF NOT EXISTS idx_rides_status ON rides (status)",
    "CREATE INDEX IF NOT EXISTS idx_reviews_rated ON reviews (rated_id)",
    # one paid payment per ride (double-payment protection)
    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_paid_payment ON payments (ride_id) WHERE status = 'paid'",
    # one review per person per ride
    "CREATE UNIQUE INDEX IF NOT EXISTS uniq_review_per_ride ON reviews (ride_id, rater_id)",
]

def init_db():
    with engine.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    SQLModel.metadata.create_all(engine)       # creates any missing tables
    for sql in MIGRATIONS:                     # then adds any missing columns / indexes
        try:
            with engine.begin() as c:
                c.execute(text(sql))
        except Exception as e:
            print("Migration warning:", str(e).splitlines()[0])

def get_session():
    with Session(engine) as s:
        yield s