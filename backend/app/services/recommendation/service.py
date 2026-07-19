"""Recommendation service — wires the reader to the pure engine (CLAUDE.md §3.1).

Fetches the candidate set once (no N+1), runs the deterministic engine, and
shapes the ranked results (score, template explanation, per-dimension
breakdown) into the response DTO.
"""

from app.repositories.protocols import ArchitectureReader
from app.schemas.architecture import ArchitectureSummary
from app.schemas.recommendation import (
    FlexibleRecommendationRequest,
    Recommendation,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendation.engine import DEFAULT_TOP_N, recommend
from app.services.recommendation.explanation import build_explanation
from app.services.recommendation.normalization import normalize_request


class RecommendationService:
    """Produces ranked architecture recommendations for a requirements object."""

    def __init__(self, reader: ArchitectureReader) -> None:
        self._reader = reader

    async def recommend(
        self, request: RecommendationRequest, top_n: int = DEFAULT_TOP_N
    ) -> RecommendationResponse:
        """Rank the inventory against ``request``.

        An empty inventory yields an explicit empty result, not an error
        (CLAUDE.md §6.3 / S3.4).
        """
        candidates = await self._reader.list_all()
        ranked = recommend(request, candidates, top_n)
        recommendations = [
            Recommendation(
                architecture=ArchitectureSummary.from_domain(item.architecture),
                score=round(item.score, 4),
                explanation=build_explanation(request, item.breakdown, item.score),
                match_breakdown={key: round(value, 4) for key, value in item.breakdown.items()},
            )
            for item in ranked
        ]
        return RecommendationResponse(
            recommendations=recommendations,
            total_candidates_evaluated=len(candidates),
        )

    async def recommend_flexible(
        self, request: FlexibleRecommendationRequest, top_n: int = DEFAULT_TOP_N
    ) -> RecommendationResponse:
        """Rank from free-text requirements (bonus, CLAUDE.md §6.1).

        Normalizes each free-form field to the nearest enum, then delegates to
        the same scoring path — the engine is never bypassed or changed. An
        unmappable value raises a ``ValidationError`` (422).
        """
        return await self.recommend(normalize_request(request), top_n)
