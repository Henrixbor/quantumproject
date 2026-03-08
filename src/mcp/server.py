"""MCP server exposing quantum optimization tools for Claude and other AI assistants."""

from __future__ import annotations

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.models.schemas import (
    MeetingScheduleRequest,
    PortfolioRequest,
    RouteRequest,
)
from src.quantum.portfolio import optimize_portfolio
from src.quantum.router import optimize_route
from src.quantum.scheduler import optimize_schedule

server = Server("quantum-mcp-relayer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="quantum_portfolio_optimizer",
            description=(
                "Optimize investment portfolio allocation using quantum QAOA algorithm. "
                "Provides optimal asset allocation with Sharpe ratio optimization. "
                "Supports crypto (BTC, ETH, SOL...) and stocks (AAPL, GOOGL...)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "assets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string", "description": "Ticker symbol"},
                                "expected_return": {
                                    "type": "number",
                                    "description": "Expected annual return (optional)",
                                },
                                "volatility": {
                                    "type": "number",
                                    "description": "Annual volatility (optional)",
                                },
                            },
                            "required": ["symbol"],
                        },
                        "minItems": 2,
                        "maxItems": 20,
                        "description": "Assets to optimize",
                    },
                    "risk_tolerance": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5,
                        "description": "0=conservative, 1=aggressive",
                    },
                },
                "required": ["assets"],
            },
        ),
        Tool(
            name="quantum_route_optimizer",
            description=(
                "Find the shortest route through multiple locations using quantum TSP solver. "
                "20-40% shorter routes than naive ordering. Provide lat/lon coordinates."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "locations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                            },
                            "required": ["name", "lat", "lon"],
                        },
                        "minItems": 3,
                        "maxItems": 15,
                        "description": "Locations to visit",
                    },
                    "return_to_start": {
                        "type": "boolean",
                        "default": True,
                        "description": "Return to starting point",
                    },
                },
                "required": ["locations"],
            },
        ),
        Tool(
            name="quantum_meeting_scheduler",
            description=(
                "Schedule meetings optimally across participants with availability constraints. "
                "90% satisfaction vs 60% with classical methods. Respects preferences and priorities."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "participants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "available_slots": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "e.g. ['Mon 9:00-11:00', 'Tue 14:00-16:00']",
                                },
                                "priority": {
                                    "type": "number",
                                    "default": 1.0,
                                    "description": "Priority weight",
                                },
                                "preferences": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Preferred slots (subset of available)",
                                },
                            },
                            "required": ["name", "available_slots"],
                        },
                        "minItems": 2,
                        "maxItems": 20,
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "default": 60,
                        "description": "Meeting duration in minutes",
                    },
                    "num_meetings": {
                        "type": "integer",
                        "default": 1,
                        "description": "Number of meetings to schedule",
                    },
                },
                "required": ["participants"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "quantum_portfolio_optimizer":
        request = PortfolioRequest(**arguments)
        result = await optimize_portfolio(request)
    elif name == "quantum_route_optimizer":
        request = RouteRequest(**arguments)
        result = await optimize_route(request)
    elif name == "quantum_meeting_scheduler":
        request = MeetingScheduleRequest(**arguments)
        result = await optimize_schedule(request)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return [TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
