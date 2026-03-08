import pytest

from src.models.schemas import Location, RouteRequest
from src.quantum.router import optimize_route


@pytest.mark.asyncio
async def test_basic_route_optimization():
    request = RouteRequest(
        locations=[
            Location(name="Helsinki", lat=60.17, lon=24.94),
            Location(name="Tampere", lat=61.50, lon=23.79),
            Location(name="Turku", lat=60.45, lon=22.27),
        ],
        return_to_start=True,
    )
    result = await optimize_route(request)

    assert len(result.route) == 4  # 3 + return
    assert result.route[-1] == result.route[0]
    assert result.total_distance_km > 0
    assert result.qubit_count > 0


@pytest.mark.asyncio
async def test_route_no_return():
    request = RouteRequest(
        locations=[
            Location(name="A", lat=0.0, lon=0.0),
            Location(name="B", lat=1.0, lon=1.0),
            Location(name="C", lat=2.0, lon=0.0),
        ],
        return_to_start=False,
    )
    result = await optimize_route(request)

    assert len(result.route) == 3
    assert result.total_distance_km > 0


@pytest.mark.asyncio
async def test_route_larger_set():
    locations = [
        Location(name=f"City{i}", lat=60 + i * 0.5, lon=24 + i * 0.3)
        for i in range(7)
    ]
    request = RouteRequest(locations=locations)
    result = await optimize_route(request)

    assert len(result.route) == 8  # 7 + return
    assert result.total_distance_km > 0
