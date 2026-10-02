"""Tests for FastAPI endpoints in backend/app/api.py."""

from fastapi.testclient import TestClient
from backend.app.api import app

client = TestClient(app)


def test_health_check():
    """Verify health check returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "phase": "3"}


def test_api_advisory_success():
    """Verify POST /api/advisory returns weather and parsed details."""
    response = client.post(
        "/api/advisory",
        json={"query": "Can I cycle in Bangalore today?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["activity"] == "cycling"
    assert "Bangalore" in data["location"]
    assert data["latitude"] is not None
    assert data["weather"] is not None
    assert "temperature" in data["weather"]
    assert data["response"] is not None


def test_api_advisory_empty_query():
    """Verify empty query returns 400 Bad Request."""
    response = client.post("/api/advisory", json={"query": "   "})
    assert response.status_code == 400
