"""Anti-spam and anti-token-farming checks for uploaded datasets."""

import json
import math
import random
from collections import Counter


# -------------------------------------------------
# SAFE VALUE NORMALIZATION
# -------------------------------------------------
def normalize_value(v):

    if v is None:
        return "NULL"

    return str(v).strip()


# -------------------------------------------------
# LOW ENTROPY DETECTION
# -------------------------------------------------
def detect_low_entropy(rows):

    values = []

    for r in rows:
        values.extend([normalize_value(v) for v in r.values()])

    if len(values) == 0:
        return True

    counter = Counter(values)

    entropy = 0

    total = len(values)

    for c in counter.values():

        p = c / total

        if p > 0:
            entropy -= p * math.log2(p)

    # repetitive values → low entropy
    return entropy < 1.0


# -------------------------------------------------
# TOO MANY DUPLICATES
# -------------------------------------------------
def detect_duplicate_rows(rows):

    if not rows:
        return True

    normalized = [json.dumps(r, sort_keys=True) for r in rows]

    unique_rows = len(set(normalized))

    duplicate_ratio = 1 - (unique_rows / len(rows))

    return duplicate_ratio > 0.7


# -------------------------------------------------
# CONSTANT COLUMN DETECTION
# -------------------------------------------------
def detect_constant_columns(rows):

    if not rows:
        return True

    columns = rows[0].keys()

    constant_columns = 0

    for col in columns:

        values = set(normalize_value(r.get(col)) for r in rows)

        if len(values) <= 1:
            constant_columns += 1

    return constant_columns >= len(columns) * 0.6


# -------------------------------------------------
# SMALL DATASET DETECTION
# -------------------------------------------------
def detect_too_small(rows):

    return len(rows) < 10


# -------------------------------------------------
# COLUMN DIVERSITY CHECK
# -------------------------------------------------
def detect_low_column_diversity(rows):

    if not rows:
        return True

    columns = rows[0].keys()

    diversity_score = 0

    for col in columns:

        values = set(normalize_value(r.get(col)) for r in rows)

        diversity_score += len(values)

    avg_diversity = diversity_score / len(columns)

    return avg_diversity < 2


# -------------------------------------------------
# SYNTHETIC DATA PATTERN DETECTION
# -------------------------------------------------
def detect_synthetic_patterns(rows):

    sample = rows[:100]

    patterns = []

    for r in sample:
        patterns.append(tuple(normalize_value(v) for v in r.values()))

    counter = Counter(patterns)

    most_common = counter.most_common(1)

    if most_common and most_common[0][1] > len(sample) * 0.5:
        return True

    return False


# -------------------------------------------------
# NUMERIC RANDOMNESS CHECK
# -------------------------------------------------
def detect_fake_numeric_patterns(rows):

    numeric_values = []

    for r in rows:

        for v in r.values():

            try:
                numeric_values.append(float(v))
            except Exception:
                continue

    if len(numeric_values) < 20:
        return False

    mean = sum(numeric_values) / len(numeric_values)

    variance = sum(
        (x - mean) ** 2
        for x in numeric_values
    ) / len(numeric_values)

    return variance < 0.0001


# -------------------------------------------------
# ROW SIMILARITY CHECK
# -------------------------------------------------
def detect_row_similarity(rows):

    if len(rows) < 20:
        return False

    sample = rows[:100]

    similarities = 0

    for _ in range(20):

        a = random.choice(sample)
        b = random.choice(sample)

        if a == b:
            similarities += 1

    return similarities > 10


# -------------------------------------------------
# COLUMN TYPE CONSISTENCY CHECK
# -------------------------------------------------
def detect_column_type_anomaly(rows):

    if not rows:
        return False

    columns = rows[0].keys()

    anomalies = 0

    for col in columns:

        types = set(type(r.get(col)).__name__ for r in rows if col in r)

        if len(types) > 3:
            anomalies += 1

    return anomalies > len(columns) * 0.3


# -------------------------------------------------
# MAIN SPAM DETECTOR
# -------------------------------------------------
def is_spam_dataset(rows):

    if detect_too_small(rows):
        return True

    if detect_low_entropy(rows):
        return True

    if detect_duplicate_rows(rows):
        return True

    if detect_constant_columns(rows):
        return True

    if detect_low_column_diversity(rows):
        return True

    if detect_synthetic_patterns(rows):
        return True

    if detect_fake_numeric_patterns(rows):
        return True

    if detect_row_similarity(rows):
        return True

    if detect_column_type_anomaly(rows):
        return True

    return False