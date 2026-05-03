"""Dataset upload, listing, preview, download and rating routes – Firebase version."""

from __future__ import annotations

import csv
import io
import json
import uuid
import re
import math
import hashlib
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from google.cloud import firestore

from ..firebase_config import db, bucket
from .deps import get_current_user_id

from ..services.anti_spam import is_spam_dataset
from ..services.ai_validator import validate_dataset
from ..services.dataset_ai_score import compute_ai_score
from ..services.data_valuation import compute_dataset_value, compute_token_reward

router = APIRouter(prefix="/datasets", tags=["datasets"])


# -------------------------------------------------
# HASH FUNCTIONS
# -------------------------------------------------
def generate_dataset_hash(rows):

    normalized = json.dumps(
        sorted(rows, key=lambda x: json.dumps(x, sort_keys=True)),
        sort_keys=True
    )

    return hashlib.sha256(normalized.encode()).hexdigest()


def generate_file_hash(content: bytes):
    return hashlib.sha256(content).hexdigest()


# -------------------------------------------------
# PII ANONYMIZATION
# -------------------------------------------------
def anonymize_dataset(rows):

    email_pattern = r"\S+@\S+"
    phone_pattern = r"\b\d{10}\b"
    aadhaar_pattern = r"\b\d{12}\b"

    cleaned_rows = []

    for row in rows:

        new_row = {}

        for key, value in row.items():

            if isinstance(value, str):

                value = re.sub(email_pattern, "[EMAIL]", value)
                value = re.sub(phone_pattern, "[PHONE]", value)
                value = re.sub(aadhaar_pattern, "[ID]", value)

            new_row[key] = value

        cleaned_rows.append(new_row)

    return cleaned_rows


# -------------------------------------------------
# DATASET QUALITY ANALYSIS
# -------------------------------------------------
def analyze_dataset(rows):

    total_rows = len(rows)
    columns = rows[0].keys()

    missing = 0
    total_cells = total_rows * len(columns)

    for r in rows:
        for v in r.values():
            if v == "" or v is None:
                missing += 1

    missing_ratio = missing / total_cells

    unique_rows = set(json.dumps(r, sort_keys=True) for r in rows)
    duplicate_ratio = 1 - (len(unique_rows) / total_rows)

    values = []

    for r in rows:
        values.extend(list(r.values()))

    counter = Counter(values)

    entropy = 0

    for c in counter.values():
        p = c / len(values)
        entropy -= p * math.log2(p)

    entropy_score = min(entropy / 5, 1)

    quality_score = (
        (1 - missing_ratio) * 0.4 +
        (1 - duplicate_ratio) * 0.3 +
        entropy_score * 0.3
    )

    return round(quality_score, 2)


# -------------------------------------------------
# DATASET PRICE
# -------------------------------------------------
def calculate_dataset_price(dataset_value, rows):

    base_price = dataset_value * 5
    size_bonus = math.log(rows + 1)

    return round(base_price * size_bonus, 2)


# -------------------------------------------------
# LIST DATASETS
# -------------------------------------------------
@router.get("/")
async def list_datasets():

    docs = db.collection("datasets").limit(100).stream()

    results = []

    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        results.append(data)

    return results


# -------------------------------------------------
# DATASET PREVIEW
# -------------------------------------------------
@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str):

    doc = db.collection("datasets").document(dataset_id).get()

    if not doc.exists:
        raise HTTPException(404, "Dataset not found")

    data = doc.to_dict()

    return {
        "id": dataset_id,
        "title": data.get("title"),
        "category": data.get("category"),
        "record_count": data.get("record_count"),
        "quality_score": data.get("quality_score"),
        "ai_training_score": data.get("ai_training_score"),
        "dataset_value": data.get("dataset_value"),
        "price": data.get("price"),
        "downloads": data.get("downloads", 0),
        "rating": data.get("rating", 0),
        "sample_records": data.get("sample_records", [])
    }


# -------------------------------------------------
# DOWNLOAD DATASET
# -------------------------------------------------
@router.get("/{dataset_id}/download")
async def download_dataset(dataset_id: str):

    doc = db.collection("datasets").document(dataset_id).get()

    if not doc.exists:
        raise HTTPException(404, "Dataset not found")

    data = doc.to_dict()

    db.collection("datasets").document(dataset_id).update({
        "downloads": firestore.Increment(1)
    })

    return {
        "file_url": data.get("file_url"),
        "downloads": data.get("downloads", 0) + 1
    }


# -------------------------------------------------
# RATE DATASET
# -------------------------------------------------
@router.post("/{dataset_id}/rate")
async def rate_dataset(
    dataset_id: str,
    rating: int = Form(...),
    user_id: str = Depends(get_current_user_id)
):

    if rating < 1 or rating > 5:
        raise HTTPException(400, "Rating must be between 1 and 5")

    dataset_ref = db.collection("datasets").document(dataset_id)
    doc = dataset_ref.get()

    if not doc.exists:
        raise HTTPException(404, "Dataset not found")

    data = doc.to_dict()

    current_rating = data.get("rating", 0)
    rating_count = data.get("rating_count", 0)

    new_rating = (
        (current_rating * rating_count + rating)
        / (rating_count + 1)
    )

    dataset_ref.update({
        "rating": round(new_rating, 2),
        "rating_count": rating_count + 1
    })

    return {
        "dataset_id": dataset_id,
        "new_rating": round(new_rating, 2),
        "rating_count": rating_count + 1
    }


# -------------------------------------------------
# DELETE DATASET
# -------------------------------------------------
@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    user_id: str = Depends(get_current_user_id)
):

    dataset_ref = db.collection("datasets").document(dataset_id)
    doc = dataset_ref.get()

    if not doc.exists:
        raise HTTPException(404, "Dataset not found")

    dataset = doc.to_dict()

    if dataset.get("owner_id") != user_id:
        raise HTTPException(403, "Not allowed")

    reward = dataset.get("token_reward", 0)

    purchases = (
        db.collection("purchases")
        .where("dataset_id", "==", dataset_id)
        .limit(1)
        .get()
    )

    if purchases:
        raise HTTPException(
            400,
            "Dataset cannot be deleted because it has been purchased"
        )

    dataset_ref.delete()

    db.collection("dataset_registry").document(dataset["dataset_hash"]).delete()

    db.collection("users").document(user_id).update({
        "token_balance": firestore.Increment(-reward),
        "datasets_uploaded": firestore.Increment(-1)
    })

    db.collection("transactions").add({
        "user_id": user_id,
        "dataset_id": dataset_id,
        "amount": -reward,
        "type": "dataset_delete_rollback",
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "message": "Dataset deleted",
        "tokens_removed": reward
    }