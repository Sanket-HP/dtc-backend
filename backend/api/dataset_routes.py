"""Dataset upload, listing, preview, and download routes – Firebase version."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..firebase_config import db, bucket
from .deps import get_current_user_id

router = APIRouter(prefix="/datasets", tags=["datasets"])


# -------------------------------------------------
# UPLOAD DATASET
# -------------------------------------------------
@router.post("/upload", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
    user_id: str = Depends(get_current_user_id),
):

    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file provided")

    content = await file.read()

    # Detect format
    if file.filename.endswith(".csv"):
        file_format = "csv"
        text = content.decode()
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

    elif file.filename.endswith(".json"):
        file_format = "json"
        rows = json.loads(content)

    else:
        raise HTTPException(400, "Only CSV or JSON allowed")

    record_count = len(rows)
    fields = list(rows[0].keys()) if rows else []
    sample_records = rows[:5]

    # Upload file to Firebase Storage
    blob = bucket.blob(f"datasets/{file.filename}")
    blob.upload_from_string(content)

    file_url = blob.public_url

    # Save metadata in Firestore
    doc = db.collection("datasets").document()

    dataset_data = {
        "id": doc.id,
        "owner_id": user_id,
        "title": title,
        "description": description,
        "category": category,
        "original_filename": file.filename,
        "file_format": file_format,
        "record_count": record_count,
        "fields": fields,
        "sample_records": sample_records,
        "file_url": file_url,
        "created_at": datetime.now(timezone.utc)
    }

    doc.set(dataset_data)

    # Reward tokens to user
    reward = record_count * 0.5

    db.collection("users").document(user_id).update({
        "token_balance": reward
    })

    dataset_data["token_reward"] = reward

    return dataset_data


# -------------------------------------------------
# MY DATASETS
# -------------------------------------------------
@router.get("/mine")
async def my_datasets(user_id: str = Depends(get_current_user_id)):

    docs = db.collection("datasets").where("owner_id", "==", user_id).stream()

    datasets = []

    for d in docs:
        datasets.append(d.to_dict())

    return datasets


# -------------------------------------------------
# DATASET STATS
# -------------------------------------------------
@router.get("/stats")
async def dataset_stats(user_id: str = Depends(get_current_user_id)):

    docs = db.collection("datasets").where("owner_id", "==", user_id).stream()

    total_datasets = 0
    total_records = 0

    for d in docs:
        data = d.to_dict()
        total_datasets += 1
        total_records += data.get("record_count", 0)

    return {
        "datasets_uploaded": total_datasets,
        "total_records": total_records
    }


# -------------------------------------------------
# GET DATASET
# -------------------------------------------------
@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):

    doc = db.collection("datasets").document(dataset_id).get()

    if not doc.exists:
        raise HTTPException(404, "Dataset not found")

    return doc.to_dict()


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
        "id": data["id"],
        "title": data["title"],
        "fields": data["fields"],
        "sample_records": data["sample_records"],
        "record_count": data["record_count"]
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

    return JSONResponse({
        "download_url": data["file_url"]
    })