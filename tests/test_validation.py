"""Tests for input validation and preprocessing edge cases.

Covers:
- Portfolio: duplicate assets, unknown symbols, extreme returns/volatility,
  infeasible allocation constraints
- Route: duplicate locations, ocean coordinates, minimum location count
- Schedule: invalid slot formats, past-day filtering, overlapping slots,
  preference-outside-availability
"""

from __future__ import annotations

import pytest

from src.models.schemas import (
    Asset,
    Location,
    MeetingParticipant,
    MeetingScheduleRequest,
    PortfolioRequest,
    RouteRequest,
)
from src.quantum.validation import (
    ValidationError,
    validate_and_preprocess_portfolio,
    validate_and_preprocess_route,
    validate_and_preprocess_schedule,
)


# ---------------------------------------------------------------------------
# Portfolio validation
# ---------------------------------------------------------------------------


class TestPortfolioValidation:
    def test_duplicate_assets_removed(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC"),
                Asset(symbol="ETH"),
                Asset(symbol="btc"),  # duplicate (case-insensitive)
            ],
        )
        result, warnings = validate_and_preprocess_portfolio(request)
        symbols = [a.symbol for a in result.assets]
        assert len(symbols) == 2
        assert any("Duplicate" in w for w in warnings)

    def test_single_asset_after_dedup_fails(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC"),
                Asset(symbol="btc"),
            ],
        )
        with pytest.raises(ValidationError, match="2 unique assets"):
            validate_and_preprocess_portfolio(request)

    def test_unknown_symbol_warning(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC"),
                Asset(symbol="XYZUNKNOWN"),
            ],
        )
        _, warnings = validate_and_preprocess_portfolio(request)
        assert any("XYZUNKNOWN" in w for w in warnings)

    def test_extreme_expected_return_fails(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC", expected_return=10.0),  # 1000%, above 5.0 limit
                Asset(symbol="ETH"),
            ],
        )
        with pytest.raises(ValidationError, match="not realistic"):
            validate_and_preprocess_portfolio(request)

    def test_negative_extreme_return_fails(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC", expected_return=-2.0),  # below -1.0
                Asset(symbol="ETH"),
            ],
        )
        with pytest.raises(ValidationError, match="not realistic"):
            validate_and_preprocess_portfolio(request)

    def test_zero_volatility_fails(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC", volatility=0.001),  # below 0.01
                Asset(symbol="ETH"),
            ],
        )
        with pytest.raises(ValidationError, match="Minimum realistic volatility"):
            validate_and_preprocess_portfolio(request)

    def test_infeasible_min_allocation(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC"),
                Asset(symbol="ETH"),
                Asset(symbol="SOL"),
            ],
            min_allocation=0.5,  # 0.5 * 3 = 1.5 > 1.0
            max_allocation=0.8,
        )
        with pytest.raises(ValidationError, match="Infeasible"):
            validate_and_preprocess_portfolio(request)

    def test_min_equals_max_allocation_fails(self):
        request = PortfolioRequest(
            assets=[
                Asset(symbol="BTC"),
                Asset(symbol="ETH"),
            ],
            min_allocation=0.5,
            max_allocation=0.5,
        )
        with pytest.raises(ValidationError, match="strictly less"):
            validate_and_preprocess_portfolio(request)


# ---------------------------------------------------------------------------
# Route validation
# ---------------------------------------------------------------------------


class TestRouteValidation:
    def test_too_few_locations(self):
        request = RouteRequest(
            locations=[
                Location(name="A", lat=60.0, lon=24.0),
                Location(name="B", lat=61.0, lon=25.0),
                Location(name="C", lat=60.5, lon=24.5),
            ],
        )
        # 3 is the minimum, should pass
        result, _ = validate_and_preprocess_route(request)
        assert len(result.locations) == 3

    def test_near_duplicate_locations_removed(self):
        request = RouteRequest(
            locations=[
                Location(name="A", lat=60.0, lon=24.0),
                Location(name="A-dup", lat=60.0, lon=24.0),  # same coords
                Location(name="B", lat=61.0, lon=25.0),
                Location(name="C", lat=62.0, lon=26.0),
            ],
        )
        result, warnings = validate_and_preprocess_route(request)
        assert len(result.locations) == 3
        assert any("100m" in w for w in warnings)

    def test_ocean_location_warning(self):
        request = RouteRequest(
            locations=[
                Location(name="Helsinki", lat=60.17, lon=24.94),
                Location(name="Mid-Ocean", lat=0.0, lon=-20.0),  # Gulf of Guinea, ocean
                Location(name="Tampere", lat=61.50, lon=23.79),
            ],
        )
        _, warnings = validate_and_preprocess_route(request)
        assert any("ocean" in w.lower() for w in warnings)

    def test_too_few_after_dedup_fails(self):
        request = RouteRequest(
            locations=[
                Location(name="A", lat=60.0, lon=24.0),
                Location(name="B", lat=60.0, lon=24.0),  # same as A
                Location(name="C", lat=60.0, lon=24.0),  # same as A
            ],
        )
        with pytest.raises(ValidationError, match="unique locations"):
            validate_and_preprocess_route(request)

    def test_large_distance_warning(self):
        request = RouteRequest(
            locations=[
                Location(name="Helsinki", lat=60.17, lon=24.94),
                Location(name="Antipode", lat=-60.17, lon=-155.06),  # antipodal to Helsinki, >20,000km
                Location(name="Tokyo", lat=35.68, lon=139.69),
            ],
        )
        _, warnings = validate_and_preprocess_route(request)
        assert any("20,000 km" in w for w in warnings)


# ---------------------------------------------------------------------------
# Schedule validation
# ---------------------------------------------------------------------------


class TestScheduleValidation:
    def test_invalid_slot_format(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["InvalidFormat"],
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-10:00"],
                ),
            ],
        )
        with pytest.raises(ValidationError, match="Invalid time slot format"):
            validate_and_preprocess_schedule(request)

    def test_invalid_day_name(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Xyz 09:00-10:00"],
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-10:00"],
                ),
            ],
        )
        with pytest.raises(ValidationError, match="Unrecognized day"):
            validate_and_preprocess_schedule(request)

    def test_end_before_start_fails(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Mon 10:00-09:00"],  # end before start
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-10:00"],
                ),
            ],
        )
        with pytest.raises(ValidationError, match="end time must be after"):
            validate_and_preprocess_schedule(request)

    def test_preference_outside_availability_warning(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Mon 09:00-11:00"],
                    preferences=["Tue 14:00-16:00"],  # not in available
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-11:00"],
                ),
            ],
        )
        _, warnings = validate_and_preprocess_schedule(request)
        assert any("not within their available" in w for w in warnings)

    def test_no_overlap_warning(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Mon 09:00-10:00"],
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Fri 14:00-15:00"],
                ),
            ],
        )
        _, warnings = validate_and_preprocess_schedule(request)
        assert any("overlapping availability" in w.lower() for w in warnings)

    def test_slot_too_short_for_duration_warning(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Mon 09:00-09:30"],  # 30 min < 60 min
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-09:30"],
                ),
            ],
            duration_minutes=60,
        )
        _, warnings = validate_and_preprocess_schedule(request)
        assert any("long enough" in w for w in warnings)

    def test_overlapping_slots_merged(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Mon 09:00-11:00", "Mon 10:00-12:00"],
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-12:00"],
                ),
            ],
        )
        result, warnings = validate_and_preprocess_schedule(request)
        # Alice's slots should be merged into Mon 09:00-12:00
        alice = result.participants[0]
        assert len(alice.available_slots) == 1
        assert "09:00-12:00" in alice.available_slots[0]

    def test_invalid_hour_fails(self):
        request = MeetingScheduleRequest(
            participants=[
                MeetingParticipant(
                    name="Alice",
                    available_slots=["Mon 25:00-26:00"],  # invalid hours
                ),
                MeetingParticipant(
                    name="Bob",
                    available_slots=["Mon 09:00-10:00"],
                ),
            ],
        )
        with pytest.raises(ValidationError, match="Invalid time"):
            validate_and_preprocess_schedule(request)
