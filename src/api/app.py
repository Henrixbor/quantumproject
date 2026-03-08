"""FastAPI application for Quantum MCP Relayer REST API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

settings = get_settings()

app = FastAPI(
    title="Quantum MCP Relayer",
    description="Quantum computing as a service — portfolio optimization, route planning, and meeting scheduling powered by QAOA.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
