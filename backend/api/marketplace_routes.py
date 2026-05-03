"""Marketplace routes – browse, purchase, aggregate (Firebase version)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..firebase_config import db
from .deps import get_current_user
from .schemas import AggregateRequest, PurchaseRequest

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# -------------------------------------------------
# LIST DATASETS IN MARKETPLACE
# -------------------------------------------------
@router.get("/datasets")
async def list_marketplace(
    category: str | None = Query(None),
    min_quality: float | None = Query(None),
    min_trust: float | None = Query(None),
):

    docs = db.collection("datasets").stream()

    datasets = []

    for doc in docs:

        data = doc.to_dict()
        data["id"] = doc.id

        if category and data.get("category") != category:
            continue

        if min_quality and data.get("quality_score", 0) < min_quality:
            continue

        if min_trust and data.get("trust_score", 0) < min_trust:
            continue

        datasets.append(data)

    datasets.sort(
        key=lambda x: x.get("created_at", datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True
    )

    return datasets


# -------------------------------------------------
# TRENDING DATASETS
# -------------------------------------------------
@router.get("/trending")
async def trending_datasets():

    docs = (
        db.collection("datasets")
        .order_by("download_count", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        results.append(data)

    return results


# -------------------------------------------------
# FEATURED DATASETS
# -------------------------------------------------
@router.get("/featured")
async def featured_datasets():

    docs = db.collection("datasets").stream()

    datasets = []

    for d in docs:

        data = d.to_dict()
        data["id"] = d.id

        if data.get("quality_score", 0) >= 0.9:
            datasets.append(data)

    datasets.sort(key=lambda x: x.get("trust_score", 0), reverse=True)

    return datasets[:10]


# -------------------------------------------------
# LIST CATEGORIES
# -------------------------------------------------
@router.get("/categories")
async def list_categories():

    docs = db.collection("datasets").stream()

    category_count = {}

    for doc in docs:

        data = doc.to_dict()

        category = data.get("category", "general")

        category_count[category] = category_count.get(category, 0) + 1

    return [
        {"category": k, "count": v}
        for k, v in category_count.items()
    ]


# -------------------------------------------------
# DATASET PREVIEW
# -------------------------------------------------
@router.get("/datasets/{dataset_id}/preview")
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
        "trust_score": data.get("trust_score"),
        "dataset_value": data.get("dataset_value"),
        "download_count": data.get("download_count", 0)
    }


# -------------------------------------------------
# PURCHASE DATASET
# -------------------------------------------------
@router.post("/purchase", status_code=201)
async def purchase_dataset(
    body: PurchaseRequest,
    user: dict = Depends(get_current_user),
):

    dataset_ref = db.collection("datasets").document(body.dataset_id)
    dataset_doc = dataset_ref.get()

    if not dataset_doc.exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")

    dataset = dataset_doc.to_dict()

    if dataset["owner_id"] == user["id"]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot purchase your own dataset"
        )

    # Prevent duplicate purchase
    existing_purchase = (
        db.collection("purchases")
        .where("buyer_id", "==", user["id"])
        .where("dataset_id", "==", body.dataset_id)
        .limit(1)
        .stream()
    )

    if list(existing_purchase):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Dataset already purchased"
        )

    buyer_ref = db.collection("users").document(user["id"])
    buyer_doc = buyer_ref.get()

    if not buyer_doc.exists:
        raise HTTPException(404, "Buyer account not found")

    buyer = buyer_doc.to_dict()

    price = dataset.get("dataset_value", 10)

    if buyer.get("token_balance", 0) < price:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Insufficient token balance"
        )

    # Deduct buyer tokens
    buyer_ref.update({
        "token_balance": buyer["token_balance"] - price
    })

    # Add tokens to dataset owner
    owner_ref = db.collection("users").document(dataset["owner_id"])
    owner_doc = owner_ref.get()

    if owner_doc.exists:

        owner = owner_doc.to_dict()

        owner_ref.update({
            "token_balance": owner.get("token_balance", 0) + price
        })

    # Increase dataset counters
    dataset_ref.update({
        "download_count": dataset.get("download_count", 0) + 1,
        "purchase_count": dataset.get("purchase_count", 0) + 1
    })

    # Save purchase
    purchase_ref = db.collection("purchases").document()

    purchase_data = {
        "id": purchase_ref.id,
        "buyer_id": user["id"],
        "dataset_id": body.dataset_id,
        "price_paid": price,
        "file_url": dataset.get("file_url"),
        "purchased_at": datetime.now(timezone.utc)
    }

    purchase_ref.set(purchase_data)

    # Log transaction
    db.collection("transactions").add({
        "user_id": user["id"],
        "dataset_id": body.dataset_id,
        "amount": -price,
        "type": "dataset_purchase",
        "created_at": datetime.now(timezone.utc)
    })

    return purchase_data


# -------------------------------------------------
# AGGREGATE DATASETS
# -------------------------------------------------
@router.post("/aggregate", status_code=201)
async def aggregate_datasets(
    body: AggregateRequest,
    user: dict = Depends(get_current_user),
):

    docs = db.collection("datasets").where("category", "==", body.category).stream()

    combined_records = []
    fields = set()

    for doc in docs:

        data = doc.to_dict()

        sample = data.get("sample_records", [])

        for row in sample:
            combined_records.append(row)
            fields.update(row.keys())

    if not combined_records:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No datasets found for this category"
        )

    new_dataset_ref = db.collection("datasets").document()

    dataset_data = {
        "id": new_dataset_ref.id,
        "owner_id": user["id"],
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "record_count": len(combined_records),
        "fields": list(fields),
        "sample_records": combined_records[:5],
        "is_aggregated": True,
        "created_at": datetime.now(timezone.utc),
        "download_count": 0
    }

    new_dataset_ref.set(dataset_data)

    return dataset_data