"""Dataset anonymization – strips PII columns from tabular data."""

from __future__ import annotations

import re
from typing import Any

from ..config import PII_FIELDS


def _normalize(name: str) -> str:
    return re.sub(r"[\s\-_]+", "_", name.strip().lower())


def is_pii_field(field_name: str) -> bool:
    return _normalize(field_name) in PII_FIELDS


def anonymize_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Remove PII fields from a list of dicts.

    Returns (cleaned_records, list_of_removed_field_names).
    """
    if not records:
        return [], []

    all_fields = set()
    for rec in records:
        all_fields.update(rec.keys())

    removed = sorted(f for f in all_fields if is_pii_field(f))
    keep = [f for f in all_fields if not is_pii_field(f)]

    cleaned: list[dict[str, Any]] = []
    for rec in records:
        cleaned.append({k: rec.get(k) for k in keep})

    return cleaned, removed
