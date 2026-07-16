"""Index declarations, ensured at startup (CLAUDE.md §3.6, §5).

Indexes live in code so a fresh database is production-shaped on first run.
``create_index`` is idempotent — re-running at every startup is safe.
"""

import logging

import pymongo

from app.db.client import MongoDatabase

ARCHITECTURES_COLLECTION = "architectures"
SCRAPE_JOBS_COLLECTION = "scrape_jobs"

logger = logging.getLogger(__name__)


async def ensure_indexes(database: MongoDatabase) -> None:
    """Create all declared indexes (idempotent)."""
    architectures = database[ARCHITECTURES_COLLECTION]
    # Unique slug: stable public identifier for detail lookups.
    await architectures.create_index("slug", unique=True)
    # Unique source_url: idempotent scraping — re-scrapes upsert, never duplicate.
    await architectures.create_index("source_url", unique=True)
    # List view sorted by recency.
    await architectures.create_index([("scraped_at", pymongo.DESCENDING)])
    # Multikey pre-filters for recommendations and tag filtering.
    await architectures.create_index("characteristics.use_cases")
    await architectures.create_index("tags")

    scrape_jobs = database[SCRAPE_JOBS_COLLECTION]
    # Job-history listing, newest first; status for polling queries.
    await scrape_jobs.create_index([("started_at", pymongo.DESCENDING)])
    await scrape_jobs.create_index("status")
    logger.info("MongoDB indexes ensured")
