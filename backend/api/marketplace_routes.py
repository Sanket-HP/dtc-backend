"""Marketplace routes – browse, purchase, aggregate (Firebase version)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.cloud import firestore

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
    limit: int = Query(50, ge=1, le=100),
):

    docs = db.collection("datasets").limit(500).stream()

    datasets = []

    for doc in docs:

        data = doc.to_dict()
        data["id"] = doc.id

        if category and data.get("category") != category:
            continue

        if min_quality and data.get("quality_score", 0) < min_quality:
            continue

        datasets.append(data)

    datasets.sort(
        key=lambda x: (
            x.get("downloads", 0),
            x.get("quality_score", 0)
        ),
        reverse=True
    )

    return datasets[:limit]


# -------------------------------------------------
# TRENDING DATASETS
# -------------------------------------------------
@router.get("/trending")
async def trending_datasets():

    docs = (
        db.collection("datasets")
        .order_by("downloads", direction=firestore.Query.DESCENDING)
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

    docs = db.collection("datasets").limit(300).stream()

    datasets = []

    for d in docs:

        data = d.to_dict()
        data["id"] = d.id

        if data.get("quality_score", 0) >= 0.9:
            datasets.append(data)

    datasets.sort(key=lambda x: x.get("downloads", 0), reverse=True)

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
        "dataset_value": data.get("dataset_value"),
        "price": data.get("price"),
        "downloads": data.get("downloads", 0)
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

    if dataset.get("owner_id") == user.get("id"):
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

    price = dataset.get("price", 5)

    if buyer.get("token_balance", 0) < price:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Insufficient token balance"
        )

    # Royalty split
    owner_share = round(price * 0.8, 2)
    platform_fee = round(price * 0.2, 2)

    owner_ref = db.collection("users").document(dataset["owner_id"])

    # Deduct buyer tokens
    buyer_ref.update({
        "token_balance": firestore.Increment(-price)
    })

    # Reward owner
    owner_ref.update({
        "token_balance": firestore.Increment(owner_share),
        "tokens_earned": firestore.Increment(owner_share)
    })

    # Update dataset stats
    dataset_ref.update({
        "downloads": firestore.Increment(1)
    })

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

    # Buyer transaction
    db.collection("transactions").add({
        "user_id": user["id"],
        "dataset_id": body.dataset_id,
        "amount": -price,
        "type": "dataset_purchase",
        "created_at": datetime.now(timezone.utc)
    })

    # Seller transaction
    db.collection("transactions").add({
        "user_id": dataset["owner_id"],
        "dataset_id": body.dataset_id,
        "amount": owner_share,
        "type": "dataset_sale",
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
        "downloads": 0,
        "price": 0
    }

    new_dataset_ref.set(dataset_data)

    return dataset_data