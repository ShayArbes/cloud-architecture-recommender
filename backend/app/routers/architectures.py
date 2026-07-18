"""Architecture inventory endpoints — HTTP layer only (CLAUDE.md §3.1)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.dependencies import ArchitectureReaderDep
from app.models.enums import UseCase
from app.schemas.architecture import (
    ArchitectureListResponse,
    ArchitectureSummary,
    PageMeta,
)

router = APIRouter(prefix="/architectures", tags=["architectures"])


@router.get("", response_model=ArchitectureListResponse)
async def list_architectures(
    reader: ArchitectureReaderDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
    use_case: UseCase | None = None,
    tag: str | None = None,
) -> ArchitectureListResponse:
    """List architectures, newest first, with pagination and optional filters."""
    architectures, total = await reader.list_page(
        limit=limit, offset=offset, use_case=use_case, tag=tag
    )
    return ArchitectureListResponse(
        items=[ArchitectureSummary.from_domain(architecture) for architecture in architectures],
        page=PageMeta(total=total, limit=limit, offset=offset),
    )
