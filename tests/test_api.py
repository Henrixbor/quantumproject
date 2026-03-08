import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import Tier, key_store

client = TestClient(app)

# Generate a test API key
_test_key = key_store.generate_key(owner="test", tier=Tier.free)
AUTH = {"X-API-Key": _test_key}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_unauthenticated_returns_401():
    resp = client.post(
        "/api/v1/portfolio/optimize",
        json={"assets": [{"symbol": "BTC"}, {"symbol": "ETH"}]},
    )
    assert resp.status_code == 401


def test_portfolio_endpoint():
    resp = client.post(
        "/api/v1/portfolio/optimize",
        json={
            "assets": [{"symbol": "BTC"}, {"symbol": "ETH"}],
            "risk_tolerance": 0.5,
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "allocations" in data
    assert "sharpe_ratio" in data


def test_route_endpoint():
    resp = client.post(
        "/api/v1/route/optimize",
        json={
            "locations": [
                {"name": "A", "lat": 60.17, "lon": 24.94},
                {"name": "B", "lat": 61.50, "lon": 23.79},
                {"name": "C", "lat": 60.45, "lon": 22.27},
            ]
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "route" in data
    assert "total_distance_km" in data


def test_schedule_endpoint():
    resp = client.post(
        "/api/v1/schedule/optimize",
        json={
            "participants": [
                {"name": "Alice", "available_slots": ["Mon 9:00-11:00"]},
                {"name": "Bob", "available_slots": ["Mon 10:00-12:00"]},
            ]
        },
        headers=AUTH,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "scheduled_slots" in data
    assert "satisfaction_score" in data


def test_invalid_portfolio():
    resp = client.post(
        "/api/v1/portfolio/optimize",
        json={"assets": [{"symbol": "BTC"}]},  # min 2
        headers=AUTH,
    )
    assert resp.status_code == 422
