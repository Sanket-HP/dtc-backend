"""Leaderboard routes for DataTrust Coin platform."""

from fastapi import APIRouter, Query
from google.cloud import firestore
from ..firebase_config import db

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


# -------------------------------------------------
# TOP CONTRIBUTORS (BY TOKEN BALANCE)
# -------------------------------------------------
@router.get("/contributors")
async def top_contributors(limit: int = 10):

    users = db.collection("users").stream()

    leaderboard = []

    for user_doc in users:

        user = user_doc.to_dict() or {}

        if user.get("status") == "deleted":
            continue

        user_id = user_doc.id

        # count datasets + token rewards
        datasets = (
            db.collection("datasets")
            .where("owner_id", "==", user_id)
            .stream()
        )

        dataset_count = 0
        total_tokens = 0

        for d in datasets:

            data = d.to_dict() or {}

            dataset_count += 1
            total_tokens += data.get("token_reward", 0)

        leaderboard.append({
            "user_id": user_id,
            "username": user.get("username", "anonymous"),
            "datasets_uploaded": dataset_count,
            "token_balance": round(total_tokens, 2)
        })

    leaderboard.sort(
        key=lambda x: x["token_balance"],
        reverse=True
    )

    return leaderboard[:limit]

# -------------------------------------------------
# TOP DATASET CREATORS
# -------------------------------------------------
@router.get("/creators")
async def top_dataset_creators(limit: int = Query(10, ge=1, le=50)):

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
    )[:limit]

    results = []

    for user_id, count in sorted_creators:

        user_doc = db.collection("users").document(user_id).get()

        if not user_doc.exists:
            continue

        user = user_doc.to_dict() or {}

        if user.get("status") == "deleted":
            continue

        results.append({
            "user_id": user_id,
            "username": user.get("username", "anonymous"),
            "datasets_uploaded": count,
            "token_balance": user.get("token_balance", 0),
            "tokens_earned": user.get("tokens_earned", 0)
        })

    return results


# -------------------------------------------------
# TOP DATASETS (BY QUALITY)
# -------------------------------------------------
@router.get("/datasets")
async def top_datasets(limit: int = Query(10, ge=1, le=50)):

    docs = db.collection("datasets").stream()

    datasets = []

    for d in docs:

        data = d.to_dict() or {}

        datasets.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "quality_score": data.get("quality_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "downloads": data.get("downloads", 0),
            "price": data.get("price", 0)
        })

    datasets.sort(key=lambda x: x["quality_score"], reverse=True)

    return datasets[:limit]


# -------------------------------------------------
# MOST DOWNLOADED DATASETS
# -------------------------------------------------
@router.get("/downloads")
async def most_downloaded_datasets(limit: int = Query(10, ge=1, le=50)):

    docs = db.collection("datasets").stream()

    datasets = []

    for d in docs:

        data = d.to_dict() or {}

        datasets.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "downloads": data.get("downloads", 0),
            "quality_score": data.get("quality_score", 0),
            "price": data.get("price", 0)
        })

    datasets.sort(key=lambda x: x["downloads"], reverse=True)

    return datasets[:limit]


# -------------------------------------------------
# HIGHEST RATED DATASETS
# -------------------------------------------------
@router.get("/ratings")
async def highest_rated_datasets(limit: int = Query(10, ge=1, le=50)):

    docs = db.collection("datasets").stream()

    datasets = []

    for d in docs:

        data = d.to_dict() or {}

        datasets.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "rating": data.get("rating", 0),
            "rating_count": data.get("rating_count", 0),
            "downloads": data.get("downloads", 0)
        })

    datasets.sort(key=lambda x: x["rating"], reverse=True)

    return datasets[:limit]


# -------------------------------------------------
# TOP AI DATASETS
# -------------------------------------------------
@router.get("/ai-datasets")
async def top_ai_datasets(limit: int = Query(10, ge=1, le=50)):

    docs = db.collection("datasets").stream()

    datasets = []

    for d in docs:

        data = d.to_dict() or {}

        datasets.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "ai_training_score": data.get("ai_training_score", 0),
            "quality_score": data.get("quality_score", 0),
            "downloads": data.get("downloads", 0)
        })

    datasets.sort(key=lambda x: x["ai_training_score"], reverse=True)

    return datasets[:limit]


# -------------------------------------------------
# HIGHEST VALUE DATASETS
# -------------------------------------------------
@router.get("/value")
async def highest_value_datasets(limit: int = Query(10, ge=1, le=50)):

    docs = db.collection("datasets").stream()

    datasets = []

    for d in docs:

        data = d.to_dict() or {}

        datasets.append({
            "dataset_id": d.id,
            "title": data.get("title"),
            "dataset_value": data.get("dataset_value", 0),
            "quality_score": data.get("quality_score", 0),
            "downloads": data.get("downloads", 0),
            "price": data.get("price", 0)
        })

    datasets.sort(key=lambda x: x["dataset_value"], reverse=True)

    return datasets[:limit]