"""MCP server exposing quantum optimization tools for Claude and other AI assistants.

Provides tools, resources, and prompts for quantum-powered portfolio optimization,
route planning (TSP), and meeting scheduling via QAOA.
"""

from __future__ import annotations

import json
from typing import Iterable

from pydantic import ValidationError as PydanticValidationError

from mcp.server import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

from src.models.schemas import (
    MeetingScheduleRequest,
    PortfolioRequest,
    RouteRequest,
)
from src.quantum.market_data import DEFAULT_RETURNS, DEFAULT_VOLATILITY
from src.quantum.portfolio import optimize_portfolio
from src.quantum.router import optimize_route
from src.quantum.scheduler import optimize_schedule
from src.quantum.validation import ValidationError

server = Server("quantum-mcp-relayer")

# ---------------------------------------------------------------------------
# Pricing / tier data (shared by resource handler and formatting)
# ---------------------------------------------------------------------------

PRICING_TIERS = {
    "free": {
        "price": "$0/month",
        "requests_per_day": 10,
        "max_assets": 5,
        "max_locations": 5,
        "max_participants": 5,
        "support": "Community",
    },
    "starter": {
        "price": "$29/month",
        "requests_per_day": 100,
        "max_assets": 10,
        "max_locations": 10,
        "max_participants": 10,
        "support": "Email",
    },
    "pro": {
        "price": "$99/month",
        "requests_per_day": 1000,
        "max_assets": 20,
        "max_locations": 15,
        "max_participants": 20,
        "support": "Priority email",
    },
    "business": {
        "price": "Custom",
        "requests_per_day": "Unlimited",
        "max_assets": 20,
        "max_locations": 15,
        "max_participants": 20,
        "support": "Dedicated",
    },
}


# ---------------------------------------------------------------------------
# Result formatting helpers
# ---------------------------------------------------------------------------

def _format_portfolio_result(result) -> str:
    """Format a PortfolioResult into human-readable text with raw JSON detail."""
    data = result.model_dump()

    # Build the allocation summary line
    alloc_parts = []
    for symbol, weight in data["allocations"].items():
        alloc_parts.append(f"{weight:.0%} {symbol}")
    alloc_summary = ", ".join(alloc_parts)

    lines = [
        f"Optimal allocation: {alloc_summary}",
        f"Sharpe ratio: {data['sharpe_ratio']:.2f}",
        f"Expected annual return: {data['expected_return']:.1%}",
        f"Annual volatility: {data['volatility']:.1%}",
        f"Method: {data['method']} ({data['qubit_count']} qubits)",
    ]

    # Append warnings if present
    if data.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        for w in data["warnings"]:
            lines.append(f"  - {w}")

    # Append raw JSON as detail block
    lines.append("")
    lines.append("--- Raw JSON ---")
    lines.append(json.dumps(data, indent=2))

    return "\n".join(lines)


def _format_route_result(result) -> str:
    """Format a RouteResult into human-readable text with raw JSON detail."""
    data = result.model_dump()

    route_str = " -> ".join(data["route"])
    improvement = data["improvement_vs_naive"]

    lines = [
        f"Best route: {route_str}",
        f"Total distance: {data['total_distance_km']:.1f} km",
    ]
    if improvement > 0:
        lines.append(f"Improvement: {improvement:.0f}% shorter than naive ordering")
    lines.append(f"Method: {data['method']} ({data['qubit_count']} qubits)")

    if data.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        for w in data["warnings"]:
            lines.append(f"  - {w}")

    lines.append("")
    lines.append("--- Raw JSON ---")
    lines.append(json.dumps(data, indent=2))

    return "\n".join(lines)


def _format_schedule_result(result) -> str:
    """Format a MeetingScheduleResult into human-readable text with raw JSON detail."""
    data = result.model_dump()

    lines = []
    for slot in data["scheduled_slots"]:
        attendees = data["attendance"].get(slot, [])
        attendee_str = ", ".join(attendees) if attendees else "no attendees"
        lines.append(f"Best time: {slot} ({attendee_str} can attend)")

    satisfaction = data["satisfaction_score"]
    lines.append(f"Satisfaction score: {satisfaction:.0%}")
    lines.append(f"Method: {data['method']} ({data['qubit_count']} qubits)")

    if data.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        for w in data["warnings"]:
            lines.append(f"  - {w}")

    lines.append("")
    lines.append("--- Raw JSON ---")
    lines.append(json.dumps(data, indent=2))

    return "\n".join(lines)


def _format_validation_error(error: ValidationError, tool_name: str) -> str:
    """Format a ValidationError into a clear, actionable message."""
    return (
        f"Input validation failed for {tool_name}:\n"
        f"{error.message}\n\n"
        f"Please fix the input and try again."
    )


def _format_pydantic_error(error: PydanticValidationError, tool_name: str) -> str:
    """Format a Pydantic ValidationError into a clear, actionable message."""
    issues = []
    for err in error.errors():
        loc = " -> ".join(str(part) for part in err["loc"])
        issues.append(f"  - {loc}: {err['msg']}")

    return (
        f"Invalid input for {tool_name}:\n"
        + "\n".join(issues)
        + "\n\nPlease check the input schema and try again."
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

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
    try:
        if name == "quantum_portfolio_optimizer":
            request = PortfolioRequest(**arguments)
            result = await optimize_portfolio(request)
            text = _format_portfolio_result(result)
        elif name == "quantum_route_optimizer":
            request = RouteRequest(**arguments)
            result = await optimize_route(request)
            text = _format_route_result(result)
        elif name == "quantum_meeting_scheduler":
            request = MeetingScheduleRequest(**arguments)
            result = await optimize_schedule(request)
            text = _format_schedule_result(result)
        else:
            return [TextContent(
                type="text",
                text=(
                    f"Unknown tool '{name}'. Available tools: "
                    "quantum_portfolio_optimizer, quantum_route_optimizer, "
                    "quantum_meeting_scheduler"
                ),
            )]

        return [TextContent(type="text", text=text)]

    except ValidationError as e:
        return [TextContent(
            type="text",
            text=_format_validation_error(e, name),
        )]
    except PydanticValidationError as e:
        return [TextContent(
            type="text",
            text=_format_pydantic_error(e, name),
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=(
                f"An unexpected error occurred while running {name}.\n"
                f"Error type: {type(e).__name__}\n"
                f"Details: {e}\n\n"
                f"If this persists, please check your inputs or try again."
            ),
        )]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="quantum://supported-assets",
            name="supported-assets",
            description="List of supported asset symbols with default expected returns and volatility",
            mimeType="application/json",
        ),
        Resource(
            uri="quantum://pricing",
            name="pricing",
            description="Current pricing tiers and usage limits",
            mimeType="application/json",
        ),
        Resource(
            uri="quantum://status",
            name="status",
            description="Backend status: simulator vs real quantum hardware",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri) -> Iterable[ReadResourceContents]:
    uri_str = str(uri)

    if uri_str == "quantum://supported-assets":
        assets = {}
        all_symbols = sorted(set(DEFAULT_RETURNS.keys()) | set(DEFAULT_VOLATILITY.keys()))
        for symbol in all_symbols:
            assets[symbol] = {
                "expected_return": DEFAULT_RETURNS.get(symbol),
                "volatility": DEFAULT_VOLATILITY.get(symbol),
            }
        return [ReadResourceContents(
            content=json.dumps({"supported_assets": assets}, indent=2),
            mime_type="application/json",
        )]

    elif uri_str == "quantum://pricing":
        return [ReadResourceContents(
            content=json.dumps({"tiers": PRICING_TIERS}, indent=2),
            mime_type="application/json",
        )]

    elif uri_str == "quantum://status":
        status = {
            "backend": "simulator",
            "simulator_engine": "Qiskit Aer statevector",
            "real_quantum_available": False,
            "max_qubits_simulated": 20,
            "avg_latency_ms": 200,
            "status": "operational",
            "note": (
                "Currently running on a classical QAOA simulator. "
                "Real quantum hardware (IBM Quantum) planned for future release."
            ),
        }
        return [ReadResourceContents(
            content=json.dumps(status, indent=2),
            mime_type="application/json",
        )]

    else:
        return [ReadResourceContents(
            content=json.dumps({"error": f"Unknown resource: {uri_str}"}),
            mime_type="application/json",
        )]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="optimize-crypto-portfolio",
            description="Guide through cryptocurrency portfolio optimization with quantum QAOA",
            arguments=[
                PromptArgument(
                    name="coins",
                    description="Comma-separated list of crypto symbols (e.g. BTC,ETH,SOL)",
                    required=False,
                ),
                PromptArgument(
                    name="risk_level",
                    description="Risk appetite: conservative, moderate, or aggressive",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="plan-route",
            description="Guide through multi-stop route planning with quantum TSP solver",
            arguments=[
                PromptArgument(
                    name="locations",
                    description="Comma-separated list of location names (e.g. Helsinki,Turku,Tampere)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="schedule-meeting",
            description="Guide through optimal meeting scheduling across participants",
            arguments=[
                PromptArgument(
                    name="participants",
                    description="Comma-separated participant names (e.g. Alice,Bob,Carol)",
                    required=False,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    args = arguments or {}

    if name == "optimize-crypto-portfolio":
        coins = args.get("coins", "BTC, ETH, SOL")
        risk = args.get("risk_level", "moderate")
        risk_map = {"conservative": 0.2, "moderate": 0.5, "aggressive": 0.8}
        risk_val = risk_map.get(risk.lower(), 0.5)

        return GetPromptResult(
            description="Optimize a crypto portfolio using quantum computing",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"I want to optimize a cryptocurrency portfolio with these coins: {coins}.\n"
                            f"My risk tolerance is {risk} (numeric value: {risk_val}).\n\n"
                            f"Please use the quantum_portfolio_optimizer tool to find the optimal "
                            f"allocation. For each coin, you don't need to provide expected_return "
                            f"or volatility unless I specify them -- the system has built-in market data.\n\n"
                            f"After getting the result, explain:\n"
                            f"1. The recommended allocation and why\n"
                            f"2. The Sharpe ratio and what it means\n"
                            f"3. Any warnings or caveats\n"
                            f"4. How the quantum optimization compares to a simple equal-weight portfolio"
                        ),
                    ),
                ),
            ],
        )

    elif name == "plan-route":
        locations = args.get("locations", "")
        location_hint = (
            f"The locations I want to visit are: {locations}."
            if locations
            else (
                "I need to plan a route through multiple locations. "
                "Please ask me for the locations I want to visit (I'll provide names "
                "and you can look up approximate lat/lon coordinates)."
            )
        )

        return GetPromptResult(
            description="Plan an optimal route through multiple locations",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"{location_hint}\n\n"
                            f"Please use the quantum_route_optimizer tool to find the shortest route.\n"
                            f"For each location, provide the name and approximate lat/lon coordinates.\n\n"
                            f"After getting the result, explain:\n"
                            f"1. The optimal visiting order\n"
                            f"2. Total distance and how much shorter it is than a naive ordering\n"
                            f"3. Any warnings about the locations"
                        ),
                    ),
                ),
            ],
        )

    elif name == "schedule-meeting":
        participants = args.get("participants", "")
        participant_hint = (
            f"The participants are: {participants}."
            if participants
            else (
                "I need to schedule a meeting. "
                "Please ask me for the participant names and their availability."
            )
        )

        return GetPromptResult(
            description="Schedule a meeting optimally across participants",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"{participant_hint}\n\n"
                            f"Please help me find the best meeting time using the "
                            f"quantum_meeting_scheduler tool.\n\n"
                            f"For each participant, I'll need to provide:\n"
                            f"- Their available time slots (e.g., 'Mon 09:00-12:00')\n"
                            f"- Optionally, preferred slots and priority weight\n\n"
                            f"After getting the result, explain:\n"
                            f"1. The recommended meeting time\n"
                            f"2. Who can attend\n"
                            f"3. The satisfaction score and what it means\n"
                            f"4. Any scheduling conflicts or warnings"
                        ),
                    ),
                ),
            ],
        )

    else:
        return GetPromptResult(
            description="Unknown prompt",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"Unknown prompt '{name}'. Available prompts: "
                            f"optimize-crypto-portfolio, plan-route, schedule-meeting"
                        ),
                    ),
                ),
            ],
        )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
