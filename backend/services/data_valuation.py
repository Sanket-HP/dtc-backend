"""Dataset valuation engine for DataTrust Coin.

Calculates dataset market value based on:
- AI training usefulness
- dataset quality
- dataset demand
- category rarity
- dataset size
- dataset freshness
"""

from datetime import datetime, timezone
from ..firebase_config import db


# -------------------------------------------------
# CATEGORY RARITY SCORE
# -------------------------------------------------
def category_rarity(category: str):

    docs = (
        db.collection("datasets")
        .where("category", "==", category)
        .stream()
    )

    count = len(list(docs))

    # fewer datasets → higher rarity
    if count < 5:
        return 1.0

    if count < 20:
        return 0.8

    if count < 100:
        return 0.6

    return 0.4


# -------------------------------------------------
# DEMAND SCORE (DOWNLOADS)
# -------------------------------------------------
def demand_score(downloads: int):

    if downloads < 5:
        return 0.2

    if downloads < 20:
        return 0.5

    if downloads < 100:
        return 0.8

    return 1.0


# -------------------------------------------------
# DATASET SIZE SCORE
# -------------------------------------------------
def size_score(records: int):

    if records < 100:
        return 0.2

    if records < 1000:
        return 0.5

    if records < 10000:
        return 0.8

    return 1.0


# -------------------------------------------------
# DATASET FRESHNESS SCORE
# -------------------------------------------------
def freshness_score(created_at):

    if not created_at:
        return 0.5

    if isinstance(created_at, str):
        return 0.5

    age_days = (datetime.now(timezone.utc) - created_at).days

    if age_days < 7:
        return 1.0

    if age_days < 30:
        return 0.8

    if age_days < 180:
        return 0.6

    return 0.4


# -------------------------------------------------
# MAIN DATASET VALUATION
# -------------------------------------------------
def compute_dataset_value(
    record_count: int,
    quality_score: float,
    ai_score: float,
    category: str,
    downloads: int = 0,
    created_at=None
):

    rarity = category_rarity(category)

    demand = demand_score(downloads)

    size = size_score(record_count)

    freshness = freshness_score(created_at)

    dataset_value = (
        ai_score * 0.35 +
        quality_score * 0.25 +
        demand * 0.15 +
        rarity * 0.10 +
        size * 0.10 +
        freshness * 0.05
    )

    return round(min(dataset_value, 1), 3)


# -------------------------------------------------
# TOKEN REWARD CALCULATION
# -------------------------------------------------
def compute_token_reward(
    record_count: int,
    dataset_value: float
):

    # base reward per record
    base_tokens = record_count * 0.2

    reward = base_tokens * dataset_value

    # prevent extreme farming
    reward = min(reward, 5000)

    return round(reward, 2)