"""AI dataset validation service.

Detects:
- AI generated datasets
- synthetic/random datasets
- copied datasets
- low diversity datasets
- structural anomalies
"""

import json
import math
import hashlib
from collections import Counter


# -------------------------------------------------
# ENTROPY CHECK
# -------------------------------------------------
def calculate_entropy(values):

    if not values:
        return 0

    counter = Counter(values)

    entropy = 0

    total = len(values)

    for c in counter.values():

        p = c / total

        entropy -= p * math.log2(p)

    return entropy


# -------------------------------------------------
# LOW VARIANCE DETECTION
# -------------------------------------------------
def detect_low_variance(rows):

    if not rows:
        return True

    columns = rows[0].keys()

    low_variance_columns = 0

    for col in columns:

        values = [r.get(col) for r in rows]

        unique_values = set(values)

        if len(unique_values) <= 2:
            low_variance_columns += 1

    return low_variance_columns >= len(columns) * 0.6


# -------------------------------------------------
# RANDOM DATA DETECTION
# -------------------------------------------------
def detect_random_dataset(rows):

    values = []

    for r in rows:
        values.extend(list(r.values()))

    entropy = calculate_entropy(values)

    # extremely high entropy can indicate random data
    if entropy > 7:
        return True

    return False


# -------------------------------------------------
# COLUMN DIVERSITY
# -------------------------------------------------
def detect_low_diversity(rows):

    if not rows:
        return True

    columns = rows[0].keys()

    diversity = 0

    for col in columns:

        values = set(r.get(col) for r in rows)

        diversity += len(values)

    avg_diversity = diversity / len(columns)

    return avg_diversity < 3


# -------------------------------------------------
# AI GENERATED DATASET DETECTION
# -------------------------------------------------
def detect_ai_generated(rows):

    patterns = Counter()

    for r in rows[:100]:

        pattern = tuple(r.values())

        patterns[pattern] += 1

    most_common = patterns.most_common(1)

    if most_common and most_common[0][1] > 10:
        return True

    return False


# -------------------------------------------------
# STRUCTURAL ANOMALY DETECTION
# -------------------------------------------------
def detect_structure_anomaly(rows):

    if not rows:
        return True

    base_columns = set(rows[0].keys())

    mismatch = 0

    for r in rows:

        if set(r.keys()) != base_columns:
            mismatch += 1

    ratio = mismatch / len(rows)

    return ratio > 0.2


# -------------------------------------------------
# DATASET FINGERPRINT
# -------------------------------------------------
def dataset_fingerprint(rows):

    normalized = json.dumps(
        sorted(rows, key=lambda x: json.dumps(x, sort_keys=True)),
        sort_keys=True
    )

    return hashlib.sha256(normalized.encode()).hexdigest()


# -------------------------------------------------
# AI VALIDATION SCORE
# -------------------------------------------------
def compute_validation_score(issues):

    base_score = 1.0

    penalties = {
        "low_variance_columns": 0.2,
        "random_data_pattern": 0.25,
        "low_column_diversity": 0.2,
        "ai_generated_pattern": 0.25,
        "structure_anomaly": 0.15
    }

    for issue in issues:
        base_score -= penalties.get(issue, 0.1)

    return max(round(base_score, 2), 0)


# -------------------------------------------------
# MAIN VALIDATOR
# -------------------------------------------------
def validate_dataset(rows):

    problems = []

    if detect_low_variance(rows):
        problems.append("low_variance_columns")

    if detect_random_dataset(rows):
        problems.append("random_data_pattern")

    if detect_low_diversity(rows):
        problems.append("low_column_diversity")

    if detect_ai_generated(rows):
        problems.append("ai_generated_pattern")

    if detect_structure_anomaly(rows):
        problems.append("structure_anomaly")

    validation_score = compute_validation_score(problems)

    return {
        "valid": len(problems) == 0,
        "issues": problems,
        "validation_score": validation_score,
        "fingerprint": dataset_fingerprint(rows)
    }