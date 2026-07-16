"""MongoDB client lifecycle and access (CLAUDE.md §3.1).

The Motor client is created in the application lifespan and stored on
``app.state``; routers and services obtain it via the ``get_mongo_client``
dependency rather than importing a module-level singleton.
"""

import logging
from typing import Any, cast

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Motor's client is generic over the document type; plain dicts at this layer —
# repositories convert them into Pydantic domain models before returning.
MongoClient = AsyncIOMotorClient[dict[str, Any]]


def create_client(mongo_uri: str) -> MongoClient:
    """Create a Motor client for ``mongo_uri``.

    The connection is lazy — no network call happens until the first
    operation — so this is safe to call at startup before MongoDB is reachable.
    """
    return AsyncIOMotorClient(mongo_uri)


def get_mongo_client(request: Request) -> MongoClient:
    """FastAPI dependency returning the app-scoped Motor client."""
    return cast(MongoClient, request.app.state.mongo_client)


async def ping(client: MongoClient) -> bool:
    """Return ``True`` if MongoDB responds to an admin ``ping``, else ``False``."""
    try:
        await client.admin.command("ping")
    except Exception:
        logger.warning("MongoDB ping failed", exc_info=True)
        return False
    return True
