"""Validates the curated seed catalogue (S5.3).

The catalogue is a deliverable in its own right: it must be internally
consistent (unique identifiers, seed-tagged) and broad enough to exercise the
recommendation engine across every use case. No database is involved — the
data is validated as Pydantic models at import time.
"""

from app.db.seed_data import SEED_ARCHITECTURES, SEED_PARSER_VERSION
from app.models.enums import UseCase


def test_catalogue_is_non_empty() -> None:
    assert len(SEED_ARCHITECTURES) >= 5


def test_slugs_are_unique() -> None:
    slugs = [architecture.slug for architecture in SEED_ARCHITECTURES]
    assert len(slugs) == len(set(slugs))


def test_source_urls_are_unique() -> None:
    # Upsert keys on source_url; duplicates would silently collapse entries.
    urls = [architecture.source_url for architecture in SEED_ARCHITECTURES]
    assert len(urls) == len(set(urls))


def test_every_entry_is_seed_tagged() -> None:
    assert all(a.parser_version == SEED_PARSER_VERSION for a in SEED_ARCHITECTURES)


def test_every_entry_has_services() -> None:
    assert all(a.aws_services for a in SEED_ARCHITECTURES)


def test_covers_all_use_cases() -> None:
    # A recommendation for any use case should find at least one candidate.
    covered = {
        use_case
        for architecture in SEED_ARCHITECTURES
        for use_case in architecture.characteristics.use_cases
    }
    assert covered == set(UseCase)
