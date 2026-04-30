"""Dataset metadata model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, String, Integer, Float, DateTime, Text, ForeignKey
from ..database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "dtc_datasets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("dtc_users.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    category = Column(String(100), default="general")
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(300), default="")
    file_format = Column(String(10), default="csv")
    record_count = Column(Integer, default=0)
    fields = Column(Text, default="[]")
    sample_data = Column(Text, default="[]")
    token_reward = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    is_aggregated = Column(Boolean, default=False)
    status = Column(String(30), default="processed")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)



class Purchase(Base):
    __tablename__ = "dtc_purchases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String, ForeignKey("dtc_users.id"), nullable=False, index=True)
    dataset_id = Column(String, ForeignKey("dtc_datasets.id"), nullable=False)
    price_paid = Column(Float, default=0.0)
    purchased_at = Column(DateTime(timezone=True), default=_utcnow)
