"""Marketplace routes – browse, purchase, aggregate (Firebase version)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..firebase_config import db
from .deps import get_current_user
from .schemas import (
    AggregateRequest,
    DatasetResponse,
    PurchaseRequest,
    PurchaseResponse,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# -------------------------------------------------
# LIST DATASETS IN MARKETPLACE
# -------------------------------------------------
@router.get("/datasets")
async def list_marketplace(category: str | None = Query(None)):

    docs = db.collection("datasets").stream()

    datasets = []

    for doc in docs:
        data = doc.to_dict()

        if category and data.get("category") != category:
            continue

        datasets.append(data)

    datasets.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return datasets


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
# PURCHASE DATASET
# -------------------------------------------------
@router.post("/purchase", status_code=201)
async def purchase_dataset(
    body: PurchaseRequest,
    user: dict = Depends(get_current_user),
):

    dataset_doc = db.collection("datasets").document(body.dataset_id).get()

    if not dataset_doc.exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")

    dataset = dataset_doc.to_dict()

    if dataset["owner_id"] == user["id"]:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot purchase your own dataset"
        )

    buyer_doc = db.collection("users").document(user["id"]).get()
    buyer = buyer_doc.to_dict()

    price = dataset.get("price", 10)

    if buyer.get("token_balance", 0) < price:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Insufficient token balance"
        )

    # Deduct tokens from buyer
    db.collection("users").document(user["id"]).update({
        "token_balance": buyer["token_balance"] - price
    })

    # Add tokens to owner
    owner_doc = db.collection("users").document(dataset["owner_id"]).get()

    if owner_doc.exists:
        owner = owner_doc.to_dict()

        db.collection("users").document(dataset["owner_id"]).update({
            "token_balance": owner.get("token_balance", 0) + price
        })

    # Save purchase record
    purchase_ref = db.collection("purchases").document()

    purchase_data = {
        "id": purchase_ref.id,
        "buyer_id": user["id"],
        "dataset_id": body.dataset_id,
        "price_paid": price
    }

    purchase_ref.set(purchase_data)

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

    new_dataset = db.collection("datasets").document()

    dataset_data = {
        "id": new_dataset.id,
        "owner_id": user["id"],
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "record_count": len(combined_records),
        "fields": list(fields),
        "sample_records": combined_records[:5],
        "is_aggregated": True
    }

    new_dataset.set(dataset_data)

    return dataset_data