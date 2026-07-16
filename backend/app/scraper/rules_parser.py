"""Rule-based architecture parser — the no-API-key fallback (CLAUDE.md §2).

Extraction strategy per field:
- title: first ``<h1>``, falling back to ``<title>``.
- description: meta description → og:description → first substantial paragraph.
- services: word-boundary regex scan of the *raw* HTML against the service
  catalog — AWS pages embed much of their content in client-rendered JSON,
  so visible-text-only scanning misses services.
- diagram: first ``<img>`` whose src mentions a diagram/architecture.
- tags: lowercased short service names (e.g. "lambda", "dynamodb").
"""

import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.errors import ScrapeError
from app.models.architecture import AwsService, ParsedArchitecture
from app.scraper.characteristics import extract_characteristics
from app.scraper.service_catalog import CATEGORY_PURPOSES, SERVICE_CATALOG

RULES_PARSER_VERSION = "rules-v1"

_MAX_DESCRIPTION_LENGTH = 500
_MIN_PARAGRAPH_LENGTH = 60
_DIAGRAM_SRC_HINTS = ("architecture", "diagram")

# Boilerplate suffixes AWS appends to page titles.
_TITLE_SUFFIXES = (" | AWS Solutions", " - Amazon Web Services", " | AWS")


def _slugify(title: str) -> str:
    """Derive a URL-safe, stable identifier from the title (CLAUDE.md §5.1)."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug


def _service_tag(service_name: str) -> str:
    """Lowercase tag from a service name, vendor prefix dropped."""
    short_name = re.sub(r"^(Amazon|AWS)\s+", "", service_name)
    return re.sub(r"[^a-z0-9]+", "-", short_name.lower()).strip("-")


class RulesBasedParser:
    """Deterministic BeautifulSoup parser; runs with no external dependencies."""

    parser_version = RULES_PARSER_VERSION

    async def parse(self, raw_html: str, source_url: str) -> ParsedArchitecture:
        """Extract a ``ParsedArchitecture`` from ``raw_html`` (no I/O performed)."""
        soup = BeautifulSoup(raw_html, "html.parser")
        title = self._extract_title(soup)
        if title is None:
            raise ScrapeError("Page has no usable title", details={"source_url": source_url})
        services = self._extract_services(raw_html)
        description = self._extract_description(soup)
        characteristics = extract_characteristics(title, description, services)
        return ParsedArchitecture(
            slug=_slugify(title),
            title=title,
            source_url=source_url,
            description=description,
            use_cases=characteristics.use_cases,
            aws_services=services,
            characteristics=characteristics,
            diagram_url=self._extract_diagram_url(soup),
            tags=[_service_tag(service.name) for service in services],
            parser_version=self.parser_version,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        for selector in ("h1", "title"):
            element = soup.find(selector)
            if element is not None:
                text = element.get_text(strip=True)
                if text:
                    return self._strip_title_suffixes(text)
        return None

    @staticmethod
    def _strip_title_suffixes(title: str) -> str:
        for suffix in _TITLE_SUFFIXES:
            title = title.removesuffix(suffix)
        return title.strip()

    def _extract_description(self, soup: BeautifulSoup) -> str:
        for selector in ('meta[name="description"]', 'meta[property="og:description"]'):
            meta = soup.select_one(selector)
            if isinstance(meta, Tag):
                content = meta.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()[:_MAX_DESCRIPTION_LENGTH]
        for paragraph in soup.find_all("p"):
            text = paragraph.get_text(" ", strip=True)
            if len(text) >= _MIN_PARAGRAPH_LENGTH:
                return text[:_MAX_DESCRIPTION_LENGTH]
        return ""

    @staticmethod
    def _extract_services(raw_html: str) -> list[AwsService]:
        services = [
            AwsService(
                name=definition.name,
                category=definition.category,
                purpose=CATEGORY_PURPOSES[definition.category],
            )
            for definition in SERVICE_CATALOG
            if re.search(rf"\b(?:{definition.pattern})\b", raw_html)
        ]
        return services

    @staticmethod
    def _extract_diagram_url(soup: BeautifulSoup) -> str | None:
        for image in soup.find_all("img"):
            if not isinstance(image, Tag):
                continue
            src = image.get("src")
            if isinstance(src, str) and any(hint in src.lower() for hint in _DIAGRAM_SRC_HINTS):
                return src if src.startswith("http") else f"https://aws.amazon.com{src}"
        return None
