"""API DTOs for the architecture endpoints (CLAUDE.md §3.1 — schemas vs models)."""

from datetime import datetime

from pydantic import BaseModel

from app.models.architecture import (
    Architecture,
    ArchitectureCharacteristics,
    AwsService,
)
from app.models.enums import UseCase


class ArchitectureSummary(BaseModel):
    """List-view projection of an architecture — metadata + timestamps, no heavy fields."""

    slug: str
    title: str
    source_url: str
    description: str
    use_cases: list[UseCase]
    service_count: int
    tags: list[str]
    scraped_at: datetime
    parsed_at: datetime

    @classmethod
    def from_domain(cls, architecture: Architecture) -> "ArchitectureSummary":
        """Map a domain model to its summary DTO (explicit, no field leakage)."""
        return cls(
            slug=architecture.slug,
            title=architecture.title,
            source_url=architecture.source_url,
            description=architecture.description,
            use_cases=architecture.use_cases,
            service_count=len(architecture.aws_services),
            tags=architecture.tags,
            scraped_at=architecture.scraped_at,
            parsed_at=architecture.parsed_at,
        )


class ArchitectureDetail(BaseModel):
    """Full architecture detail (CLAUDE.md §5.1) — everything the UI renders."""

    slug: str
    title: str
    source_url: str
    description: str
    use_cases: list[UseCase]
    aws_services: list[AwsService]
    characteristics: ArchitectureCharacteristics
    diagram_url: str | None
    tags: list[str]
    parser_version: str
    scraped_at: datetime
    parsed_at: datetime

    @classmethod
    def from_domain(cls, architecture: Architecture) -> "ArchitectureDetail":
        """Map a domain model to its detail DTO."""
        return cls.model_validate(architecture.model_dump())


class PageMeta(BaseModel):
    """Pagination metadata for a list response."""

    total: int
    limit: int
    offset: int


class ArchitectureListResponse(BaseModel):
    """Paginated list of architecture summaries."""

    items: list[ArchitectureSummary]
    page: PageMeta
