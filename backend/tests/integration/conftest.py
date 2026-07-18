"""Integration-test harness: httpx AsyncClient over the ASGI app + real Mongo (S2.4).

Endpoints run through the real MongoDB repositories against a dedicated test
database. The scrape pipeline is faked so tests never touch the network. The
whole module skips cleanly when MongoDB is unreachable.
"""

import os
from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from motor.motor_asyncio import AsyncIOMotorClient

from app.db.client import MongoDatabase
from app.dependencies import get_database, get_scrape_pipeline
from app.main import app
from app.scraper.pipeline import PipelineResult

TEST_DATABASE_NAME = "cloud_arch_integration_db"
_PING_TIMEOUT_MS = 500


class ConfigurablePipeline:
    """Fake pipeline whose result each test can set via the ``pipeline`` fixture."""

    def __init__(self) -> None:
        self.result = PipelineResult()

    async def run(self, limit: int) -> PipelineResult:
        return self.result


@pytest.fixture
def pipeline() -> ConfigurablePipeline:
    return ConfigurablePipeline()


@pytest.fixture
async def integration_db() -> AsyncIterator[MongoDatabase]:
    """Yield a clean test database; skip the module if MongoDB is unreachable."""
    mongo_uri = os.environ.get("MONGO_TEST_URI", "mongodb://localhost:27017")
    client: AsyncIOMotorClient[dict[str, object]] = AsyncIOMotorClient(
        mongo_uri, tz_aware=True, serverSelectionTimeoutMS=_PING_TIMEOUT_MS
    )
    try:
        await client.admin.command("ping")
    except Exception:
        client.close()
        pytest.skip(f"MongoDB not reachable at {mongo_uri}")
    await client.drop_database(TEST_DATABASE_NAME)
    try:
        yield client[TEST_DATABASE_NAME]
    finally:
        await client.drop_database(TEST_DATABASE_NAME)
        client.close()


@pytest.fixture
async def api_client(
    integration_db: MongoDatabase,
    pipeline: ConfigurablePipeline,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an AsyncClient bound to the app, backed by the test database.

    ``LifespanManager`` runs the app's lifespan so ``app.state.mongo_client``
    exists for the health endpoint; the repositories are redirected to the test
    database via the ``get_database`` override.
    """
    app.dependency_overrides[get_database] = lambda: integration_db
    app.dependency_overrides[get_scrape_pipeline] = lambda: pipeline
    try:
        async with LifespanManager(app) as managed:
            transport = httpx.ASGITransport(app=managed.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
                yield api
    finally:
        app.dependency_overrides.clear()
