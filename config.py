from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/cabgo"
    redis_url: str = ""
    use_celery: bool = False
    secret_key: str = "change-me"
    google_maps_key: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    smtp_host: str = ""
    smtp_user: str = ""
    smtp_pass: str = ""
    frontend_url: str = "http://localhost:3000"

settings = Settings()