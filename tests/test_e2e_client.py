"""
Comprehensive end-to-end API test client for the Quantum MCP Relayer.

Tests the full lifecycle: health check, signup, authentication,
portfolio optimization, route optimization, meeting scheduling,
edge cases, and error handling.

Run:
    pytest tests/test_e2e_client.py -v -s

Requires the API to be running at http://localhost:8000 (or set BASE_URL env var).
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Generate a unique email per test run to avoid 409 conflicts
_RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL = f"e2e-{_RUN_ID}@quantumtest.dev"
TEST_PASSWORD = "SecureP@ssw0rd!2026"


# ---------------------------------------------------------------------------
# Test result tracking
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    status_code: int | None = None
    detail: str = ""


_results: list[TestResult] = []


def _log_request(method: str, path: str, body: dict | None = None) -> None:
    print(f"\n{'='*72}")
    print(f"  REQUEST  {method} {path}")
    if body:
        print(f"  BODY     {json.dumps(body, indent=2)[:500]}")
    print(f"{'='*72}")


def _log_response(resp: requests.Response, duration_ms: float) -> None:
    print(f"  STATUS   {resp.status_code}")
    print(f"  TIME     {duration_ms:.1f} ms")
    try:
        body = resp.json()
        formatted = json.dumps(body, indent=2)
        # Truncate very long responses
        if len(formatted) > 1500:
            formatted = formatted[:1500] + "\n  ... (truncated)"
        print(f"  BODY     {formatted}")
    except Exception:
        print(f"  BODY     {resp.text[:300]}")
    # Rate limit headers
    rl_limit = resp.headers.get("X-RateLimit-Limit")
    if rl_limit:
        print(f"  RATE     {resp.headers.get('X-RateLimit-Remaining')}/{rl_limit} remaining")


def _record(name: str, passed: bool, duration_ms: float,
            status_code: int | None = None, detail: str = "") -> None:
    tag = "PASS" if passed else "FAIL"
    print(f"\n  [{tag}] {name} ({duration_ms:.1f} ms)")
    if detail:
        print(f"         {detail}")
    _results.append(TestResult(name=name, passed=passed,
                               duration_ms=duration_ms,
                               status_code=status_code, detail=detail))


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(path: str, headers: dict | None = None) -> tuple[requests.Response, float]:
    url = f"{BASE_URL}{path}"
    _log_request("GET", url)
    t0 = time.perf_counter()
    resp = requests.get(url, headers=headers or {}, timeout=30)
    dur = (time.perf_counter() - t0) * 1000
    _log_response(resp, dur)
    return resp, dur


def _post(path: str, body: dict, headers: dict | None = None) -> tuple[requests.Response, float]:
    url = f"{BASE_URL}{path}"
    _log_request("POST", url, body)
    t0 = time.perf_counter()
    resp = requests.post(url, json=body, headers=headers or {}, timeout=60)
    dur = (time.perf_counter() - t0) * 1000
    _log_response(resp, dur)
    return resp, dur


# ---------------------------------------------------------------------------
# Shared state across tests
# ---------------------------------------------------------------------------

_state: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# 1. Health check
# ---------------------------------------------------------------------------

def test_01_health_check():
    """GET /health should return status ok."""
    resp, dur = _get("/health")
    data = resp.json()
    ok = resp.status_code == 200 and data.get("status") == "ok"
    _record("Health check", ok, dur, resp.status_code,
            f"backend={data.get('backend')}")
    assert resp.status_code == 200
    assert data["status"] == "ok"
    assert "backend" in data


# ---------------------------------------------------------------------------
# 2. Signup
# ---------------------------------------------------------------------------

def test_02_signup():
    """POST /api/v1/auth/signup should create an account and return an API key."""
    body = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    resp, dur = _post("/api/v1/auth/signup", body)
    data = resp.json()
    ok = resp.status_code == 200 and "api_key" in data
    _record("Signup", ok, dur, resp.status_code,
            f"email={data.get('email')}, tier={data.get('tier')}")
    assert resp.status_code == 200
    assert data["api_key"].startswith("qmr_")
    assert data["tier"] == "free"
    # Store for later tests
    _state["api_key"] = data["api_key"]
    _state["user_id"] = data["id"]


def test_02b_signup_duplicate():
    """Duplicate signup should return 409."""
    body = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    resp, dur = _post("/api/v1/auth/signup", body)
    ok = resp.status_code == 409
    _record("Signup duplicate rejection", ok, dur, resp.status_code)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 3. Portfolio optimization -- crypto
# ---------------------------------------------------------------------------

def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": _state["api_key"]}


def test_03_portfolio_crypto():
    """Optimize a crypto portfolio: BTC, ETH, SOL, AVAX."""
    body = {
        "assets": [
            {"symbol": "BTC", "expected_return": 0.65, "volatility": 0.75},
            {"symbol": "ETH", "expected_return": 0.80, "volatility": 0.85},
            {"symbol": "SOL", "expected_return": 1.20, "volatility": 1.10},
            {"symbol": "AVAX", "expected_return": 0.90, "volatility": 0.95},
        ],
        "risk_tolerance": 0.7,
        "min_allocation": 0.05,
        "max_allocation": 0.60,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        allocs = data.get("allocations", {})
        alloc_sum = sum(allocs.values())
        ok = ok and abs(alloc_sum - 1.0) < 0.02  # allow small rounding
        ok = ok and all(v >= 0.0 for v in allocs.values())
        ok = ok and "sharpe_ratio" in data
        _record("Portfolio crypto (BTC/ETH/SOL/AVAX)", ok, dur, resp.status_code,
                f"allocations_sum={alloc_sum:.4f}, sharpe={data.get('sharpe_ratio', 'N/A')}, "
                f"qubits={data.get('qubit_count')}")
    else:
        _record("Portfolio crypto (BTC/ETH/SOL/AVAX)", False, dur, resp.status_code,
                f"error={data}")
    assert resp.status_code == 200
    assert abs(sum(data["allocations"].values()) - 1.0) < 0.02


# ---------------------------------------------------------------------------
# 4. Portfolio optimization -- stocks
# ---------------------------------------------------------------------------

def test_04_portfolio_stocks():
    """Optimize a stock portfolio: AAPL, GOOGL, MSFT, NVDA."""
    body = {
        "assets": [
            {"symbol": "AAPL", "expected_return": 0.25, "volatility": 0.30},
            {"symbol": "GOOGL", "expected_return": 0.28, "volatility": 0.33},
            {"symbol": "MSFT", "expected_return": 0.22, "volatility": 0.27},
            {"symbol": "NVDA", "expected_return": 0.55, "volatility": 0.60},
        ],
        "risk_tolerance": 0.4,
        "min_allocation": 0.10,
        "max_allocation": 0.50,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        allocs = data["allocations"]
        alloc_sum = sum(allocs.values())
        # Validate constraints
        ok = ok and abs(alloc_sum - 1.0) < 0.02
        ok = ok and all(v >= 0.0 for v in allocs.values())
        _record("Portfolio stocks (AAPL/GOOGL/MSFT/NVDA)", ok, dur, resp.status_code,
                f"allocations_sum={alloc_sum:.4f}, expected_return={data.get('expected_return', 'N/A')}")
    else:
        _record("Portfolio stocks", False, dur, resp.status_code)
    assert resp.status_code == 200
    assert abs(sum(data["allocations"].values()) - 1.0) < 0.02


# ---------------------------------------------------------------------------
# 5. Route optimization -- Finnish cities
# ---------------------------------------------------------------------------

def test_05_route_finnish_cities():
    """Optimize route through 5 Finnish cities."""
    body = {
        "locations": [
            {"name": "Helsinki", "lat": 60.1699, "lon": 24.9384},
            {"name": "Tampere", "lat": 61.4978, "lon": 23.7610},
            {"name": "Turku", "lat": 60.4518, "lon": 22.2666},
            {"name": "Oulu", "lat": 65.0121, "lon": 25.4651},
            {"name": "Jyväskylä", "lat": 62.2426, "lon": 25.7473},
        ],
        "return_to_start": True,
    }
    resp, dur = _post("/api/v1/route/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        route = data.get("route", [])
        expected_cities = {"Helsinki", "Tampere", "Turku", "Oulu", "Jyväskylä"}
        # Route may include return-to-start duplicate; check unique names
        route_set = set(route)
        all_visited = expected_cities.issubset(route_set)
        ok = ok and all_visited
        ok = ok and data.get("total_distance_km", 0) > 0
        _record("Route Finnish cities", ok, dur, resp.status_code,
                f"distance={data.get('total_distance_km', 'N/A'):.1f} km, "
                f"route={'->'.join(route)}, "
                f"improvement={data.get('improvement_vs_naive', 'N/A')}%")
    else:
        _record("Route Finnish cities", False, dur, resp.status_code)
    assert resp.status_code == 200
    assert set(data["route"]).issuperset({"Helsinki", "Tampere", "Turku", "Oulu", "Jyväskylä"})


# ---------------------------------------------------------------------------
# 6. Route optimization -- European capitals
# ---------------------------------------------------------------------------

def test_06_route_european_capitals():
    """Optimize route through 4 European capitals."""
    body = {
        "locations": [
            {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
            {"name": "Berlin", "lat": 52.5200, "lon": 13.4050},
            {"name": "Rome", "lat": 41.9028, "lon": 12.4964},
            {"name": "Madrid", "lat": 40.4168, "lon": -3.7038},
        ],
        "return_to_start": False,
    }
    resp, dur = _post("/api/v1/route/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        route = data.get("route", [])
        expected = {"Paris", "Berlin", "Rome", "Madrid"}
        ok = ok and expected.issubset(set(route))
        ok = ok and data.get("total_distance_km", 0) > 0
        _record("Route European capitals", ok, dur, resp.status_code,
                f"distance={data.get('total_distance_km', 'N/A'):.1f} km, "
                f"route={'->'.join(route)}")
    else:
        _record("Route European capitals", False, dur, resp.status_code)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 7. Meeting scheduling -- 4 people, complex availability
# ---------------------------------------------------------------------------

def test_07_meeting_4_people():
    """Schedule a meeting for 4 people with complex availability."""
    body = {
        "participants": [
            {
                "name": "Alice",
                "available_slots": ["Mon 09:00-11:00", "Tue 14:00-16:00", "Wed 10:00-12:00"],
                "priority": 3.0,
                "preferences": ["Mon 09:00-11:00"],
            },
            {
                "name": "Bob",
                "available_slots": ["Mon 09:00-11:00", "Tue 14:00-16:00", "Thu 09:00-11:00"],
                "priority": 2.0,
                "preferences": ["Tue 14:00-16:00"],
            },
            {
                "name": "Charlie",
                "available_slots": ["Mon 09:00-11:00", "Wed 10:00-12:00", "Thu 09:00-11:00"],
                "priority": 1.0,
                "preferences": [],
            },
            {
                "name": "Diana",
                "available_slots": ["Mon 09:00-11:00", "Tue 14:00-16:00", "Wed 10:00-12:00", "Thu 09:00-11:00"],
                "priority": 1.5,
                "preferences": ["Wed 10:00-12:00"],
            },
        ],
        "duration_minutes": 60,
        "num_meetings": 1,
    }
    resp, dur = _post("/api/v1/schedule/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        slots = data.get("scheduled_slots", [])
        satisfaction = data.get("satisfaction_score", 0)
        ok = ok and len(slots) >= 1
        ok = ok and 0 <= satisfaction <= 1
        attendance = data.get("attendance", {})
        _record("Meeting 4 people (complex)", ok, dur, resp.status_code,
                f"slots={slots}, satisfaction={satisfaction:.2f}, "
                f"attendees={attendance}, qubits={data.get('qubit_count')}")
    else:
        _record("Meeting 4 people (complex)", False, dur, resp.status_code)
    assert resp.status_code == 200
    assert len(data["scheduled_slots"]) >= 1
    assert 0 <= data["satisfaction_score"] <= 1


# ---------------------------------------------------------------------------
# 8. Meeting scheduling -- 6 people, 3 meetings
# ---------------------------------------------------------------------------

def test_08_meeting_6_people_3_meetings():
    """Schedule 3 meetings for 6 people."""
    body = {
        "participants": [
            {
                "name": "Person1",
                "available_slots": ["Mon 09:00-10:00", "Mon 14:00-15:00", "Tue 09:00-10:00",
                                    "Wed 11:00-12:00", "Thu 14:00-15:00"],
                "priority": 2.0,
            },
            {
                "name": "Person2",
                "available_slots": ["Mon 09:00-10:00", "Tue 09:00-10:00", "Wed 11:00-12:00",
                                    "Thu 14:00-15:00", "Fri 09:00-10:00"],
                "priority": 1.5,
            },
            {
                "name": "Person3",
                "available_slots": ["Mon 14:00-15:00", "Tue 09:00-10:00", "Wed 11:00-12:00",
                                    "Thu 14:00-15:00"],
                "priority": 1.0,
            },
            {
                "name": "Person4",
                "available_slots": ["Mon 09:00-10:00", "Mon 14:00-15:00", "Wed 11:00-12:00",
                                    "Fri 09:00-10:00"],
                "priority": 1.0,
            },
            {
                "name": "Person5",
                "available_slots": ["Tue 09:00-10:00", "Wed 11:00-12:00", "Thu 14:00-15:00",
                                    "Fri 09:00-10:00"],
                "priority": 3.0,
            },
            {
                "name": "Person6",
                "available_slots": ["Mon 09:00-10:00", "Tue 09:00-10:00", "Thu 14:00-15:00",
                                    "Fri 09:00-10:00"],
                "priority": 1.0,
            },
        ],
        "duration_minutes": 60,
        "num_meetings": 3,
    }
    resp, dur = _post("/api/v1/schedule/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        slots = data.get("scheduled_slots", [])
        ok = ok and len(slots) >= 1  # should schedule at least 1, ideally 3
        ok = ok and 0 <= data.get("satisfaction_score", -1) <= 1
        _record("Meeting 6 people / 3 meetings", ok, dur, resp.status_code,
                f"scheduled={len(slots)} slots, "
                f"satisfaction={data.get('satisfaction_score', 'N/A')}")
    else:
        _record("Meeting 6 people / 3 meetings", False, dur, resp.status_code)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 9. Edge cases
# ---------------------------------------------------------------------------

def test_09a_portfolio_min_assets():
    """Edge case: portfolio with exactly 2 assets (minimum)."""
    body = {
        "assets": [
            {"symbol": "BTC", "expected_return": 0.50, "volatility": 0.70},
            {"symbol": "ETH", "expected_return": 0.60, "volatility": 0.80},
        ],
        "risk_tolerance": 0.5,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        alloc_sum = sum(data["allocations"].values())
        ok = ok and abs(alloc_sum - 1.0) < 0.02
        _record("Portfolio min (2 assets)", ok, dur, resp.status_code,
                f"sum={alloc_sum:.4f}")
    else:
        _record("Portfolio min (2 assets)", False, dur, resp.status_code)
    assert resp.status_code == 200


def test_09b_portfolio_max_assets():
    """Edge case: portfolio with 20 assets (maximum)."""
    symbols = [
        "BTC", "ETH", "SOL", "AVAX", "DOT", "ADA", "MATIC", "LINK", "ATOM", "UNI",
        "AAVE", "CRV", "MKR", "SNX", "COMP", "SUSHI", "YFI", "BAL", "DYDX", "GMX",
    ]
    body = {
        "assets": [
            {"symbol": s, "expected_return": 0.10 + i * 0.04, "volatility": 0.20 + i * 0.03}
            for i, s in enumerate(symbols)
        ],
        "risk_tolerance": 0.5,
        "min_allocation": 0.02,
        "max_allocation": 0.20,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        alloc_sum = sum(data["allocations"].values())
        ok = ok and abs(alloc_sum - 1.0) < 0.05  # larger tolerance for 20 assets
        _record("Portfolio max (20 assets)", ok, dur, resp.status_code,
                f"sum={alloc_sum:.4f}, qubits={data.get('qubit_count')}")
    else:
        _record("Portfolio max (20 assets)", False, dur, resp.status_code)
    assert resp.status_code == 200


def test_09c_route_min_locations():
    """Edge case: route with exactly 3 locations (minimum)."""
    body = {
        "locations": [
            {"name": "A", "lat": 60.17, "lon": 24.94},
            {"name": "B", "lat": 61.50, "lon": 23.76},
            {"name": "C", "lat": 60.45, "lon": 22.27},
        ],
        "return_to_start": True,
    }
    resp, dur = _post("/api/v1/route/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        ok = ok and {"A", "B", "C"}.issubset(set(data["route"]))
        ok = ok and data["total_distance_km"] > 0
        _record("Route min (3 locations)", ok, dur, resp.status_code,
                f"route={'->'.join(data['route'])}")
    else:
        _record("Route min (3 locations)", False, dur, resp.status_code)
    assert resp.status_code == 200


def test_09d_meeting_same_availability():
    """Edge case: all participants share the same availability."""
    shared_slots = ["Mon 10:00-11:00", "Wed 14:00-15:00"]
    body = {
        "participants": [
            {"name": "Alpha", "available_slots": shared_slots, "priority": 1.0},
            {"name": "Beta", "available_slots": shared_slots, "priority": 1.0},
            {"name": "Gamma", "available_slots": shared_slots, "priority": 1.0},
            {"name": "Delta", "available_slots": shared_slots, "priority": 1.0},
        ],
        "duration_minutes": 60,
        "num_meetings": 1,
    }
    resp, dur = _post("/api/v1/schedule/optimize", body, headers=_auth_headers())
    data = resp.json()
    ok = resp.status_code == 200
    if ok:
        slots = data["scheduled_slots"]
        ok = ok and len(slots) >= 1
        # The chosen slot should be one of the shared ones
        ok = ok and any(s in shared_slots for s in slots)
        _record("Meeting same availability", ok, dur, resp.status_code,
                f"slot={slots}")
    else:
        _record("Meeting same availability", False, dur, resp.status_code)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 10. Error cases
# ---------------------------------------------------------------------------

def test_10a_portfolio_too_few_assets():
    """Error case: portfolio with only 1 asset should fail validation."""
    body = {
        "assets": [{"symbol": "BTC", "expected_return": 0.5, "volatility": 0.7}],
        "risk_tolerance": 0.5,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    ok = resp.status_code == 422  # Pydantic validation error
    _record("Error: too few assets (1)", ok, dur, resp.status_code)
    assert resp.status_code == 422


def test_10b_portfolio_missing_fields():
    """Error case: portfolio request missing required fields."""
    body = {"risk_tolerance": 0.5}  # no assets
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    ok = resp.status_code == 422
    _record("Error: missing assets field", ok, dur, resp.status_code)
    assert resp.status_code == 422


def test_10c_portfolio_invalid_risk():
    """Error case: risk_tolerance out of range."""
    body = {
        "assets": [
            {"symbol": "BTC", "expected_return": 0.5, "volatility": 0.7},
            {"symbol": "ETH", "expected_return": 0.6, "volatility": 0.8},
        ],
        "risk_tolerance": 5.0,  # max is 1.0
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers=_auth_headers())
    ok = resp.status_code == 422
    _record("Error: invalid risk_tolerance", ok, dur, resp.status_code)
    assert resp.status_code == 422


def test_10d_route_too_few_locations():
    """Error case: route with only 2 locations (min is 3)."""
    body = {
        "locations": [
            {"name": "A", "lat": 60.17, "lon": 24.94},
            {"name": "B", "lat": 61.50, "lon": 23.76},
        ],
        "return_to_start": True,
    }
    resp, dur = _post("/api/v1/route/optimize", body, headers=_auth_headers())
    ok = resp.status_code == 422
    _record("Error: too few locations (2)", ok, dur, resp.status_code)
    assert resp.status_code == 422


def test_10e_no_auth():
    """Error case: request without API key should return 401."""
    body = {
        "assets": [
            {"symbol": "BTC", "expected_return": 0.5, "volatility": 0.7},
            {"symbol": "ETH", "expected_return": 0.6, "volatility": 0.8},
        ],
        "risk_tolerance": 0.5,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body, headers={})
    ok = resp.status_code == 401
    _record("Error: no auth header", ok, dur, resp.status_code)
    assert resp.status_code == 401


def test_10f_invalid_api_key():
    """Error case: request with invalid API key should return 401."""
    body = {
        "assets": [
            {"symbol": "BTC", "expected_return": 0.5, "volatility": 0.7},
            {"symbol": "ETH", "expected_return": 0.6, "volatility": 0.8},
        ],
        "risk_tolerance": 0.5,
    }
    resp, dur = _post("/api/v1/portfolio/optimize", body,
                      headers={"X-API-Key": "qmr_000000000000000000000000deadbeef1234567890ab"})
    ok = resp.status_code == 401
    _record("Error: invalid API key", ok, dur, resp.status_code)
    assert resp.status_code == 401


def test_10g_invalid_lat_lon():
    """Error case: route with latitude out of range."""
    body = {
        "locations": [
            {"name": "Valid", "lat": 60.17, "lon": 24.94},
            {"name": "Invalid", "lat": 200.0, "lon": 24.94},
            {"name": "Also Valid", "lat": 61.50, "lon": 23.76},
        ],
        "return_to_start": True,
    }
    resp, dur = _post("/api/v1/route/optimize", body, headers=_auth_headers())
    ok = resp.status_code == 422
    _record("Error: invalid lat (200)", ok, dur, resp.status_code)
    assert resp.status_code == 422


def test_10h_schedule_empty_participants():
    """Error case: schedule with only 1 participant (min is 2)."""
    body = {
        "participants": [
            {"name": "Alone", "available_slots": ["Mon 09:00-10:00"], "priority": 1.0},
        ],
        "duration_minutes": 60,
        "num_meetings": 1,
    }
    resp, dur = _post("/api/v1/schedule/optimize", body, headers=_auth_headers())
    ok = resp.status_code == 422
    _record("Error: too few participants (1)", ok, dur, resp.status_code)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def test_99_summary():
    """Print the final test summary report."""
    print("\n")
    print("=" * 72)
    print("  QUANTUM MCP RELAYER -- END-TO-END TEST REPORT")
    print("=" * 72)
    passed = sum(1 for r in _results if r.passed)
    failed = sum(1 for r in _results if not r.passed)
    total = len(_results)
    total_time = sum(r.duration_ms for r in _results)
    print(f"\n  Total:  {total} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Time:   {total_time:.0f} ms ({total_time/1000:.1f} s)")
    print()
    if failed:
        print("  FAILED TESTS:")
        for r in _results:
            if not r.passed:
                print(f"    - {r.name} (HTTP {r.status_code}) {r.detail}")
        print()
    print("=" * 72)
    if failed:
        print(f"  RESULT: FAIL ({failed} of {total} tests failed)")
    else:
        print(f"  RESULT: ALL {total} TESTS PASSED")
    print("=" * 72)
    # Do not assert here -- this is just the summary printer
