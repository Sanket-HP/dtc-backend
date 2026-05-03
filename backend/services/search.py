"""Dataset search service for DataTrust Coin.

Provides:
- smart search with relevance ranking
- category filtering
- trending datasets
- high quality datasets
- trusted datasets
"""

from ..firebase_config import db


# -------------------------------------------------
# SMART DATASET SEARCH WITH RELEVANCE SCORING
# -------------------------------------------------
def search_datasets(query: str):

    query = query.lower()

    docs = db.collection("datasets").stream()

    ranked_results = []

    for d in docs:

        data = d.to_dict()

        title = str(data.get("title", "")).lower()
        description = str(data.get("description", "")).lower()
        category = str(data.get("category", "")).lower()

        quality = data.get("quality_score", 0)
        trust = data.get("trust_score", 0)
        ai_score = data.get("ai_training_score", 0)
        downloads = data.get("download_count", 0)
        dataset_value = data.get("dataset_value", 0)

        score = 0

        # title match (highest weight)
        if query in title:
            score += 3

        # description match
        if query in description:
            score += 2

        # category match
        if query in category:
            score += 1

        if score > 0:

            ranking_score = (
                score +
                (quality * 2) +
                (trust * 1.5) +
                (ai_score * 2) +
                (downloads * 0.01) +
                (dataset_value * 0.5)
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
                "download_count": downloads,
                "rating": data.get("rating", 0)
            })

    ranked_results.sort(key=lambda x: x["ranking"], reverse=True)

    return ranked_results


# -------------------------------------------------
# FILTER DATASETS BY CATEGORY
# -------------------------------------------------
def filter_by_category(category: str):

    docs = (
        db.collection("datasets")
        .where("category", "==", category)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict()

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "description": data.get("description"),
            "record_count": data.get("record_count", 0),
            "quality_score": data.get("quality_score", 0),
            "trust_score": data.get("trust_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "download_count": data.get("download_count", 0),
            "dataset_value": data.get("dataset_value", 0)
        })

    return results


# -------------------------------------------------
# TRENDING DATASETS (Most Downloaded)
# -------------------------------------------------
def trending_datasets():

    docs = (
        db.collection("datasets")
        .order_by("download_count", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict()

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "download_count": data.get("download_count", 0),
            "trust_score": data.get("trust_score", 0),
            "quality_score": data.get("quality_score", 0),
            "ai_training_score": data.get("ai_training_score", 0)
        })

    return results


# -------------------------------------------------
# BEST QUALITY DATASETS
# -------------------------------------------------
def best_quality_datasets():

    docs = (
        db.collection("datasets")
        .order_by("quality_score", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict()

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "quality_score": data.get("quality_score", 0),
            "trust_score": data.get("trust_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "record_count": data.get("record_count", 0)
        })

    return results


# -------------------------------------------------
# MOST TRUSTED DATASETS
# -------------------------------------------------
def most_trusted_datasets():

    docs = (
        db.collection("datasets")
        .order_by("trust_score", direction="DESCENDING")
        .limit(10)
        .stream()
    )

    results = []

    for d in docs:

        data = d.to_dict()

        results.append({
            "id": d.id,
            "title": data.get("title"),
            "category": data.get("category"),
            "trust_score": data.get("trust_score", 0),
            "quality_score": data.get("quality_score", 0),
            "ai_training_score": data.get("ai_training_score", 0),
            "download_count": data.get("download_count", 0)
        })

    return results