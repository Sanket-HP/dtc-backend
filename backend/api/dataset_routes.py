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

from ..firebase_config import db, bucket
from .deps import get_current_user_id

from ..services.anti_spam import is_spam_dataset
from ..services.ai_validator import validate_dataset
from ..services.dataset_ai_score import compute_ai_score
from ..services.data_valuation import compute_dataset_value, compute_token_reward

router = APIRouter(prefix="/datasets", tags=["datasets"])


# -------------------------------------------------
# DATASET HASH GENERATION (GLOBAL DUPLICATE DETECTION)
# -------------------------------------------------
def generate_dataset_hash(rows):

    normalized = json.dumps(
        sorted(rows, key=lambda x: json.dumps(x, sort_keys=True)),
        sort_keys=True
    )

    return hashlib.sha256(normalized.encode()).hexdigest()


# -------------------------------------------------
# PARTIAL SIMILARITY DETECTION
# prevents users uploading slightly modified datasets
# -------------------------------------------------
def dataset_similarity(rows1, rows2):

    set1 = set(json.dumps(r, sort_keys=True) for r in rows1[:500])
    set2 = set(json.dumps(r, sort_keys=True) for r in rows2[:500])

    if not set1 or not set2:
        return 0

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union


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
# UPLOAD DATASET
# -------------------------------------------------
@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
    user_id: str = Depends(get_current_user_id),
):

    content = await file.read()

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 20MB)")

    # Parse dataset
    if file.filename.endswith(".csv"):

        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

    elif file.filename.endswith(".json"):

        rows = json.loads(content)

    else:
        raise HTTPException(400, "Only CSV or JSON allowed")

    if len(rows) < 20:
        raise HTTPException(400, "Dataset too small (minimum 20 rows)")

    rows = anonymize_dataset(rows)

    # Spam detection
    if is_spam_dataset(rows):
        raise HTTPException(400, "Dataset rejected: spam dataset detected")

    # AI validation
    validation = validate_dataset(rows)

    if not validation["valid"]:
        raise HTTPException(400, f"Dataset rejected: {validation['issues']}")

    dataset_hash = generate_dataset_hash(rows)

    # -------------------------------------------------
    # GLOBAL DUPLICATE DETECTION
    # -------------------------------------------------
    existing = (
        db.collection("datasets")
        .where("dataset_hash", "==", dataset_hash)
        .limit(1)
        .get()
    )

    if existing:
        raise HTTPException(400, "This dataset already exists on the platform.")

    # -------------------------------------------------
    # SIMILAR DATASET DETECTION
    # -------------------------------------------------
    docs = db.collection("datasets").limit(50).stream()

    for d in docs:

        data = d.to_dict()

        sample = data.get("sample_records")

        if sample:

            similarity = dataset_similarity(rows, sample)

            if similarity > 0.9:
                raise HTTPException(
                    400,
                    "Dataset too similar to existing dataset."
                )

    # -------------------------------------------------
    # SCORING
    # -------------------------------------------------
    quality_score = analyze_dataset(rows)

    ai_score = compute_ai_score(rows)

    record_count = len(rows)

    dataset_value = compute_dataset_value(
        record_count,
        quality_score,
        ai_score,
        category
    )

    reward = compute_token_reward(record_count, dataset_value)

    dataset_id = str(uuid.uuid4())

    storage_filename = f"{dataset_id}_{file.filename}"

    blob = bucket.blob(f"datasets/{storage_filename}")
    blob.upload_from_string(content)

    file_url = blob.public_url

    # -------------------------------------------------
    # SAVE DATASET
    # -------------------------------------------------
    dataset_data = {
        "id": dataset_id,
        "owner_id": user_id,
        "title": title,
        "description": description,
        "category": category,
        "record_count": record_count,
        "quality_score": quality_score,
        "ai_training_score": ai_score,
        "dataset_value": dataset_value,
        "trust_score": round((quality_score + ai_score) / 2, 2),
        "rating": 0,
        "rating_count": 0,
        "download_count": 0,
        "purchase_count": 0,
        "dataset_hash": dataset_hash,
        "file_url": file_url,
        "sample_records": rows[:20],
        "created_at": datetime.now(timezone.utc)
    }

    db.collection("datasets").document(dataset_id).set(dataset_data)

    # -------------------------------------------------
    # UPDATE USER WALLET
    # -------------------------------------------------
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    balance = 0

    if user_doc.exists:
        balance = user_doc.to_dict().get("token_balance", 0)

    user_ref.update({
        "token_balance": balance + reward
    })

    db.collection("transactions").add({
        "user_id": user_id,
        "dataset_id": dataset_id,
        "amount": reward,
        "type": "dataset_reward",
        "created_at": datetime.now(timezone.utc)
    })

    dataset_data["token_reward"] = reward

    return dataset_data