"""Structured logging configuration (CLAUDE.md §3.3 — no print debugging)."""

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(level: str) -> None:
    """Configure root logging once at application startup.

    Args:
        level: A logging level name (e.g. ``"INFO"``, ``"DEBUG"``).
    """
    logging.basicConfig(level=level.upper(), format=_LOG_FORMAT)
