"""User profile, wallet, reputation and analytics routes."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from ..firebase_config import db
from .deps import get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])


# -------------------------------------------------
# GET CURRENT USER PROFILE
# -------------------------------------------------
@router.get("/me")
async def get_my_profile(user_id: str = Depends(get_current_user_id)):

    doc = db.collection("users").document(user_id).get()

    if not doc.exists:
        raise HTTPException(404, "User not found")

    data = doc.to_dict()
    data["id"] = user_id

    return data


# -------------------------------------------------
# USER WALLET BALANCE
# -------------------------------------------------
@router.get("/wallet")
async def get_wallet(user_id: str = Depends(get_current_user_id)):

    doc = db.collection("users").document(user_id).get()

    if not doc.exists:
        raise HTTPException(404, "User not found")

    user = doc.to_dict()

    return {
        "user_id": user_id,
        "token_balance": user.get("token_balance", 0),
        "updated_at": user.get("updated_at", datetime.now(timezone.utc))
    }


# -------------------------------------------------
# USER DATASETS
# -------------------------------------------------
@router.get("/datasets")
async def get_user_datasets(user_id: str = Depends(get_current_user_id)):

    docs = (
        db.collection("datasets")
        .where("owner_id", "==", user_id)
        .stream()
    )

    datasets = []

    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        datasets.append(data)

    return datasets


# -------------------------------------------------
# USER TRANSACTIONS
# -------------------------------------------------
@router.get("/transactions")
async def get_transactions(user_id: str = Depends(get_current_user_id)):

    docs = (
        db.collection("transactions")
        .where("user_id", "==", user_id)
        .order_by("created_at", direction="DESCENDING")
        .limit(50)
        .stream()
    )

    transactions = []

    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        transactions.append(data)

    return transactions


# -------------------------------------------------
# USER REPUTATION SCORE
# -------------------------------------------------
@router.get("/reputation")
async def get_reputation(user_id: str = Depends(get_current_user_id)):

    datasets = (
        db.collection("datasets")
        .where("owner_id", "==", user_id)
        .stream()
    )

    total_quality = 0
    total_ai_score = 0
    dataset_count = 0
    downloads = 0

    for d in datasets:

        data = d.to_dict()

        total_quality += data.get("quality_score", 0)
        total_ai_score += data.get("ai_training_score", 0)
        downloads += data.get("download_count", 0)
        dataset_count += 1

    reputation = 0

    if dataset_count > 0:

        avg_quality = total_quality / dataset_count
        avg_ai_score = total_ai_score / dataset_count

        reputation = round(
            (avg_quality * 40) +
            (avg_ai_score * 30) +
            min(downloads / 10, 30),
            2
        )

    # Contributor badge system
    badge = "Beginner"

    if reputation > 90:
        badge = "Elite Data Architect"

    elif reputation > 70:
        badge = "Trusted Data Scientist"

    elif reputation > 50:
        badge = "Rising Researcher"

    elif reputation > 30:
        badge = "Active Contributor"

    return {
        "user_id": user_id,
        "datasets_uploaded": dataset_count,
        "total_downloads": downloads,
        "reputation_score": reputation,
        "badge": badge
    }


# -------------------------------------------------
# USER ANALYTICS
# -------------------------------------------------
@router.get("/analytics")
async def user_analytics(user_id: str = Depends(get_current_user_id)):

    datasets = (
        db.collection("datasets")
        .where("owner_id", "==", user_id)
        .stream()
    )

    dataset_count = 0
    total_records = 0
    total_downloads = 0
    total_value = 0

    for d in datasets:

        data = d.to_dict()

        dataset_count += 1
        total_records += data.get("record_count", 0)
        total_downloads += data.get("download_count", 0)
        total_value += data.get("dataset_value", 0)

    return {
        "datasets_uploaded": dataset_count,
        "records_contributed": total_records,
        "total_downloads": total_downloads,
        "total_dataset_value": round(total_value, 2)
    }


# -------------------------------------------------
# PUBLIC USER PROFILE
# -------------------------------------------------
@router.get("/{user_id}")
async def get_public_profile(user_id: str):

    doc = db.collection("users").document(user_id).get()

    if not doc.exists:
        raise HTTPException(404, "User not found")

    data = doc.to_dict()

    return {
        "username": data.get("username"),
        "full_name": data.get("full_name"),
        "token_balance": data.get("token_balance", 0),
        "is_company": data.get("is_company", False),
        "created_at": data.get("created_at")
    }