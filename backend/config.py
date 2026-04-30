"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv(
    "DTC_DATABASE_URL",
    f"sqlite+aiosqlite:///{BASE_DIR / 'dtc.db'}",
)

SECRET_KEY = os.getenv("DTC_SECRET_KEY", "change-me-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("DTC_TOKEN_EXPIRE_MIN", "1440"))

STORAGE_DIR = BASE_DIR / "storage" / "datasets"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_ORIGINS = os.getenv("DTC_ALLOWED_ORIGINS", "*").split(",")

TOKENS_PER_RECORD = float(os.getenv("DTC_TOKENS_PER_RECORD", "0.5"))

PII_FIELDS = {
    "name", "first_name", "last_name", "full_name",
    "email", "e-mail", "email_address",
    "phone", "phone_number", "mobile", "telephone",
    "address", "street", "city", "zip", "zipcode", "postal_code",
    "ssn", "social_security", "passport", "driver_license",
}
