"""Recommendation endpoint — HTTP layer only (CLAUDE.md §3.1)."""

from fastapi import APIRouter

from app.dependencies import RecommendationServiceDep
from app.schemas.recommendation import (
    FlexibleRecommendationRequest,
    RecommendationRequest,
    RecommendationResponse,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
async def create_recommendations(
    request: RecommendationRequest, service: RecommendationServiceDep
) -> RecommendationResponse:
    """Rank the architecture inventory against the 9-dimension requirements."""
    return await service.recommend(request)


@router.post("/flexible", response_model=RecommendationResponse)
async def create_flexible_recommendations(
    request: FlexibleRecommendationRequest, service: RecommendationServiceDep
) -> RecommendationResponse:
    """Rank from free-text requirements (bonus): normalize to enums, then score."""
    return await service.recommend_flexible(request)
