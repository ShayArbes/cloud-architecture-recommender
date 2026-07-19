"""Seed the architecture inventory from the curated catalogue (CLAUDE.md §5.3).

Run with ``python -m app.db.seed``. Seeding is idempotent: architectures are
upserted by ``source_url`` (like a real scrape), so re-running never creates
duplicates. Safe to run at container start or by hand for a live demo.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.client import create_client
from app.db.indexes import ensure_indexes
from app.db.seed_data import SEED_ARCHITECTURES
from app.models.architecture import Architecture, ParsedArchitecture
from app.repositories.architectures import MongoArchitectureRepository

logger = logging.getLogger(__name__)

# Spacing between successive seed timestamps so the list view (sorted by
# ``scraped_at`` desc) presents the catalogue in a stable, catalogue order.
_SEED_TIME_STEP = timedelta(minutes=1)


def _stamp(parsed: ParsedArchitecture, scraped_at: datetime) -> Architecture:
    """Attach seed timestamps to a parsed entry (mirrors the scrape pipeline)."""
    return Architecture(**parsed.model_dump(), scraped_at=scraped_at, parsed_at=scraped_at)


async def seed(repository: MongoArchitectureRepository) -> int:
    """Upsert every curated architecture; return the number processed."""
    now = datetime.now(UTC)
    for index, parsed in enumerate(SEED_ARCHITECTURES):
        # Earlier entries get later timestamps so the first shows as newest.
        await repository.upsert(_stamp(parsed, now - index * _SEED_TIME_STEP))
    return len(SEED_ARCHITECTURES)


async def main() -> None:
    """Connect to MongoDB, ensure indexes, and seed the inventory."""
    settings = get_settings()
    configure_logging(settings.log_level)
    client = create_client(settings.mongo_uri)
    try:
        database = client[settings.mongo_db_name]
        await ensure_indexes(database)
        repository = MongoArchitectureRepository(database)
        count = await seed(repository)
        total = await repository.count()
        logger.info("Seeded %d architectures (%d total in inventory)", count, total)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
