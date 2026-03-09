"""Tests for the MCP server: tool listing, tool calling, result formatting,
resource listing/reading, prompt listing/getting, and error handling."""

import json

import pytest

from src.mcp.server import (
    PRICING_TIERS,
    _format_pydantic_error,
    _format_portfolio_result,
    _format_route_result,
    _format_schedule_result,
    _format_validation_error,
    call_tool,
    get_prompt,
    list_prompts,
    list_resources,
    list_tools,
    read_resource,
)
from src.quantum.validation import ValidationError


# ---------------------------------------------------------------------------
# Tool listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_tools_returns_three_tools():
    tools = await list_tools()
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert names == {
        "quantum_portfolio_optimizer",
        "quantum_route_optimizer",
        "quantum_meeting_scheduler",
    }


@pytest.mark.asyncio
async def test_list_tools_all_have_input_schemas():
    tools = await list_tools()
    for tool in tools:
        assert tool.inputSchema is not None
        assert tool.inputSchema["type"] == "object"
        assert "properties" in tool.inputSchema
        assert "required" in tool.inputSchema


# ---------------------------------------------------------------------------
# Tool calling — valid inputs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_portfolio_optimizer_valid():
    arguments = {
        "assets": [
            {"symbol": "BTC"},
            {"symbol": "ETH"},
            {"symbol": "SOL"},
        ],
        "risk_tolerance": 0.5,
    }
    result = await call_tool("quantum_portfolio_optimizer", arguments)
    assert len(result) == 1
    text = result[0].text

    # Human-readable section
    assert "Optimal allocation:" in text
    assert "Sharpe ratio:" in text
    assert "Expected annual return:" in text

    # Raw JSON section
    assert "--- Raw JSON ---" in text
    json_part = text.split("--- Raw JSON ---")[1].strip()
    data = json.loads(json_part)
    assert "allocations" in data
    assert "sharpe_ratio" in data


@pytest.mark.asyncio
async def test_call_route_optimizer_valid():
    arguments = {
        "locations": [
            {"name": "Helsinki", "lat": 60.17, "lon": 24.94},
            {"name": "Turku", "lat": 60.45, "lon": 22.27},
            {"name": "Tampere", "lat": 61.50, "lon": 23.79},
        ],
        "return_to_start": True,
    }
    result = await call_tool("quantum_route_optimizer", arguments)
    assert len(result) == 1
    text = result[0].text

    assert "Best route:" in text
    assert "Total distance:" in text
    assert "km" in text
    assert "--- Raw JSON ---" in text

    json_part = text.split("--- Raw JSON ---")[1].strip()
    data = json.loads(json_part)
    assert "route" in data
    assert "total_distance_km" in data


@pytest.mark.asyncio
async def test_call_meeting_scheduler_valid():
    arguments = {
        "participants": [
            {"name": "Alice", "available_slots": ["Fri 09:00-12:00", "Fri 14:00-16:00"]},
            {"name": "Bob", "available_slots": ["Fri 10:00-13:00"]},
        ],
        "duration_minutes": 60,
    }
    result = await call_tool("quantum_meeting_scheduler", arguments)
    assert len(result) == 1
    text = result[0].text

    assert "Best time:" in text
    assert "Satisfaction score:" in text
    assert "--- Raw JSON ---" in text


# ---------------------------------------------------------------------------
# Tool calling — invalid inputs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_unknown_tool():
    result = await call_tool("nonexistent_tool", {})
    assert len(result) == 1
    assert "Unknown tool" in result[0].text
    assert "nonexistent_tool" in result[0].text


@pytest.mark.asyncio
async def test_call_portfolio_too_few_assets():
    arguments = {
        "assets": [{"symbol": "BTC"}],
    }
    result = await call_tool("quantum_portfolio_optimizer", arguments)
    text = result[0].text
    # Pydantic validation catches minItems=2
    assert "Invalid input" in text or "validation" in text.lower()


@pytest.mark.asyncio
async def test_call_portfolio_missing_assets():
    result = await call_tool("quantum_portfolio_optimizer", {})
    text = result[0].text
    assert "Invalid input" in text or "validation" in text.lower() or "required" in text.lower()


@pytest.mark.asyncio
async def test_call_route_too_few_locations():
    arguments = {
        "locations": [
            {"name": "A", "lat": 0.0, "lon": 0.0},
            {"name": "B", "lat": 1.0, "lon": 1.0},
        ],
    }
    result = await call_tool("quantum_route_optimizer", arguments)
    text = result[0].text
    assert "validation" in text.lower() or "Invalid input" in text


@pytest.mark.asyncio
async def test_call_portfolio_unrealistic_return():
    """Validation catches expected_return > 5.0 as a fatal error."""
    arguments = {
        "assets": [
            {"symbol": "BTC", "expected_return": 10.0},
            {"symbol": "ETH"},
        ],
    }
    result = await call_tool("quantum_portfolio_optimizer", arguments)
    text = result[0].text
    assert "validation failed" in text.lower() or "not realistic" in text.lower()


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------

def test_format_portfolio_result():
    from src.models.schemas import PortfolioResult

    result = PortfolioResult(
        allocations={"BTC": 0.35, "ETH": 0.45, "SOL": 0.20},
        expected_return=0.72,
        volatility=0.55,
        sharpe_ratio=2.41,
        method="QAOA (simulated)",
        qubit_count=9,
        warnings=["Test warning"],
    )
    text = _format_portfolio_result(result)
    assert "35% BTC" in text
    assert "45% ETH" in text
    assert "20% SOL" in text
    assert "2.41" in text
    assert "Test warning" in text
    assert "--- Raw JSON ---" in text


def test_format_route_result():
    from src.models.schemas import RouteResult

    result = RouteResult(
        route=["Helsinki", "Turku", "Tampere", "Helsinki"],
        total_distance_km=453.2,
        improvement_vs_naive=23.0,
        method="QAOA (simulated)",
        qubit_count=9,
        warnings=[],
    )
    text = _format_route_result(result)
    assert "Helsinki -> Turku -> Tampere -> Helsinki" in text
    assert "453.2 km" in text
    assert "23% shorter" in text


def test_format_schedule_result():
    from src.models.schemas import MeetingScheduleResult

    result = MeetingScheduleResult(
        scheduled_slots=["Mon 10:00-11:00"],
        attendance={"Mon 10:00-11:00": ["Alice", "Bob", "Carol"]},
        satisfaction_score=1.0,
        method="QAOA (simulated)",
        qubit_count=5,
        warnings=[],
    )
    text = _format_schedule_result(result)
    assert "Mon 10:00-11:00" in text
    assert "Alice, Bob, Carol" in text
    assert "100%" in text


def test_format_validation_error():
    err = ValidationError("At least 2 unique assets are required.")
    text = _format_validation_error(err, "quantum_portfolio_optimizer")
    assert "validation failed" in text.lower()
    assert "At least 2 unique assets" in text
    assert "fix the input" in text.lower()


def test_format_portfolio_result_no_warnings():
    from src.models.schemas import PortfolioResult

    result = PortfolioResult(
        allocations={"BTC": 0.50, "ETH": 0.50},
        expected_return=0.70,
        volatility=0.60,
        sharpe_ratio=1.10,
        method="QAOA (simulated)",
        qubit_count=6,
        warnings=[],
    )
    text = _format_portfolio_result(result)
    assert "Warnings:" not in text
    assert "Optimal allocation:" in text


# ---------------------------------------------------------------------------
# Warnings / borderline inputs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_symbol_warning():
    """Unknown symbol should produce a warning but still succeed."""
    arguments = {
        "assets": [
            {"symbol": "BTC"},
            {"symbol": "XYZFAKE"},
        ],
    }
    result = await call_tool("quantum_portfolio_optimizer", arguments)
    text = result[0].text
    # Should contain the result AND a warning about the unknown symbol
    assert "Optimal allocation:" in text
    assert "XYZFAKE" in text
    assert "not in our default market data" in text or "not recognized" in text


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_resources_returns_three():
    resources = await list_resources()
    assert len(resources) == 3
    uris = {str(r.uri) for r in resources}
    assert "quantum://supported-assets" in uris
    assert "quantum://pricing" in uris
    assert "quantum://status" in uris


@pytest.mark.asyncio
async def test_read_supported_assets_resource():
    contents = await read_resource("quantum://supported-assets")
    contents_list = list(contents)
    assert len(contents_list) == 1
    data = json.loads(contents_list[0].content)
    assert "supported_assets" in data
    assert "BTC" in data["supported_assets"]
    assert "ETH" in data["supported_assets"]
    assert "expected_return" in data["supported_assets"]["BTC"]
    assert "volatility" in data["supported_assets"]["BTC"]


@pytest.mark.asyncio
async def test_read_pricing_resource():
    contents = await read_resource("quantum://pricing")
    contents_list = list(contents)
    data = json.loads(contents_list[0].content)
    assert "tiers" in data
    assert "free" in data["tiers"]
    assert "pro" in data["tiers"]


@pytest.mark.asyncio
async def test_read_status_resource():
    contents = await read_resource("quantum://status")
    contents_list = list(contents)
    data = json.loads(contents_list[0].content)
    assert data["backend"] == "simulator"
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_read_unknown_resource():
    contents = await read_resource("quantum://nonexistent")
    contents_list = list(contents)
    data = json.loads(contents_list[0].content)
    assert "error" in data


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_prompts_returns_three():
    prompts = await list_prompts()
    assert len(prompts) == 3
    names = {p.name for p in prompts}
    assert names == {"optimize-crypto-portfolio", "plan-route", "schedule-meeting"}


@pytest.mark.asyncio
async def test_get_portfolio_prompt_default():
    result = await get_prompt("optimize-crypto-portfolio", None)
    assert result.description is not None
    assert len(result.messages) == 1
    msg = result.messages[0]
    assert msg.role == "user"
    assert "quantum_portfolio_optimizer" in msg.content.text
    # Default coins should appear
    assert "BTC" in msg.content.text


@pytest.mark.asyncio
async def test_get_portfolio_prompt_with_args():
    result = await get_prompt(
        "optimize-crypto-portfolio",
        {"coins": "ADA,DOT,LINK", "risk_level": "aggressive"},
    )
    msg = result.messages[0]
    assert "ADA,DOT,LINK" in msg.content.text
    assert "aggressive" in msg.content.text
    assert "0.8" in msg.content.text


@pytest.mark.asyncio
async def test_get_route_prompt():
    result = await get_prompt("plan-route", {"locations": "Paris,Lyon,Marseille"})
    msg = result.messages[0]
    assert "Paris,Lyon,Marseille" in msg.content.text
    assert "quantum_route_optimizer" in msg.content.text


@pytest.mark.asyncio
async def test_get_schedule_prompt():
    result = await get_prompt("schedule-meeting", {"participants": "Alice,Bob"})
    msg = result.messages[0]
    assert "Alice,Bob" in msg.content.text
    assert "quantum_meeting_scheduler" in msg.content.text


@pytest.mark.asyncio
async def test_get_unknown_prompt():
    result = await get_prompt("nonexistent", None)
    msg = result.messages[0]
    assert "Unknown prompt" in msg.content.text
