"""Core dataset processing service."""

from __future__ import annotations

import csv
import io
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import STORAGE_DIR, TOKENS_PER_RECORD
from ..models.dataset import Dataset
from ..models.user import User
from ..utils.anonymizer import anonymize_records
from ..utils.parser import parse_file


async def process_and_store(
    db: AsyncSession,
    owner_id: str,
    title: str,
    description: str,
    category: str,
    raw_content: bytes,
    original_filename: str,
) -> Dataset:
    """Parse, anonymize, store, and record a dataset upload."""
    records = parse_file(raw_content, original_filename)
    if not records:
        raise ValueError("The uploaded file contains no records.")

    cleaned, removed_fields = anonymize_records(records)

    dataset_id = str(uuid.uuid4())
    fmt = "csv" if original_filename.lower().endswith(".csv") else "json"
    stored_filename = f"{dataset_id}.{fmt}"
    dest = STORAGE_DIR / stored_filename

    if fmt == "csv":
        _write_csv(cleaned, dest)
    else:
        _write_json(cleaned, dest)

    fields = sorted({k for rec in cleaned for k in rec.keys()})
    sample = cleaned[:5]
    record_count = len(cleaned)
    reward = round(record_count * TOKENS_PER_RECORD, 2)

    price = round(reward * 2, 2)

    ds = Dataset(
        id=dataset_id,
        owner_id=owner_id,
        title=title,
        description=description,
        category=category,
        file_path=str(dest),
        original_filename=original_filename,
        file_format=fmt,
        record_count=record_count,
        fields=json.dumps(fields),
        sample_data=json.dumps(sample, default=str),
        token_reward=reward,
        price=price,
        status="processed",
    )
    db.add(ds)

    user = await db.get(User, owner_id)
    if user:
        user.token_balance = (user.token_balance or 0) + reward

    await db.commit()
    await db.refresh(ds)
    return ds


async def process_manual_input(
    db: AsyncSession,
    owner_id: str,
    title: str,
    description: str,
    category: str,
    records: list[dict[str, Any]],
) -> Dataset:
    """Process manually entered records."""
    if not records:
        raise ValueError("No records provided.")

    cleaned, _ = anonymize_records(records)

    dataset_id = str(uuid.uuid4())
    stored_filename = f"{dataset_id}.json"
    dest = STORAGE_DIR / stored_filename
    _write_json(cleaned, dest)

    fields = sorted({k for rec in cleaned for k in rec.keys()})
    sample = cleaned[:5]
    record_count = len(cleaned)
    reward = round(record_count * TOKENS_PER_RECORD, 2)
    price = round(reward * 2, 2)

    ds = Dataset(
        id=dataset_id,
        owner_id=owner_id,
        title=title,
        description=description,
        category=category,
        file_path=str(dest),
        original_filename="manual_input.json",
        file_format="json",
        record_count=record_count,
        fields=json.dumps(fields),
        sample_data=json.dumps(sample, default=str),
        token_reward=reward,
        price=price,
        status="processed",
    )
    db.add(ds)

    user = await db.get(User, owner_id)
    if user:
        user.token_balance = (user.token_balance or 0) + reward

    await db.commit()
    await db.refresh(ds)
    return ds


async def build_aggregated_dataset(
    db: AsyncSession,
    category: str,
    title: str,
    description: str,
    admin_id: str,
) -> Dataset:
    """Merge all datasets in a category into one aggregated dataset."""
    stmt = select(Dataset).where(
        Dataset.category == category,
        Dataset.is_aggregated == False,  # noqa: E712
        Dataset.status == "processed",
    )
    result = await db.execute(stmt)
    sources = result.scalars().all()

    if not sources:
        raise ValueError(f"No source datasets found for category '{category}'.")

    all_records: list[dict[str, Any]] = []
    for src in sources:
        path = Path(src.file_path)
        if not path.exists():
            continue
        raw = path.read_bytes()
        if src.file_format == "csv":
            from ..utils.parser import parse_csv
            all_records.extend(parse_csv(raw))
        else:
            from ..utils.parser import parse_json
            all_records.extend(parse_json(raw))

    if not all_records:
        raise ValueError("Source datasets contain no readable records.")

    dataset_id = str(uuid.uuid4())
    dest = STORAGE_DIR / f"{dataset_id}.csv"
    _write_csv(all_records, dest)

    fields = sorted({k for r in all_records for k in r.keys()})
    sample = all_records[:5]
    record_count = len(all_records)
    price = round(record_count * TOKENS_PER_RECORD * 2, 2)

    ds = Dataset(
        id=dataset_id,
        owner_id=admin_id,
        title=title,
        description=description,
        category=category,
        file_path=str(dest),
        original_filename=f"aggregated_{category}.csv",
        file_format="csv",
        record_count=record_count,
        fields=json.dumps(fields),
        sample_data=json.dumps(sample, default=str),
        token_reward=0,
        price=price,
        is_aggregated=True,
        status="processed",
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return ds


def _write_csv(records: list[dict[str, Any]], path: Path) -> None:
    if not records:
        path.write_text("")
        return
    fieldnames = sorted({k for r in records for k in r.keys()})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    path.write_text(buf.getvalue(), encoding="utf-8")


def _write_json(records: list[dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")


async def get_dataset_stats(db: AsyncSession, owner_id: str) -> dict:
    """Return aggregate stats for a user's datasets."""
    stmt = select(
        func.count(Dataset.id),
        func.coalesce(func.sum(Dataset.record_count), 0),
        func.coalesce(func.sum(Dataset.token_reward), 0),
    ).where(Dataset.owner_id == owner_id)
    result = await db.execute(stmt)
    row = result.one()
    return {
        "total_datasets": row[0],
        "total_records": int(row[1]),
        "total_tokens_earned": float(row[2]),
    }
