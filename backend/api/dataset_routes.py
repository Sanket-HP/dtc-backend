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


# -------------------------------------------------
# DATASET PRICE
# -------------------------------------------------
def calculate_dataset_price(dataset_value, records):

    base_price = dataset_value * 5
    size_bonus = math.log(records + 1)

    return round(base_price * size_bonus, 2)


# -------------------------------------------------
# PARSE DATASET FILE
# -------------------------------------------------
def parse_file(content: bytes, filename: str):

    if filename.endswith(".csv"):

        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))

        return [row for row in reader]

    elif filename.endswith(".json"):

        return json.loads(content)

    else:
        raise HTTPException(400, "Unsupported file format")


# -------------------------------------------------
# UPLOAD DATASET
# -------------------------------------------------
@router.post("/upload")
async def upload_dataset(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):

    content = await file.read()

    rows = parse_file(content, file.filename)

    if not rows:
        raise HTTPException(400, "Dataset is empty")

    if is_spam_dataset(rows):
        raise HTTPException(400, "Dataset flagged as spam")

    dataset_hash = generate_dataset_hash(rows)

    record_count = len(rows)

    # AI scoring
    ai_score = compute_ai_score(rows)

    # quality
    quality_score = 1 - (len(set(json.dumps(r, sort_keys=True) for r in rows)) / record_count)

    # dataset value
    dataset_value = compute_dataset_value(
        record_count,
        quality_score,
        ai_score,
        category,
        downloads=0,
        created_at=datetime.now(timezone.utc)
    )

    # token reward
    token_reward = compute_token_reward(record_count, dataset_value)

    # PRICE FIX
    price = calculate_dataset_price(dataset_value, record_count)

    dataset_id = str(uuid.uuid4())

    # upload file to firebase
    blob = bucket.blob(f"datasets/{dataset_id}/{file.filename}")
    blob.upload_from_string(content)

    file_url = blob.public_url

    dataset_data = {

        "id": dataset_id,
        "title": title,
        "description": description,
        "category": category,

        "owner_id": user_id,

        "record_count": record_count,

        "quality_score": round(quality_score, 2),
        "ai_training_score": round(ai_score, 2),

        "dataset_value": dataset_value,

        "token_reward": token_reward,

        "price": price,

        "downloads": 0,
        "rating": 0,
        "rating_count": 0,

        "dataset_hash": dataset_hash,

        "file_url": file_url,

        "created_at": datetime.now(timezone.utc)
    }

    db.collection("datasets").document(dataset_id).set(dataset_data)

    # reward tokens
    db.collection("users").document(user_id).update({
        "token_balance": firestore.Increment(token_reward),
        "tokens_earned": firestore.Increment(token_reward),
        "datasets_uploaded": firestore.Increment(1)
    })

    db.collection("transactions").add({
        "user_id": user_id,
        "dataset_id": dataset_id,
        "amount": token_reward,
        "type": "dataset_upload_reward",
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "message": "Dataset uploaded successfully",
        "dataset_id": dataset_id,
        "token_reward": token_reward,
        "price": price
    }


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