"""Marketplace routes – browse, purchase, aggregate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.dataset import Dataset, Purchase
from ..models.user import User
from ..services.dataset_service import build_aggregated_dataset
from .deps import get_current_user
from .schemas import (
    AggregateRequest,
    DatasetResponse,
    PurchaseRequest,
    PurchaseResponse,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_marketplace(
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Dataset).where(Dataset.status == "processed")
    if category:
        stmt = stmt.where(Dataset.category == category)
    stmt = stmt.order_by(Dataset.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func, distinct

    stmt = select(Dataset.category, func.count(Dataset.id)).where(
        Dataset.status == "processed"
    ).group_by(Dataset.category)
    result = await db.execute(stmt)
    return [{"category": row[0], "count": row[1]} for row in result.all()]


@router.post("/purchase", response_model=PurchaseResponse, status_code=201)
async def purchase_dataset(
    body: PurchaseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ds = await db.get(Dataset, body.dataset_id)
    if not ds:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    if ds.owner_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot purchase your own dataset")
    if (user.token_balance or 0) < ds.price:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Insufficient token balance")

    user.token_balance = (user.token_balance or 0) - ds.price
    owner = await db.get(User, ds.owner_id)
    if owner:
        owner.token_balance = (owner.token_balance or 0) + ds.price

    purchase = Purchase(
        buyer_id=user.id,
        dataset_id=ds.id,
        price_paid=ds.price,
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase)
    return purchase


@router.post("/aggregate", response_model=DatasetResponse, status_code=201)
async def aggregate_datasets(
    body: AggregateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        ds = await build_aggregated_dataset(
            db, body.category, body.title, body.description, user.id
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return ds
