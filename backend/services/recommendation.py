"""Dataset recommendation engine for DataTrust Coin."""

from collections import Counter
from ..firebase_config import db


# -------------------------------------------------
# FORMAT DATASET OBJECT
# -------------------------------------------------
def format_dataset(doc):

    data = doc.to_dict()

    return {
        "id": doc.id,
        "title": data.get("title"),
        "category": data.get("category"),
        "quality_score": data.get("quality_score", 0),
        "trust_score": data.get("trust_score", 0),
        "downloads": data.get("download_count", 0),
        "rating": data.get("rating", 0)
    }


# -------------------------------------------------
# TRENDING DATASETS
# -------------------------------------------------
def trending_datasets(limit: int = 10):

    docs = (
        db.collection("datasets")
        .order_by("download_count", direction="DESCENDING")
        .limit(limit)
        .stream()
    )

    return [format_dataset(d) for d in docs]


# -------------------------------------------------
# HIGH QUALITY DATASETS
# -------------------------------------------------
def high_quality_datasets(limit: int = 10):

    docs = (
        db.collection("datasets")
        .order_by("quality_score", direction="DESCENDING")
        .limit(limit)
        .stream()
    )

    return [format_dataset(d) for d in docs]


# -------------------------------------------------
# MOST TRUSTED DATASETS
# -------------------------------------------------
def trusted_datasets(limit: int = 10):

    docs = (
        db.collection("datasets")
        .order_by("trust_score", direction="DESCENDING")
        .limit(limit)
        .stream()
    )

    return [format_dataset(d) for d in docs]


# -------------------------------------------------
# RECOMMEND DATASETS BY CATEGORY
# -------------------------------------------------
def recommend_by_category(category: str, limit: int = 10):

    docs = (
        db.collection("datasets")
        .where("category", "==", category)
        .order_by("trust_score", direction="DESCENDING")
        .limit(limit)
        .stream()
    )

    return [format_dataset(d) for d in docs]


# -------------------------------------------------
# SIMILAR DATASETS
# -------------------------------------------------
def similar_datasets(dataset_id: str, limit: int = 5):

    doc = db.collection("datasets").document(dataset_id).get()

    if not doc.exists:
        return []

    dataset = doc.to_dict()

    category = dataset.get("category")

    docs = (
        db.collection("datasets")
        .where("category", "==", category)
        .limit(limit + 1)
        .stream()
    )

    results = []

    for d in docs:

        if d.id == dataset_id:
            continue

        results.append(format_dataset(d))

    return results[:limit]


# -------------------------------------------------
# PERSONALIZED RECOMMENDATIONS
# -------------------------------------------------
def recommend_for_user(user_id: str, limit: int = 10):

    user_datasets = (
        db.collection("datasets")
        .where("owner_id", "==", user_id)
        .stream()
    )

    categories = []

    for d in user_datasets:

        data = d.to_dict()

        categories.append(data.get("category"))

    if not categories:
        return trending_datasets(limit)

    most_common = Counter(categories).most_common(1)[0][0]

    return recommend_by_category(most_common, limit)


# -------------------------------------------------
# ENTERPRISE DATASET DISCOVERY
# -------------------------------------------------
def enterprise_recommendations(category: str | None = None, limit: int = 20):

    if category:

        docs = (
            db.collection("datasets")
            .where("category", "==", category)
            .order_by("trust_score", direction="DESCENDING")
            .limit(limit)
            .stream()
        )

    else:

        docs = (
            db.collection("datasets")
            .order_by("trust_score", direction="DESCENDING")
            .limit(limit)
            .stream()
        )

    return [format_dataset(d) for d in docs]