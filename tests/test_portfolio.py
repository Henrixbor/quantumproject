import pytest

from src.models.schemas import Asset, PortfolioRequest
from src.quantum.portfolio import optimize_portfolio


@pytest.mark.asyncio
async def test_basic_portfolio_optimization():
    request = PortfolioRequest(
        assets=[
            Asset(symbol="BTC"),
            Asset(symbol="ETH"),
            Asset(symbol="SOL"),
        ],
        risk_tolerance=0.5,
    )
    result = await optimize_portfolio(request)

    assert len(result.allocations) == 3
    assert abs(sum(result.allocations.values()) - 1.0) < 0.01
    assert all(v >= 0 for v in result.allocations.values())
    assert result.sharpe_ratio > 0
    assert result.qubit_count > 0
    assert "QAOA" in result.method


@pytest.mark.asyncio
async def test_portfolio_respects_constraints():
    request = PortfolioRequest(
        assets=[Asset(symbol="BTC"), Asset(symbol="ETH")],
        min_allocation=0.2,
        max_allocation=0.8,
    )
    result = await optimize_portfolio(request)

    for alloc in result.allocations.values():
        assert alloc >= 0.19  # slight tolerance
        assert alloc <= 0.81


@pytest.mark.asyncio
async def test_portfolio_risk_tolerance():
    conservative = await optimize_portfolio(
        PortfolioRequest(
            assets=[Asset(symbol="BTC"), Asset(symbol="GLD")],
            risk_tolerance=0.1,
        )
    )
    aggressive = await optimize_portfolio(
        PortfolioRequest(
            assets=[Asset(symbol="BTC"), Asset(symbol="GLD")],
            risk_tolerance=0.9,
        )
    )
    # Both should produce valid results
    assert abs(sum(conservative.allocations.values()) - 1.0) < 0.01
    assert abs(sum(aggressive.allocations.values()) - 1.0) < 0.01
