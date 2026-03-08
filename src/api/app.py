"""FastAPI application for Quantum MCP Relayer REST API."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.api.middleware import attach_middleware
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

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Quantum MCP Relayer",
    description="Quantum computing as a service — portfolio optimization, route planning, and meeting scheduling powered by QAOA.",
    version="0.1.0",
)

attach_middleware(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "backend": settings.quantum_backend}


@app.post("/api/v1/portfolio/optimize", response_model=PortfolioResult)
async def api_optimize_portfolio(request: PortfolioRequest) -> PortfolioResult:
    """Optimize portfolio allocation using quantum QAOA."""
    try:
        return await optimize_portfolio(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e}") from e


@app.post("/api/v1/route/optimize", response_model=RouteResult)
async def api_optimize_route(request: RouteRequest) -> RouteResult:
    """Find optimal route through locations using quantum TSP solver."""
    try:
        return await optimize_route(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {e}") from e


@app.post("/api/v1/schedule/optimize", response_model=MeetingScheduleResult)
async def api_optimize_schedule(request: MeetingScheduleRequest) -> MeetingScheduleResult:
    """Find optimal meeting schedule using quantum optimization."""
    try:
        return await optimize_schedule(request)
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


@app.post("/api/v1/waitlist", response_model=WaitlistResponse)
async def join_waitlist(request: WaitlistRequest) -> WaitlistResponse:
    """Add an email address to the early-access waitlist."""
    email = request.email.strip().lower()
    if not email or "@" not in email:
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
