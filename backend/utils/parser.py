"""Dataset file parser – reads CSV and JSON uploads into row dicts."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def parse_csv(content: bytes | str) -> list[dict[str, Any]]:
    """Parse CSV bytes/string into a list of row dicts."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append({k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()})
    return rows


def parse_json(content: bytes | str) -> list[dict[str, Any]]:
    """Parse JSON bytes/string into a list of row dicts.

    Accepts a JSON array of objects, or a single object (wrapped in a list).
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    data = json.loads(content)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of objects or a single object.")
    return data


def detect_format(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".json"):
        return "json"
    raise ValueError(f"Unsupported file format: {filename}")


def parse_file(content: bytes | str, filename: str) -> list[dict[str, Any]]:
    fmt = detect_format(filename)
    if fmt == "csv":
        return parse_csv(content)
    return parse_json(content)
