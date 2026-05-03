"""Recommendation API routes for dataset discovery."""

from fastapi import APIRouter, Depends, Query

from ..services.recommendation import (
    trending_datasets,
    high_quality_datasets,
    trusted_datasets,
    recommend_by_category,
    similar_datasets,
    recommend_for_user,
    enterprise_recommendations,
)

from .deps import get_current_user_id

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# -------------------------------------------------
# TRENDING DATASETS
# -------------------------------------------------
@router.get("/trending")
async def get_trending(limit: int = Query(10)):

    return trending_datasets(limit)


# -------------------------------------------------
# HIGH QUALITY DATASETS
# -------------------------------------------------
@router.get("/high-quality")
async def get_high_quality(limit: int = Query(10)):

    return high_quality_datasets(limit)


# -------------------------------------------------
# MOST TRUSTED DATASETS
# -------------------------------------------------
@router.get("/trusted")
async def get_trusted(limit: int = Query(10)):

    return trusted_datasets(limit)


# -------------------------------------------------
# CATEGORY RECOMMENDATIONS
# -------------------------------------------------
@router.get("/category")
async def get_category_recommendations(
    category: str,
    limit: int = Query(10)
):

    return recommend_by_category(category, limit)


# -------------------------------------------------
# SIMILAR DATASETS
# -------------------------------------------------
@router.get("/similar/{dataset_id}")
async def get_similar(dataset_id: str, limit: int = Query(5)):

    return similar_datasets(dataset_id, limit)


# -------------------------------------------------
# PERSONALIZED RECOMMENDATIONS
# -------------------------------------------------
@router.get("/personalized")
async def get_personalized(
    limit: int = Query(10),
    user_id: str = Depends(get_current_user_id)
):

    return recommend_for_user(user_id, limit)


# -------------------------------------------------
# ENTERPRISE DISCOVERY
# -------------------------------------------------
@router.get("/enterprise")
async def enterprise_discovery(
    category: str | None = None,
    limit: int = Query(20)
):

    return enterprise_recommendations(category, limit)