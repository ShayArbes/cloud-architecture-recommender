"""Domain models for parsed AWS reference architectures (CLAUDE.md §5.1)."""

from pydantic import BaseModel, Field

from app.models.enums import ServiceCategory


class AwsService(BaseModel):
    """One AWS service used by an architecture."""

    name: str
    category: ServiceCategory
    purpose: str


class ParsedArchitecture(BaseModel):
    """Structured output of parsing one scraped architecture page.

    The 9-dimension ``characteristics`` object is added in S1.3; this model
    covers the directly extractable fields.
    """

    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_url: str
    description: str
    aws_services: list[AwsService]
    diagram_url: str | None
    tags: list[str]
    parser_version: str
