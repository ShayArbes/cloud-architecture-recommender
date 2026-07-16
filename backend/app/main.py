"""FastAPI application factory, lifespan, and wiring (CLAUDE.md §3.1)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.client import create_client
from app.db.indexes import ensure_indexes
from app.routers import health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the MongoDB client on startup and close it on shutdown."""
    settings = get_settings()
    app.state.mongo_client = create_client(settings.mongo_uri)
    try:
        # Best-effort at startup: the API must come up (and report health)
        # even while MongoDB is unreachable (CLAUDE.md §3.5).
        await ensure_indexes(app.state.mongo_client[settings.mongo_db_name])
    except Exception:
        logger.warning("Could not ensure MongoDB indexes at startup", exc_info=True)
    try:
        yield
    finally:
        app.state.mongo_client.close()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Cloud Architecture Recommender API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    return app


app = create_app()
