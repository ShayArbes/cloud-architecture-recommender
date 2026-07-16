"""Fixtures for repository integration tests.

These tests need a running MongoDB (local service or ``docker compose up
mongo``). When none is reachable they skip rather than fail, so the suite
stays green on machines without MongoDB.
"""

import os
from collections.abc import AsyncIterator

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.db.client import MongoDatabase
from app.db.indexes import ensure_indexes

TEST_DATABASE_NAME = "cloud_arch_test_db"
_PING_TIMEOUT_MS = 500


@pytest.fixture
async def mongo_database() -> AsyncIterator[MongoDatabase]:
    """Yield a clean, index-ensured test database; skip if MongoDB is down."""
    mongo_uri = os.environ.get("MONGO_TEST_URI", "mongodb://localhost:27017")
    client: AsyncIOMotorClient[dict[str, object]] = AsyncIOMotorClient(
        mongo_uri, tz_aware=True, serverSelectionTimeoutMS=_PING_TIMEOUT_MS
    )
    try:
        await client.admin.command("ping")
    except Exception:
        client.close()
        pytest.skip(f"MongoDB not reachable at {mongo_uri}")
    database = client[TEST_DATABASE_NAME]
    await client.drop_database(TEST_DATABASE_NAME)
    await ensure_indexes(database)
    try:
        yield database
    finally:
        await client.drop_database(TEST_DATABASE_NAME)
        client.close()
