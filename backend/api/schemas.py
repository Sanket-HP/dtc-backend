"""Pydantic request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = ""
    is_company: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    is_company: bool
    token_balance: float
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dataset ───────────────────────────────────────────────────────────

class DatasetResponse(BaseModel):
    id: str
    owner_id: str
    title: str
    description: str
    category: str
    original_filename: str
    file_format: str
    record_count: int
    fields: str
    sample_data: str
    token_reward: float
    price: float
    is_aggregated: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ManualUploadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = ""
    category: str = "general"
    records: list[dict[str, Any]]


class DatasetStatsResponse(BaseModel):
    total_datasets: int
    total_records: int
    total_tokens_earned: float


# ── Marketplace ───────────────────────────────────────────────────────

class PurchaseRequest(BaseModel):
    dataset_id: str


class PurchaseResponse(BaseModel):
    id: str
    buyer_id: str
    dataset_id: str
    price_paid: float
    purchased_at: datetime

    class Config:
        from_attributes = True


class AggregateRequest(BaseModel):
    category: str
    title: str
    description: str = ""
