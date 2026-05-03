"""Anti-spam and anti-token-farming checks for uploaded datasets."""

import json
import math
import random
from collections import Counter


# -------------------------------------------------
# LOW ENTROPY DETECTION
# -------------------------------------------------
def detect_low_entropy(rows):

    values = []

    for r in rows:
        values.extend(list(r.values()))

    if len(values) == 0:
        return True

    counter = Counter(values)

    entropy = 0

    for c in counter.values():
        p = c / len(values)
        entropy -= p * math.log2(p)

    # repetitive values → low entropy
    if entropy < 1.0:
        return True

    return False


# -------------------------------------------------
# TOO MANY DUPLICATES
# -------------------------------------------------
def detect_duplicate_rows(rows):

    if len(rows) == 0:
        return True

    unique_rows = set(json.dumps(r, sort_keys=True) for r in rows)

    duplicate_ratio = 1 - (len(unique_rows) / len(rows))

    if duplicate_ratio > 0.7:
        return True

    return False


# -------------------------------------------------
# CONSTANT COLUMN DETECTION
# -------------------------------------------------
def detect_constant_columns(rows):

    if len(rows) == 0:
        return True

    columns = rows[0].keys()

    constant_columns = 0

    for col in columns:

        values = set(r.get(col) for r in rows)

        if len(values) == 1:
            constant_columns += 1

    if constant_columns >= len(columns) * 0.6:
        return True

    return False


# -------------------------------------------------
# SMALL DATASET DETECTION
# -------------------------------------------------
def detect_too_small(rows):

    if len(rows) < 10:
        return True

    return False


# -------------------------------------------------
# COLUMN DIVERSITY CHECK
# -------------------------------------------------
def detect_low_column_diversity(rows):

    if len(rows) == 0:
        return True

    columns = rows[0].keys()

    diversity_score = 0

    for col in columns:

        values = set(r.get(col) for r in rows)

        diversity_score += len(values)

    avg_diversity = diversity_score / len(columns)

    if avg_diversity < 2:
        return True

    return False


# -------------------------------------------------
# SYNTHETIC DATA PATTERN DETECTION
# -------------------------------------------------
def detect_synthetic_patterns(rows):

    sample = rows[:50]

    patterns = []

    for r in sample:
        patterns.append(tuple(r.values()))

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

            if isinstance(v, (int, float)):
                numeric_values.append(v)

    if len(numeric_values) < 20:
        return False

    variance = sum(
        (x - sum(numeric_values) / len(numeric_values)) ** 2
        for x in numeric_values
    ) / len(numeric_values)

    if variance < 0.0001:
        return True

    return False


# -------------------------------------------------
# RANDOM SHUFFLE SIMILARITY CHECK
# -------------------------------------------------
def detect_row_similarity(rows):

    if len(rows) < 20:
        return False

    sample = rows[:50]

    similarities = 0

    for _ in range(10):

        a = random.choice(sample)
        b = random.choice(sample)

        if a == b:
            similarities += 1

    if similarities > 6:
        return True

    return False


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

    return False