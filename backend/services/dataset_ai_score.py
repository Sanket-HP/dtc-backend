"""AI dataset usefulness scoring service.

Evaluates datasets for AI / ML training usefulness.

Scoring considers:
- feature diversity
- numeric features
- text features
- label column presence
- entropy (data randomness)
- dataset size
- feature richness
"""

import math
from collections import Counter


# -------------------------------------------------
# FEATURE DIVERSITY
# -------------------------------------------------
def feature_diversity(rows):

    if not rows:
        return 0

    columns = rows[0].keys()

    diversity_score = 0

    for col in columns:

        values = [r.get(col) for r in rows]

        unique = len(set(values))

        diversity_score += unique

    avg_diversity = diversity_score / len(columns)

    # normalize
    return min(avg_diversity / 50, 1)


# -------------------------------------------------
# NUMERIC FEATURE DETECTION
# -------------------------------------------------
def numeric_feature_ratio(rows):

    if not rows:
        return 0

    columns = rows[0].keys()

    numeric_columns = 0

    for col in columns:

        numeric_count = 0

        for r in rows:

            value = r.get(col)

            if isinstance(value, (int, float)):
                numeric_count += 1

        if numeric_count > len(rows) * 0.5:
            numeric_columns += 1

    return numeric_columns / len(columns)


# -------------------------------------------------
# TEXT FEATURE DETECTION
# -------------------------------------------------
def text_feature_ratio(rows):

    if not rows:
        return 0

    columns = rows[0].keys()

    text_columns = 0

    for col in columns:

        text_count = 0

        for r in rows:

            value = r.get(col)

            if isinstance(value, str):
                text_count += 1

        if text_count > len(rows) * 0.5:
            text_columns += 1

    return text_columns / len(columns)


# -------------------------------------------------
# LABEL COLUMN DETECTION
# -------------------------------------------------
def detect_label_column(rows):

    if not rows:
        return False

    columns = rows[0].keys()

    for col in columns:

        values = [r.get(col) for r in rows]

        unique = len(set(values))

        if 2 <= unique <= 20:
            return True

    return False


# -------------------------------------------------
# DISTRIBUTION ENTROPY
# -------------------------------------------------
def entropy_score(rows):

    values = []

    for r in rows:
        values.extend(list(r.values()))

    if not values:
        return 0

    counter = Counter(values)

    entropy = 0

    total = len(values)

    for c in counter.values():

        p = c / total

        entropy -= p * math.log2(p)

    # normalize
    return min(entropy / 6, 1)


# -------------------------------------------------
# DATASET SIZE SCORE
# -------------------------------------------------
def size_score(rows):

    n = len(rows)

    if n < 100:
        return 0.2

    if n < 1000:
        return 0.5

    if n < 10000:
        return 0.8

    return 1.0


# -------------------------------------------------
# FEATURE RICHNESS
# -------------------------------------------------
def feature_richness(rows):

    if not rows:
        return 0

    columns = len(rows[0].keys())

    if columns < 3:
        return 0.3

    if columns < 10:
        return 0.6

    if columns < 30:
        return 0.8

    return 1.0


# -------------------------------------------------
# MAIN AI TRAINING SCORE
# -------------------------------------------------
def compute_ai_score(rows):

    if not rows:
        return 0

    diversity = feature_diversity(rows)

    numeric_ratio = numeric_feature_ratio(rows)

    text_ratio = text_feature_ratio(rows)

    label_present = detect_label_column(rows)

    entropy = entropy_score(rows)

    size = size_score(rows)

    richness = feature_richness(rows)

    label_score = 1 if label_present else 0.3

    ai_score = (
        diversity * 0.20 +
        numeric_ratio * 0.15 +
        text_ratio * 0.10 +
        label_score * 0.20 +
        entropy * 0.15 +
        size * 0.10 +
        richness * 0.10
    )

    return round(min(ai_score, 1), 2)