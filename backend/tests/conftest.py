"""Shared pytest fixtures for the backend test suite."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Yield a TestClient with the app lifespan active."""
    with TestClient(app) as test_client:
        yield test_client
