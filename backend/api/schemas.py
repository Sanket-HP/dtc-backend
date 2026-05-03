"""Pydantic request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = ""
    is_company: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
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


# ─────────────────────────────────────────────
# Dataset
# ─────────────────────────────────────────────

class DatasetResponse(BaseModel):

    id: str
    owner_id: str

    title: str
    description: str
    category: str

    record_count: int

    schema: List[str]

    quality_score: float
    trust_score: float

    rating: float
    rating_count: int

    download_count: int
    purchase_count: int

    file_url: str

    created_at: datetime


class DatasetPreviewResponse(BaseModel):

    columns: List[str]

    preview: List[Dict[str, Any]]


class DatasetStatsResponse(BaseModel):

    datasets_uploaded: int

    total_records: int

    total_downloads: Optional[int] = 0


class DatasetRatingRequest(BaseModel):

    rating: int = Field(..., ge=1, le=5)


# ─────────────────────────────────────────────
# Dataset Upload (Manual)
# ─────────────────────────────────────────────

class ManualUploadRequest(BaseModel):

    title: str = Field(..., min_length=1, max_length=300)

    description: str = ""

    category: str = "general"

    records: List[Dict[str, Any]]


# ─────────────────────────────────────────────
# Marketplace
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# Dataset Requests (Bounty Marketplace)
# ─────────────────────────────────────────────

class DatasetRequestCreate(BaseModel):

    title: str

    description: str

    reward: float

    category: str = "general"

    deadline_days: int = 7


class DatasetRequestResponse(BaseModel):

    id: str

    title: str

    description: str

    reward: float

    category: str

    created_by: str

    deadline: datetime

    submission_count: int

    status: str


class DatasetSubmissionRequest(BaseModel):

    dataset_id: str


class DatasetSubmissionResponse(BaseModel):

    id: str

    request_id: str

    dataset_id: str

    submitted_by: str

    status: str

    submitted_at: datetime


# ─────────────────────────────────────────────
# Leaderboard
# ─────────────────────────────────────────────

class ContributorLeaderboard(BaseModel):

    user_id: str

    username: str

    token_balance: float

    datasets_uploaded: Optional[int] = 0


class DatasetLeaderboard(BaseModel):

    dataset_id: str

    title: str

    category: str

    quality_score: float

    trust_score: float

    downloads: int