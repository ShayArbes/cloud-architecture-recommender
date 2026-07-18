"""MongoDB repository for scrape job lifecycle records (CLAUDE.md §5.2)."""

from datetime import UTC, datetime
from typing import Any

import pymongo
from bson import ObjectId
from bson.errors import InvalidId

from app.db.client import MongoDatabase
from app.db.indexes import SCRAPE_JOBS_COLLECTION
from app.models.enums import ScrapeJobStatus, TriggerSource
from app.models.scrape_job import ScrapeJob, ScrapeJobError, ScrapeJobStats

_ACTIVE_STATUSES = [ScrapeJobStatus.PENDING.value, ScrapeJobStatus.RUNNING.value]


def _to_model(document: dict[str, Any]) -> ScrapeJob:
    document = dict(document)
    document["id"] = str(document.pop("_id"))
    return ScrapeJob.model_validate(document)


class MongoScrapeJobRepository:
    """Motor-backed implementation of ``ScrapeJobRecorder``."""

    def __init__(self, database: MongoDatabase) -> None:
        self._collection = database[SCRAPE_JOBS_COLLECTION]

    async def create(self, trigger_source: TriggerSource) -> ScrapeJob:
        """Create a job in ``pending`` state and return it."""
        document: dict[str, Any] = {
            "status": ScrapeJobStatus.PENDING.value,
            "trigger_source": trigger_source.value,
            "stats": ScrapeJobStats().model_dump(),
            "errors": [],
            "started_at": datetime.now(UTC),
            "finished_at": None,
        }
        result = await self._collection.insert_one(document)
        document["_id"] = result.inserted_id
        return _to_model(document)

    async def mark_status(self, job_id: str, status: ScrapeJobStatus) -> None:
        """Transition a job's status."""
        await self._collection.update_one(
            {"_id": ObjectId(job_id)}, {"$set": {"status": status.value}}
        )

    async def finish(
        self,
        job_id: str,
        status: ScrapeJobStatus,
        stats: ScrapeJobStats,
        errors: list[ScrapeJobError],
    ) -> None:
        """Record final stats/errors and stamp ``finished_at``."""
        await self._collection.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": status.value,
                    "stats": stats.model_dump(),
                    "errors": [error.model_dump() for error in errors],
                    "finished_at": datetime.now(UTC),
                }
            },
        )

    async def get(self, job_id: str) -> ScrapeJob | None:
        """Fetch one job by id, or ``None`` for unknown/malformed ids."""
        try:
            object_id = ObjectId(job_id)
        except InvalidId:
            return None
        document = await self._collection.find_one({"_id": object_id})
        return None if document is None else _to_model(document)

    async def list_recent(self, limit: int) -> list[ScrapeJob]:
        """Return the most recent jobs, newest first (backed by the started_at index)."""
        cursor = self._collection.find({}).sort("started_at", pymongo.DESCENDING).limit(limit)
        return [_to_model(document) async for document in cursor]

    async def has_active_job(self) -> bool:
        """Return whether a pending or running job exists (uses the status index)."""
        active = await self._collection.find_one({"status": {"$in": _ACTIVE_STATUSES}})
        return active is not None
