"""FastAPI application for Quantum MCP Relayer REST API.

Performance-optimized: CPU-bound quantum computations are offloaded
to a thread pool via asyncio.to_thread() so the event loop stays
responsive. Results are cached with a 60-second TTL to avoid
redundant re-computation of identical requests.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.api.cache import portfolio_cache, route_cache, schedule_cache
from src.api.middleware import attach_middleware
from src.api.routes_auth import router as auth_router
from src.api.routes_billing import router as billing_router
from src.config import get_settings
from src.models.schemas import (
    MeetingScheduleRequest,
    MeetingScheduleResult,
    PortfolioRequest,
    PortfolioResult,
    RouteRequest,
    RouteResult,
)
from src.quantum.portfolio import optimize_portfolio
from src.quantum.router import optimize_route
from src.quantum.scheduler import optimize_schedule
from src.quantum.validation import ValidationError

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Quantum MCP Relayer",
    description="Quantum computing as a service — portfolio optimization, route planning, and meeting scheduling powered by QAOA.",
    version="0.1.0",
)

attach_middleware(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(billing_router)


def _run_sync(async_fn, *args):
    """Run an async function synchronously in a thread.

    asyncio.to_thread() runs callables in a thread pool. Since the
    quantum optimize_* functions are async (they use `await`), we
    need to run them in a new event loop within that thread.
    """
    import asyncio as _asyncio
    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(async_fn(*args))
    finally:
        loop.close()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": settings.quantum_backend}


@app.post("/api/v1/portfolio/optimize", response_model=PortfolioResult)
async def api_optimize_portfolio(request: PortfolioRequest) -> PortfolioResult:
    """Optimize portfolio allocation using quantum QAOA.

    CPU-bound computation is offloaded to a thread so the event loop
    stays responsive. Results are cached for 60 seconds.
    """
    try:
        cached = portfolio_cache.get(request)
        if cached is not None:
            return cached
        result = await asyncio.to_thread(_run_sync, optimize_portfolio, request)
        portfolio_cache.put(request, result)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.message) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e}") from e


@app.post("/api/v1/route/optimize", response_model=RouteResult)
async def api_optimize_route(request: RouteRequest) -> RouteResult:
    """Find optimal route through locations using quantum TSP solver.

    CPU-bound computation is offloaded to a thread so the event loop
    stays responsive. Results are cached for 60 seconds.
    """
    try:
        cached = route_cache.get(request)
        if cached is not None:
            return cached
        result = await asyncio.to_thread(_run_sync, optimize_route, request)
        route_cache.put(request, result)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.message) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e}") from e


@app.post("/api/v1/schedule/optimize", response_model=MeetingScheduleResult)
async def api_optimize_schedule(request: MeetingScheduleRequest) -> MeetingScheduleResult:
    """Find optimal meeting schedule using quantum optimization.

    CPU-bound computation is offloaded to a thread so the event loop
    stays responsive. Results are cached for 60 seconds.
    """
    try:
        cached = schedule_cache.get(request)
        if cached is not None:
            return cached
        result = await asyncio.to_thread(_run_sync, optimize_schedule, request)
        schedule_cache.put(request, result)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.message) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e}") from e


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------

class WaitlistRequest(BaseModel):
    email: str = Field(description="Email address to add to the waitlist")


class WaitlistResponse(BaseModel):
    message: str
    email: str


# In-memory store — swap for a database in production
_waitlist: set[str] = set()


def _is_valid_email(email: str) -> bool:
    """Basic but stricter email validation."""
    # Must have local@domain.tld with at least 2-char TLD
    return bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email))


@app.post("/api/v1/waitlist", response_model=WaitlistResponse)
async def join_waitlist(request: WaitlistRequest) -> WaitlistResponse:
    """Add an email address to the early-access waitlist."""
    email = request.email.strip().lower()
    if not email or not _is_valid_email(email):
        raise HTTPException(status_code=422, detail="Please provide a valid email address.")
    if email in _waitlist:
        return WaitlistResponse(
            message="You're already on the waitlist! We'll be in touch soon.",
            email=email,
        )
    _waitlist.add(email)
    logger.info("Waitlist signup: %s (total: %d)", email, len(_waitlist))
    return WaitlistResponse(
        message="You're on the list! We'll send your API key soon.",
        email=email,
    )


# ---------------------------------------------------------------------------
# Static file serving — must be LAST so it doesn't shadow API routes
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).resolve().parent.parent.parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
