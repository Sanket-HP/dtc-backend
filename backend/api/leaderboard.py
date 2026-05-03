"""Leaderboard routes for DataTrust Coin platform."""

from fastapi import APIRouter
from ..firebase_config import db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


# -------------------------------------------------
# TOP CONTRIBUTORS (ACTIVE USERS ONLY)
# -------------------------------------------------
@router.get("/contributors")
async def top_contributors():

    docs = (
        db.collection("users")
        .where("status", "==", "active")   # NEW FILTER
        .order_by("token_balance", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "user_id": d.id,
            "username": data.get("username", "anonymous"),
            "full_name": data.get("full_name"),
            "token_balance": data.get("token_balance", 0),
            "datasets_uploaded": data.get("datasets_uploaded", 0)
        })

    return results


# -------------------------------------------------
# TOP DATASET CREATORS
# -------------------------------------------------
@router.get("/creators")
async def top_dataset_creators():

    docs = db.collection("datasets").stream()

    creator_counts = {}

    for d in docs:

        data = d.to_dict() or {}

        owner = data.get("owner_id")

        if not owner:
            continue

        creator_counts[owner] = creator_counts.get(owner, 0) + 1

    sorted_creators = sorted(
        creator_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    results = []

    for user_id, count in sorted_creators:

        user_doc = db.collection("users").document(user_id).get()

        if user_doc.exists:

            user = user_doc.to_dict() or {}

            # ignore deleted users
            if user.get("status") != "active":
                continue

            results.append({
                "user_id": user_id,
                "username": user.get("username", "anonymous"),
                "datasets_uploaded": count,
                "token_balance": user.get("token_balance", 0)
            })

    return results


# -------------------------------------------------
# TOP DATASETS (BY TRUST SCORE)
# -------------------------------------------------
@router.get("/datasets")
async def top_datasets():

    docs = (
        db.collection("datasets")
        .order_by("trust_score", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "quality_score": data.get("quality_score", 0),
            "trust_score": data.get("trust_score", 0),
            "downloads": data.get("download_count", 0)
        })

    return results


# -------------------------------------------------
# MOST DOWNLOADED DATASETS
# -------------------------------------------------
@router.get("/downloads")
async def most_downloaded_datasets():

    docs = (
        db.collection("datasets")
        .order_by("download_count", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "download_count": data.get("download_count", 0),
            "trust_score": data.get("trust_score", 0)
        })

    return results


# -------------------------------------------------
# HIGHEST RATED DATASETS
# -------------------------------------------------
@router.get("/ratings")
async def highest_rated_datasets():

    docs = (
        db.collection("datasets")
        .order_by("rating", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "rating": data.get("rating", 0),
            "rating_count": data.get("rating_count", 0)
        })

    return results


# -------------------------------------------------
# TOP AI DATASETS
# -------------------------------------------------
@router.get("/ai-datasets")
async def top_ai_datasets():

    docs = (
        db.collection("datasets")
        .order_by("ai_training_score", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "ai_training_score": data.get("ai_training_score", 0),
            "quality_score": data.get("quality_score", 0)
        })

    return results


# -------------------------------------------------
# HIGHEST VALUE DATASETS
# -------------------------------------------------
@router.get("/value")
async def highest_value_datasets():

    docs = (
        db.collection("datasets")
        .order_by("dataset_value", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "dataset_value": data.get("dataset_value", 0),
            "quality_score": data.get("quality_score", 0),
            "download_count": data.get("download_count", 0)
        })

    return results