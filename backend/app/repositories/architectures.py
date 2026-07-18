"""MongoDB repository for the architecture inventory (CLAUDE.md §3.1, §5.1).

The only place architecture collection queries live. Returns domain models,
never raw dicts or Motor cursors.
"""

import pymongo

from app.db.client import MongoDatabase
from app.db.indexes import ARCHITECTURES_COLLECTION
from app.models.architecture import Architecture
from app.models.enums import UseCase


class MongoArchitectureRepository:
    """Motor-backed implementation of the architecture repository protocols."""

    def __init__(self, database: MongoDatabase) -> None:
        self._collection = database[ARCHITECTURES_COLLECTION]

    async def upsert(self, architecture: Architecture) -> None:
        """Insert or replace by ``source_url`` — re-scrapes never duplicate (§5.1)."""
        document = architecture.model_dump(mode="json")
        # Timestamps stay as datetimes for range queries/sorting (not JSON strings).
        document["scraped_at"] = architecture.scraped_at
        document["parsed_at"] = architecture.parsed_at
        await self._collection.update_one(
            {"source_url": architecture.source_url},
            {"$set": document},
            upsert=True,
        )

    async def list_page(
        self,
        *,
        limit: int,
        offset: int,
        use_case: UseCase | None = None,
        tag: str | None = None,
    ) -> tuple[list[Architecture], int]:
        """Return a page (newest first) plus the total count of matches.

        Both filters hit multikey indexes (``characteristics.use_cases``,
        ``tags``); the sort uses the ``scraped_at`` index (CLAUDE.md §5.1).
        """
        query: dict[str, object] = {}
        if use_case is not None:
            query["characteristics.use_cases"] = use_case.value
        if tag is not None:
            query["tags"] = tag

        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("scraped_at", pymongo.DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        architectures = [
            Architecture.model_validate({k: v for k, v in document.items() if k != "_id"})
            async for document in cursor
        ]
        return architectures, total

    async def get_by_slug(self, slug: str) -> Architecture | None:
        """Fetch one architecture by its public slug."""
        document = await self._collection.find_one({"slug": slug})
        if document is None:
            return None
        document.pop("_id", None)
        return Architecture.model_validate(document)

    async def count(self) -> int:
        """Total number of stored architectures."""
        return await self._collection.count_documents({})
