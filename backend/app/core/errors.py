"""Application exception hierarchy and FastAPI handlers (CLAUDE.md §3.5).

Every error reaching the client is shaped into a single JSON envelope::

    {"error": {"code": "...", "message": "...", "details": {...}}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, domain-level application errors."""

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class NotFoundError(AppError):
    """A requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404


class ValidationError(AppError):
    """A request failed domain-level validation."""

    code = "VALIDATION_ERROR"
    status_code = 422


class ScrapeError(AppError):
    """A scraping/parsing operation failed."""

    code = "SCRAPE_ERROR"
    status_code = 502


class ExternalServiceError(AppError):
    """An upstream dependency (e.g. an external API) failed."""

    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502


def _envelope(code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    """Build the standard error envelope body."""
    return {"error": {"code": code, "message": message, "details": details}}


def register_exception_handlers(app: FastAPI) -> None:
    """Register the application's exception handlers on ``app``."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "VALIDATION_ERROR",
                "Request validation failed",
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing request")
        return JSONResponse(
            status_code=500,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred", {}),
        )
