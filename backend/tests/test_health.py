"""Tests for the health endpoint (S0.2)."""

from fastapi.testclient import TestClient


def test_health_reports_liveness(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mongodb"] in {"connected", "disconnected"}
