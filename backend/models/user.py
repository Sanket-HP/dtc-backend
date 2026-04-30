"""User account model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Boolean
from ..database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "dtc_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)

    hashed_password = Column(String(255), nullable=False)

    full_name = Column(String(200), default="")
    is_company = Column(Boolean, default=False)

    token_balance = Column(Float, default=0.0)

    # Password reset system
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)