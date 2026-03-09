#!/usr/bin/env python3
"""Performance benchmark suite for the Quantum MCP Relayer.

Times each quantum optimization tool at various problem sizes and
reports results in a formatted table. Run from the project root:

    python -m scripts.benchmark

Measures:
  - Portfolio optimizer:  2-10 assets
  - Route optimizer:      3-10 locations
  - Meeting scheduler:    2-10 participants
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import numpy as np

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.models.schemas import (
    Asset,
    Location,
    MeetingParticipant,
    MeetingScheduleRequest,
    PortfolioRequest,
    RouteRequest,
)
from src.quantum.portfolio import optimize_portfolio
from src.quantum.qaoa import qaoa_optimize
from src.quantum.router import optimize_route
from src.quantum.scheduler import optimize_schedule

# ---------------------------------------------------------------------------
# Test data generators
# ---------------------------------------------------------------------------

SYMBOLS = ["BTC", "ETH", "SOL", "AAPL", "GOOG", "MSFT", "AMZN", "TSLA", "NVDA", "META"]


def make_portfolio_request(n_assets: int) -> PortfolioRequest:
    assets = [Asset(symbol=SYMBOLS[i % len(SYMBOLS)]) for i in range(n_assets)]
    return PortfolioRequest(assets=assets, risk_tolerance=0.5)


CITIES = [
    ("New York", 40.7128, -74.0060),
    ("Los Angeles", 34.0522, -118.2437),
    ("Chicago", 41.8781, -87.6298),
    ("Houston", 29.7604, -95.3698),
    ("Phoenix", 33.4484, -112.0740),
    ("San Antonio", 29.4241, -98.4936),
    ("San Diego", 32.7157, -117.1611),
    ("Dallas", 32.7767, -96.7970),
    ("Denver", 39.7392, -104.9903),
    ("Seattle", 47.6062, -122.3321),
]


def make_route_request(n_locations: int) -> RouteRequest:
    locations = [
        Location(name=name, lat=lat, lon=lon)
        for name, lat, lon in CITIES[:n_locations]
    ]
    return RouteRequest(locations=locations, return_to_start=True)


SLOTS = [
    "Mon 9:00-12:00", "Mon 14:00-17:00",
    "Tue 9:00-12:00", "Tue 14:00-17:00",
    "Wed 9:00-12:00", "Wed 14:00-17:00",
    "Thu 9:00-12:00", "Thu 14:00-17:00",
    "Fri 9:00-12:00", "Fri 14:00-17:00",
]

NAMES = [
    "Alice", "Bob", "Charlie", "Diana", "Eve",
    "Frank", "Grace", "Hank", "Ivy", "Jack",
]


def make_schedule_request(n_participants: int) -> MeetingScheduleRequest:
    participants = []
    for i in range(n_participants):
        # Each participant gets a random subset of slots
        rng = np.random.default_rng(seed=i)
        n_avail = rng.integers(3, min(len(SLOTS), 7) + 1)
        avail = list(rng.choice(SLOTS, size=n_avail, replace=False))
        pref = avail[:2]
        participants.append(
            MeetingParticipant(
                name=NAMES[i % len(NAMES)],
                available_slots=avail,
                preferences=pref,
                priority=1.0,
            )
        )
    return MeetingScheduleRequest(
        participants=participants, duration_minutes=60, num_meetings=1
    )


# ---------------------------------------------------------------------------
# Direct QAOA benchmark (raw engine without problem wrappers)
# ---------------------------------------------------------------------------

def bench_qaoa_raw(n_qubits: int, num_layers: int = 2) -> float:
    """Benchmark raw QAOA engine on a random QUBO of given size.

    Returns elapsed time in seconds.
    """
    rng = np.random.default_rng(seed=42)
    Q = rng.standard_normal((n_qubits, n_qubits))
    Q = (Q + Q.T) / 2  # symmetric

    t0 = time.perf_counter()
    qaoa_optimize(Q, num_layers=num_layers, num_shots=256)
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

def time_async(coro_func, *args, repeats: int = 1) -> float:
    """Run an async function and return median wall-clock time in seconds."""
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        asyncio.get_event_loop().run_until_complete(coro_func(*args))
        times.append(time.perf_counter() - t0)
    return float(np.median(times))


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def fmt_time(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1e6:.0f} us"
    if seconds < 1.0:
        return f"{seconds * 1000:.1f} ms"
    return f"{seconds:.2f} s"


def print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    border = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"

    print()
    print(f"  {title}")
    print(f"  {border}")
    print(f"  {header_line}")
    print(f"  {border}")
    for row in rows:
        line = "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, widths)) + " |"
        print(f"  {line}")
    print(f"  {border}")


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 64)
    print("  Quantum MCP Relayer -- Performance Benchmark")
    print("=" * 64)

    # Suppress numpy warnings for cleaner output
    np.seterr(all="ignore")

    # --- Raw QAOA engine ---
    qaoa_rows = []
    for n in [6, 8, 9, 10, 12]:
        layers = 2 if n <= 10 else 1
        try:
            elapsed = bench_qaoa_raw(n, num_layers=layers)
            status = "PASS" if (n <= 9 and elapsed < 0.5) or (n <= 12 and elapsed < 3.0) else "SLOW"
            qaoa_rows.append([str(n), str(1 << n), str(layers), fmt_time(elapsed), status])
        except Exception as e:
            qaoa_rows.append([str(n), str(1 << n), str(layers), f"ERROR: {e}", "FAIL"])

    print_table(
        "QAOA Engine (raw state-vector simulation)",
        ["Qubits", "States", "Layers", "Time", "Status"],
        qaoa_rows,
    )

    # --- Portfolio optimizer ---
    portfolio_rows = []
    for n_assets in [2, 3, 4, 5, 7, 10]:
        req = make_portfolio_request(n_assets)
        try:
            elapsed = time_async(optimize_portfolio, req)
            portfolio_rows.append([str(n_assets), fmt_time(elapsed)])
        except Exception as e:
            portfolio_rows.append([str(n_assets), f"ERROR: {e}"])

    print_table(
        "Portfolio Optimizer",
        ["Assets", "Time"],
        portfolio_rows,
    )

    # --- Route optimizer ---
    route_rows = []
    for n_loc in [3, 4, 5, 6, 8, 10]:
        req = make_route_request(n_loc)
        try:
            elapsed = time_async(optimize_route, req)
            route_rows.append([str(n_loc), fmt_time(elapsed)])
        except Exception as e:
            route_rows.append([str(n_loc), f"ERROR: {e}"])

    print_table(
        "Route Optimizer (TSP)",
        ["Locations", "Time"],
        route_rows,
    )

    # --- Meeting scheduler ---
    schedule_rows = []
    for n_part in [2, 3, 5, 7, 10]:
        req = make_schedule_request(n_part)
        try:
            elapsed = time_async(optimize_schedule, req)
            schedule_rows.append([str(n_part), fmt_time(elapsed)])
        except Exception as e:
            schedule_rows.append([str(n_part), f"ERROR: {e}"])

    print_table(
        "Meeting Scheduler",
        ["Participants", "Time"],
        schedule_rows,
    )

    print()
    print("  Benchmark complete.")
    print()


if __name__ == "__main__":
    main()
