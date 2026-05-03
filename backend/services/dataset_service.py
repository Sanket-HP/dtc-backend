"""Core dataset processing service (Firebase Storage version)."""

from __future__ import annotations

import json
import uuid
import hashlib
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import TOKENS_PER_RECORD
from ..models.dataset import Dataset
from ..models.user import User
from ..utils.anonymizer import anonymize_records
from ..utils.parser import parse_file

from ..firebase_config import bucket

from ..services.dataset_ai_score import compute_ai_score
from ..services.data_valuation import compute_dataset_value
from ..services.anti_spam import is_spam_dataset


# -------------------------------------------------
# Upload dataset to Firebase Storage
# -------------------------------------------------
def upload_to_storage(file_bytes: bytes, filename: str) -> str:
    blob = bucket.blob(f"datasets/{filename}")
    blob.upload_from_string(file_bytes)
    blob.make_public()
    return blob.public_url


# -------------------------------------------------
# Generate dataset fingerprint hash
# -------------------------------------------------
def generate_dataset_hash(records: list[dict]) -> str:

    normalized = json.dumps(
        sorted(records[:200], key=lambda x: json.dumps(x, sort_keys=True)),
        sort_keys=True
    )

    return hashlib.sha256(normalized.encode()).hexdigest()


# -------------------------------------------------
# Calculate dataset quality score
# -------------------------------------------------
def calculate_quality_score(records: list[dict]) -> float:

    total = len(records)

    if total == 0:
        return 0.0

    unique_records = {json.dumps(r, sort_keys=True) for r in records}
    duplicate_ratio = 1 - (len(unique_records) / total)

    missing = 0
    total_fields = 0

    for r in records:
        for v in r.values():

            total_fields += 1

            if v in ("", None):
                missing += 1

    missing_ratio = missing / total_fields if total_fields else 0

    quality = (1 - duplicate_ratio) * (1 - missing_ratio)

    return round(quality, 3)


# -------------------------------------------------
# Process uploaded dataset
# -------------------------------------------------
async def process_and_store(
    db: AsyncSession,
    owner_id: str,
    title: str,
    description: str,
    category: str,
    raw_content: bytes,
    original_filename: str,
) -> Dataset:

    records = parse_file(raw_content, original_filename)

    if not records:
        raise ValueError("The uploaded file contains no records.")

    cleaned, removed_fields = anonymize_records(records)

    # spam detection
    if is_spam_dataset(cleaned):
        raise ValueError("Dataset rejected: spam or synthetic dataset detected.")

    dataset_hash = generate_dataset_hash(cleaned)

    # duplicate dataset protection
    stmt = select(Dataset).where(Dataset.dataset_hash == dataset_hash)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise ValueError("Duplicate dataset detected. Upload rejected.")

    dataset_id = str(uuid.uuid4())

    fmt = "csv" if original_filename.lower().endswith(".csv") else "json"
    stored_filename = f"{dataset_id}.{fmt}"

    # upload to Firebase
    file_url = upload_to_storage(raw_content, stored_filename)

    fields = sorted({k for rec in cleaned for k in rec.keys()})
    sample = cleaned[:5]

    record_count = len(cleaned)

    # quality scoring
    quality_score = calculate_quality_score(cleaned)

    # AI usefulness scoring
    ai_score = compute_ai_score(cleaned)

    # dataset valuation
    dataset_value = compute_dataset_value(
        record_count,
        quality_score,
        ai_score,
        category
    )

    # token reward
    reward = round(record_count * TOKENS_PER_RECORD * dataset_value, 2)

    # dataset price
    price = round(reward * 2, 2)

    # trust score
    trust_score = round((quality_score + ai_score) / 2, 3)

    ds = Dataset(
        id=dataset_id,
        owner_id=owner_id,
        title=title,
        description=description,
        category=category,
        file_path=file_url,
        original_filename=original_filename,
        file_format=fmt,
        record_count=record_count,
        fields=json.dumps(fields),
        sample_data=json.dumps(sample, default=str),

        dataset_hash=dataset_hash,

        quality_score=quality_score,
        ai_training_score=ai_score,
        dataset_value=dataset_value,
        trust_score=trust_score,

        downloads=0,
        purchase_count=0,

        token_reward=reward,
        price=price,

        version=1,
        status="processed",
    )

    db.add(ds)

    user = await db.get(User, owner_id)

    if user:

        user.token_balance = (user.token_balance or 0) + reward

        user.tokens_earned = (user.tokens_earned or 0) + reward

        user.datasets_uploaded = (user.datasets_uploaded or 0) + 1

    await db.commit()
    await db.refresh(ds)

    return ds


# -------------------------------------------------
# Manual dataset entry
# -------------------------------------------------
async def process_manual_input(
    db: AsyncSession,
    owner_id: str,
    title: str,
    description: str,
    category: str,
    records: list[dict[str, Any]],
) -> Dataset:

    if not records:
        raise ValueError("No records provided.")

    cleaned, _ = anonymize_records(records)

    if is_spam_dataset(cleaned):
        raise ValueError("Dataset rejected: spam dataset.")

    dataset_hash = generate_dataset_hash(cleaned)

    dataset_id = str(uuid.uuid4())

    stored_filename = f"{dataset_id}.json"

    file_bytes = json.dumps(cleaned).encode()

    file_url = upload_to_storage(file_bytes, stored_filename)

    fields = sorted({k for rec in cleaned for k in rec.keys()})
    sample = cleaned[:5]

    record_count = len(cleaned)

    quality_score = calculate_quality_score(cleaned)
    ai_score = compute_ai_score(cleaned)

    dataset_value = compute_dataset_value(
        record_count,
        quality_score,
        ai_score,
        category
    )

    reward = round(record_count * TOKENS_PER_RECORD * dataset_value, 2)

    price = round(reward * 2, 2)

    trust_score = round((quality_score + ai_score) / 2, 3)

    ds = Dataset(
        id=dataset_id,
        owner_id=owner_id,
        title=title,
        description=description,
        category=category,
        file_path=file_url,
        original_filename="manual_input.json",
        file_format="json",
        record_count=record_count,
        fields=json.dumps(fields),
        sample_data=json.dumps(sample, default=str),

        dataset_hash=dataset_hash,

        quality_score=quality_score,
        ai_training_score=ai_score,
        dataset_value=dataset_value,
        trust_score=trust_score,

        downloads=0,
        purchase_count=0,

        token_reward=reward,
        price=price,

        version=1,
        status="processed",
    )

    db.add(ds)

    user = await db.get(User, owner_id)

    if user:

        user.token_balance = (user.token_balance or 0) + reward
        user.tokens_earned = (user.tokens_earned or 0) + reward
        user.datasets_uploaded = (user.datasets_uploaded or 0) + 1

    await db.commit()
    await db.refresh(ds)

    return ds


# -------------------------------------------------
# User dataset statistics
# -------------------------------------------------
async def get_dataset_stats(db: AsyncSession, owner_id: str) -> dict:

    stmt = select(
        func.count(Dataset.id),
        func.coalesce(func.sum(Dataset.record_count), 0),
        func.coalesce(func.sum(Dataset.token_reward), 0),
    ).where(Dataset.owner_id == owner_id)

    result = await db.execute(stmt)

    row = result.one()

    return {
        "total_datasets": row[0],
        "total_records": int(row[1]),
        "total_tokens_earned": float(row[2]),
    }