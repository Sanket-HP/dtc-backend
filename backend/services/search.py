"""Dataset search service for DataTrust Coin.

Provides:
- smart search with relevance ranking
- category filtering
- trending datasets
- high quality datasets
- trusted datasets
"""

from ..firebase_config import db
from google.cloud import firestore


# -------------------------------------------------
# SMART DATASET SEARCH WITH RELEVANCE SCORING
# -------------------------------------------------
def search_datasets(query: str, limit: int = 25):

    query = str(query).lower().strip()

    docs = db.collection("datasets").limit(500).stream()

    ranked_results = []

    for d in docs:

        data = d.to_dict() or {}

        title = str(data.get("title", "")).lower()
        description = str(data.get("description", "")).lower()
        category = str(data.get("category", "")).lower()

        quality = float(data.get("quality_score", 0))
        trust = float(data.get("trust_score", 0))
        ai_score = float(data.get("ai_training_score", 0))
        downloads = int(data.get("downloads", 0))
        dataset_value = float(data.get("dataset_value", 0))
        rating = float(data.get("rating", 0))
        price = float(data.get("price", 0))

        score = 0

        # title match (highest relevance)
        if query in title:
            score += 6

        # description match
        if query in description:
            score += 3

        # category match
        if query in category:
            score += 2

        if score > 0:

            ranking_score = (
                score +
                (quality * 2.5) +
                (trust * 1.8) +
                (ai_score * 2) +
                (rating * 1.5) +
                (downloads * 0.02) +
                (dataset_value * 0.6)
            )

            ranked_results.append({
                "ranking": ranking_score,
                "id": d.id,
                "title": data.get("title"),
                "description": data.get("description"),
                "category": data.get("category"),
                "record_count": data.get("record_count", 0),
                "quality_score": quality,
                "trust_score": trust,
                "ai_training_score": ai_score,
                "dataset_value": dataset_value,
                "downloads": downloads,
                "rating": rating,
                "price": price
            })

    ranked_results.sort(key=lambda x: x["ranking"], reverse=True)

    return ranked_results[:limit]


# -------------------------------------------------
# FILTER DATASETS BY CATEGORY
# -------------------------------------------------
def filter_by_category(category: str, limit: int = 50):

    docs = (
        db.collection("datasets")
        .where("category", "==", category)
        .limit(limit)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "description": data.get("description"),
            "record_count": data.get("record_count", 0),
            "quality_score": data.get("quality_score", 0),
            "trust_score": data.get("trust_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "downloads": data.get("downloads", 0),
            "dataset_value": data.get("dataset_value", 0),
            "price": data.get("price", 0),
            "rating": data.get("rating", 0)
        })

    return results


# -------------------------------------------------
# TRENDING DATASETS (Most Downloaded)
# -------------------------------------------------
def trending_datasets(limit: int = 10):

    docs = (
        db.collection("datasets")
        .order_by("downloads", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "downloads": data.get("downloads", 0),
            "trust_score": data.get("trust_score", 0),
            "quality_score": data.get("quality_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "price": data.get("price", 0)
        })

    return results


# -------------------------------------------------
# BEST QUALITY DATASETS
# -------------------------------------------------
def best_quality_datasets(limit: int = 10):

    docs = (
        db.collection("datasets")
        .order_by("quality_score", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "quality_score": data.get("quality_score", 0),
            "trust_score": data.get("trust_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "record_count": data.get("record_count", 0),
            "price": data.get("price", 0)
        })

    return results


# -------------------------------------------------
# MOST TRUSTED DATASETS
# -------------------------------------------------
def most_trusted_datasets(limit: int = 10):

    docs = (
        db.collection("datasets")
        .order_by("trust_score", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict() or {}

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "trust_score": data.get("trust_score", 0),
            "quality_score": data.get("quality_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "downloads": data.get("downloads", 0),
            "price": data.get("price", 0)
        })

    return results