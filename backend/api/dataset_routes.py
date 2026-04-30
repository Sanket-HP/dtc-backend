"""Dataset upload, listing, preview, and download routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.dataset import Dataset
from ..models.user import User
from ..services.dataset_service import (
    process_and_store,
    process_manual_input,
    get_dataset_stats,
)
from .deps import get_current_user
from .schemas import DatasetResponse, DatasetStatsResponse, ManualUploadRequest

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("general"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file provided")
    raw = await file.read()
    try:
        ds = await process_and_store(
            db, user.id, title, description, category, raw, file.filename
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return ds


@router.post("/manual", response_model=DatasetResponse, status_code=201)
async def manual_upload(
    body: ManualUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        ds = await process_manual_input(
            db, user.id, body.title, body.description, body.category, body.records
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return ds


@router.get("/mine", response_model=list[DatasetResponse])
async def my_datasets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(Dataset.owner_id == user.id).order_by(Dataset.created_at.desc())
    )
    return result.scalars().all()


@router.get("/stats", response_model=DatasetStatsResponse)
async def my_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_dataset_stats(db, user.id)


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
):
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return ds


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
):
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    return {
        "id": ds.id,
        "title": ds.title,
        "fields": json.loads(ds.fields),
        "sample_records": json.loads(ds.sample_data),
        "record_count": ds.record_count,
    }


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ds = await db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    path = Path(ds.file_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing from storage")
    media = "text/csv" if ds.file_format == "csv" else "application/json"
    return FileResponse(path, media_type=media, filename=ds.original_filename)
