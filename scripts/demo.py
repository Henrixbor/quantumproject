#!/usr/bin/env python3
"""
Quantum MCP Relayer -- Interactive Demo Script

A standalone developer demo that connects to the local API, runs one example
of each quantum optimization tool, and prints color-formatted results.

Usage:
    python scripts/demo.py                    # uses http://localhost:8000
    BASE_URL=https://api.example.com python scripts/demo.py

Requirements:
    pip install requests
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
TIMEOUT = 60  # seconds

# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

class C:
    """ANSI escape code shortcuts."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED  = "\033[41m"


def banner(text: str) -> None:
    width = 68
    print()
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD} {'=' * width} {C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}  {text.center(width)}{C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD} {'=' * width} {C.RESET}")


def section(text: str) -> None:
    print(f"\n{C.CYAN}{C.BOLD}--- {text} ---{C.RESET}")


def ok(text: str) -> None:
    print(f"  {C.GREEN}[OK]{C.RESET} {text}")


def fail(text: str) -> None:
    print(f"  {C.RED}[FAIL]{C.RESET} {text}")


def info(text: str) -> None:
    print(f"  {C.DIM}{text}{C.RESET}")


def kv(key: str, value: str, indent: int = 4) -> None:
    pad = " " * indent
    print(f"{pad}{C.YELLOW}{key}:{C.RESET} {value}")


def json_pretty(data: dict, indent: int = 4) -> str:
    raw = json.dumps(data, indent=2)
    pad = " " * indent
    return "\n".join(f"{pad}{line}" for line in raw.splitlines())


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_session = requests.Session()


def post(path: str, body: dict, headers: dict | None = None) -> tuple[dict, float, int]:
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    resp = _session.post(url, json=body, headers=headers or {}, timeout=TIMEOUT)
    dur = (time.perf_counter() - t0) * 1000
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return data, dur, resp.status_code


def get(path: str, headers: dict | None = None) -> tuple[dict, float, int]:
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    resp = _session.get(url, headers=headers or {}, timeout=TIMEOUT)
    dur = (time.perf_counter() - t0) * 1000
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return data, dur, resp.status_code


# ---------------------------------------------------------------------------
# Demo steps
# ---------------------------------------------------------------------------

def demo_health() -> bool:
    section("Health Check")
    data, dur, status = get("/health")
    if status == 200 and data.get("status") == "ok":
        ok(f"API is healthy  ({dur:.0f} ms)")
        kv("Backend", data.get("backend", "unknown"))
        return True
    else:
        fail(f"Health check failed: HTTP {status}")
        return False


def demo_signup() -> str | None:
    section("Account Signup")
    email = f"demo-{uuid.uuid4().hex[:6]}@quantumdemo.dev"
    password = "DemoP@ss2026!"
    info(f"Creating account: {email}")
    data, dur, status = post("/api/v1/auth/signup", {
        "email": email, "password": password
    })
    if status == 200 and "api_key" in data:
        ok(f"Account created  ({dur:.0f} ms)")
        kv("User ID", data["id"])
        kv("Email", data["email"])
        kv("Tier", data["tier"])
        kv("API Key", f"{data['api_key'][:12]}...{data['api_key'][-8:]}")
        return data["api_key"]
    else:
        fail(f"Signup failed: HTTP {status} -- {data}")
        return None


def demo_portfolio(api_key: str) -> None:
    section("Portfolio Optimization (Quantum QAOA)")
    info("Optimizing a mixed tech/crypto portfolio with 6 assets...")
    body = {
        "assets": [
            {"symbol": "AAPL", "expected_return": 0.25, "volatility": 0.28},
            {"symbol": "NVDA", "expected_return": 0.55, "volatility": 0.58},
            {"symbol": "MSFT", "expected_return": 0.22, "volatility": 0.25},
            {"symbol": "BTC",  "expected_return": 0.60, "volatility": 0.75},
            {"symbol": "ETH",  "expected_return": 0.70, "volatility": 0.85},
            {"symbol": "SOL",  "expected_return": 1.10, "volatility": 1.05},
        ],
        "risk_tolerance": 0.6,
        "min_allocation": 0.05,
        "max_allocation": 0.40,
    }
    data, dur, status = post("/api/v1/portfolio/optimize", body,
                             headers={"X-API-Key": api_key})
    if status == 200:
        ok(f"Portfolio optimized  ({dur:.0f} ms)")
        print()
        allocs = data.get("allocations", {})
        max_alloc = max(allocs.values()) if allocs else 0
        for symbol, weight in sorted(allocs.items(), key=lambda x: -x[1]):
            bar_len = int(weight / max_alloc * 30) if max_alloc > 0 else 0
            bar = f"{C.GREEN}{'#' * bar_len}{C.RESET}"
            print(f"    {C.BOLD}{symbol:>6}{C.RESET}  {weight:6.1%}  {bar}")
        print()
        kv("Expected Return", f"{data.get('expected_return', 0):.2%}")
        kv("Volatility", f"{data.get('volatility', 0):.2%}")
        kv("Sharpe Ratio", f"{data.get('sharpe_ratio', 0):.3f}")
        kv("Method", data.get("method", "N/A"))
        kv("Qubits Used", str(data.get("qubit_count", "N/A")))
    else:
        fail(f"Portfolio optimization failed: HTTP {status}")
        print(json_pretty(data))


def demo_route(api_key: str) -> None:
    section("Route Optimization (Quantum TSP)")
    info("Finding the optimal route through Nordic capitals...")
    body = {
        "locations": [
            {"name": "Helsinki",    "lat": 60.1699, "lon": 24.9384},
            {"name": "Stockholm",   "lat": 59.3293, "lon": 18.0686},
            {"name": "Copenhagen",  "lat": 55.6761, "lon": 12.5683},
            {"name": "Oslo",        "lat": 59.9139, "lon": 10.7522},
            {"name": "Reykjavik",   "lat": 64.1466, "lon": -21.9426},
        ],
        "return_to_start": True,
    }
    data, dur, status = post("/api/v1/route/optimize", body,
                             headers={"X-API-Key": api_key})
    if status == 200:
        ok(f"Route optimized  ({dur:.0f} ms)")
        route = data.get("route", [])
        route_str = f" {C.YELLOW}->{C.RESET} ".join(
            f"{C.BOLD}{city}{C.RESET}" for city in route
        )
        print(f"\n    Route: {route_str}")
        print()
        kv("Total Distance", f"{data.get('total_distance_km', 0):,.1f} km")
        kv("Improvement", f"{data.get('improvement_vs_naive', 0):.1f}% vs naive ordering")
        kv("Method", data.get("method", "N/A"))
        kv("Qubits Used", str(data.get("qubit_count", "N/A")))
    else:
        fail(f"Route optimization failed: HTTP {status}")
        print(json_pretty(data))


def demo_schedule(api_key: str) -> None:
    section("Meeting Scheduler (Quantum Optimization)")
    info("Scheduling a team standup for 5 people across time zones...")
    body = {
        "participants": [
            {
                "name": "Alice (SF)",
                "available_slots": ["Mon 09:00-10:00", "Tue 09:00-10:00",
                                    "Wed 09:00-10:00", "Thu 09:00-10:00"],
                "priority": 2.0,
                "preferences": ["Wed 09:00-10:00"],
            },
            {
                "name": "Bob (NYC)",
                "available_slots": ["Mon 09:00-10:00", "Tue 09:00-10:00",
                                    "Wed 09:00-10:00", "Fri 09:00-10:00"],
                "priority": 1.5,
            },
            {
                "name": "Charlie (London)",
                "available_slots": ["Mon 09:00-10:00", "Wed 09:00-10:00",
                                    "Thu 09:00-10:00", "Fri 09:00-10:00"],
                "priority": 1.0,
            },
            {
                "name": "Diana (Helsinki)",
                "available_slots": ["Tue 09:00-10:00", "Wed 09:00-10:00",
                                    "Thu 09:00-10:00", "Fri 09:00-10:00"],
                "priority": 3.0,
                "preferences": ["Thu 09:00-10:00"],
            },
            {
                "name": "Eve (Tokyo)",
                "available_slots": ["Mon 09:00-10:00", "Wed 09:00-10:00",
                                    "Fri 09:00-10:00"],
                "priority": 1.0,
            },
        ],
        "duration_minutes": 60,
        "num_meetings": 1,
    }
    data, dur, status = post("/api/v1/schedule/optimize", body,
                             headers={"X-API-Key": api_key})
    if status == 200:
        ok(f"Meeting scheduled  ({dur:.0f} ms)")
        slots = data.get("scheduled_slots", [])
        attendance = data.get("attendance", {})
        for slot in slots:
            attendees = attendance.get(slot, [])
            print(f"\n    {C.MAGENTA}{C.BOLD}{slot}{C.RESET}")
            for name in attendees:
                print(f"      {C.GREEN}*{C.RESET} {name}")
        print()
        satisfaction = data.get("satisfaction_score", 0)
        bar_len = int(satisfaction * 30)
        sat_bar = f"{C.GREEN}{'#' * bar_len}{C.DIM}{'.' * (30 - bar_len)}{C.RESET}"
        kv("Satisfaction", f"{satisfaction:.0%}  [{sat_bar}]")
        kv("Method", data.get("method", "N/A"))
        kv("Qubits Used", str(data.get("qubit_count", "N/A")))
    else:
        fail(f"Meeting scheduling failed: HTTP {status}")
        print(json_pretty(data))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    banner("QUANTUM MCP RELAYER -- API DEMO")
    print(f"\n  {C.DIM}Target: {BASE_URL}{C.RESET}")
    print(f"  {C.DIM}Quantum computing as a service -- powered by QAOA{C.RESET}")

    # Step 1 -- Health
    if not demo_health():
        print(f"\n  {C.RED}Cannot reach the API. Is the server running at {BASE_URL}?{C.RESET}")
        print(f"  {C.DIM}Start it with: uvicorn src.api.app:app --reload{C.RESET}\n")
        return 1

    # Step 2 -- Signup
    api_key = demo_signup()
    if not api_key:
        print(f"\n  {C.RED}Signup failed. Cannot continue demo.{C.RESET}\n")
        return 1

    # Step 3 -- Portfolio
    demo_portfolio(api_key)

    # Step 4 -- Route
    demo_route(api_key)

    # Step 5 -- Schedule
    demo_schedule(api_key)

    # Done
    banner("DEMO COMPLETE")
    print(f"""
  {C.GREEN}{C.BOLD}All three quantum optimization tools demonstrated successfully.{C.RESET}

  {C.BOLD}Integration quick-start:{C.RESET}

    {C.CYAN}import requests{C.RESET}

    {C.DIM}# Authenticate{C.RESET}
    {C.CYAN}API_KEY = "qmr_your_key_here"{C.RESET}
    {C.CYAN}headers = {{"X-API-Key": API_KEY}}{C.RESET}

    {C.DIM}# Optimize a portfolio{C.RESET}
    {C.CYAN}resp = requests.post("{BASE_URL}/api/v1/portfolio/optimize",{C.RESET}
    {C.CYAN}    json={{"assets": [...], "risk_tolerance": 0.5}},{C.RESET}
    {C.CYAN}    headers=headers){C.RESET}

  {C.DIM}Docs: {BASE_URL}/docs{C.RESET}
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
