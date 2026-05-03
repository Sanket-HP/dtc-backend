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
import math
from ..firebase_config import db


# -------------------------------------------------
# CATEGORY RARITY SCORE
# -------------------------------------------------
def category_rarity(category: str):

    docs = (
        db.collection("datasets")
        .where("category", "==", category)
        .limit(200)   # performance protection
        .stream()
    )

    count = len(list(docs))

    # fewer datasets → higher rarity
    if count < 5:
        return 1.0
    if count < 20:
        return 0.85
    if count < 50:
        return 0.7
    if count < 100:
        return 0.55

    return 0.4


# -------------------------------------------------
# DEMAND SCORE (DOWNLOADS)
# -------------------------------------------------
def demand_score(downloads: int):

    if downloads <= 0:
        return 0.2
    if downloads < 5:
        return 0.35
    if downloads < 20:
        return 0.55
    if downloads < 100:
        return 0.8
    if downloads < 500:
        return 0.9

    return 1.0


# -------------------------------------------------
# DATASET SIZE SCORE
# -------------------------------------------------
def size_score(records: int):

    # logarithmic scaling to prevent farming
    score = math.log(records + 1, 10)

    if score < 1:
        return 0.25
    if score < 2:
        return 0.5
    if score < 3:
        return 0.75

    return 1.0


# -------------------------------------------------
# DATASET FRESHNESS SCORE
# -------------------------------------------------
def freshness_score(created_at):

    if not created_at:
        return 0.6

    if isinstance(created_at, str):
        return 0.6

    try:
        age_days = (datetime.now(timezone.utc) - created_at).days
    except Exception:
        return 0.6

    if age_days < 7:
        return 1.0
    if age_days < 30:
        return 0.9
    if age_days < 90:
        return 0.75
    if age_days < 180:
        return 0.6

    return 0.45


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

    # safety clamp
    dataset_value = max(dataset_value, 0.05)

    return round(min(dataset_value, 1.0), 3)


# -------------------------------------------------
# TOKEN REWARD CALCULATION
# -------------------------------------------------
def compute_token_reward(
    record_count: int,
    dataset_value: float
):

    # base reward using logarithmic scaling
    base_tokens = math.log(record_count + 1) * 10

    reward = base_tokens * dataset_value

    # prevent token farming
    if reward > 5000:
        reward = 5000

    # minimum reward guarantee
    if reward < 1:
        reward = 1

    return round(reward, 2)