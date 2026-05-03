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
        "record_count": data.get("record_count", 0),
        "quality_score": data.get("quality_score", 0),
        "trust_score": data.get("trust_score", 0),
        "ai_training_score": data.get("ai_training_score", 0),
        "dataset_value": data.get("dataset_value", 0),
        "downloads": data.get("download_count", 0),
        "rating": data.get("rating", 0)
    }


# -------------------------------------------------
# RANK DATASETS
# -------------------------------------------------
def ranking_score(data):

    quality = data.get("quality_score", 0)
    trust = data.get("trust_score", 0)
    ai_score = data.get("ai_training_score", 0)
    downloads = data.get("download_count", 0)
    value = data.get("dataset_value", 0)

    score = (
        (quality * 2) +
        (trust * 2) +
        (ai_score * 2) +
        (downloads * 0.02) +
        (value * 1.5)
    )

    return score


# -------------------------------------------------
# TRENDING DATASETS
# -------------------------------------------------
def trending_datasets(limit: int = 10):

    docs = db.collection("datasets").limit(200).stream()

    datasets = []

    for d in docs:

        data = d.to_dict()

        score = ranking_score(data)

        datasets.append((score, format_dataset(d)))

    datasets.sort(key=lambda x: x[0], reverse=True)

    return [d[1] for d in datasets[:limit]]


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
        .limit(200)
        .stream()
    )

    ranked = []

    for d in docs:

        data = d.to_dict()

        score = ranking_score(data)

        ranked.append((score, format_dataset(d)))

    ranked.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in ranked[:limit]]


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
        .limit(200)
        .stream()
    )

    ranked = []

    for d in docs:

        if d.id == dataset_id:
            continue

        data = d.to_dict()

        score = ranking_score(data)

        ranked.append((score, format_dataset(d)))

    ranked.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in ranked[:limit]]


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
            .limit(300)
            .stream()
        )

    else:

        docs = db.collection("datasets").limit(300).stream()

    ranked = []

    for d in docs:

        data = d.to_dict()

        score = ranking_score(data)

        ranked.append((score, format_dataset(d)))

    ranked.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in ranked[:limit]]