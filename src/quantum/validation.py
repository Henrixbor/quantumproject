"""Input validation and preprocessing for quantum computations.

Provides validate_and_preprocess_* functions for portfolio, route, and schedule
requests. Each returns (processed_request, warnings) where warnings is a list
of non-fatal issues the caller should surface to the user.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from datetime import datetime

import numpy as np

from src.models.schemas import (
    Asset,
    Location,
    MeetingParticipant,
    MeetingScheduleRequest,
    PortfolioRequest,
    RouteRequest,
)
from src.quantum.market_data import DEFAULT_RETURNS, DEFAULT_VOLATILITY

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_SYMBOLS: set[str] = set(DEFAULT_RETURNS.keys()) | set(DEFAULT_VOLATILITY.keys())

DAY_ALIASES: dict[str, str] = {
    "monday": "Mon", "mon": "Mon",
    "tuesday": "Tue", "tue": "Tue",
    "wednesday": "Wed", "wed": "Wed",
    "thursday": "Thu", "thu": "Thu",
    "friday": "Fri", "fri": "Fri",
    "saturday": "Sat", "sat": "Sat",
    "sunday": "Sun", "sun": "Sun",
}

DAY_ORDER = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}

# Rough bounding boxes for major land masses — used for basic ocean check.
# A coordinate is considered "likely ocean" if it falls outside ALL of these
# generous rectangles.
_LAND_BOXES: list[tuple[float, float, float, float]] = [
    # (lat_min, lat_max, lon_min, lon_max)
    (-56, 84, -180, -30),     # Americas
    (10, 72, -30, 60),        # Europe / Africa (west)
    (-37, 38, 10, 60),        # Africa (east)
    (1, 75, 60, 180),         # Asia
    (-48, -10, 110, 180),     # Australia / NZ
    (-48, -10, 100, 180),     # Oceania (broader)
    (60, 84, -180, 180),      # Arctic land masses
    (-90, -60, -180, 180),    # Antarctica
    (-10, 30, 90, 130),       # Southeast Asia
]


class ValidationError(Exception):
    """Raised when input validation fails with a fatal error."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# ===================================================================
# Portfolio validation & preprocessing
# ===================================================================


def _is_likely_ocean(lat: float, lon: float) -> bool:
    """Return True if the coordinate doesn't fall within any known land box."""
    for lat_min, lat_max, lon_min, lon_max in _LAND_BOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return False
    return True


def validate_and_preprocess_portfolio(
    request: PortfolioRequest,
) -> tuple[PortfolioRequest, list[str]]:
    """Validate and preprocess a portfolio optimization request.

    Returns:
        A tuple of (cleaned request, list of warning strings).

    Raises:
        ValidationError: On fatal validation issues that prevent computation.
    """
    warnings: list[str] = []
    request = request.model_copy(deep=True)

    # --- Normalize symbols to uppercase ----------------------------------
    for asset in request.assets:
        asset.symbol = asset.symbol.strip().upper()

    symbols = [a.symbol for a in request.assets]

    # --- Check for duplicate symbols -------------------------------------
    seen: set[str] = set()
    unique_assets: list[Asset] = []
    for asset in request.assets:
        if asset.symbol in seen:
            warnings.append(
                f"Duplicate asset '{asset.symbol}' removed. Only the first occurrence is kept."
            )
        else:
            seen.add(asset.symbol)
            unique_assets.append(asset)
    request.assets = unique_assets
    symbols = [a.symbol for a in request.assets]

    if len(request.assets) < 2:
        raise ValidationError(
            "At least 2 unique assets are required after deduplication."
        )

    # --- Validate / warn on unrecognized symbols -------------------------
    for asset in request.assets:
        if asset.symbol not in KNOWN_SYMBOLS:
            if asset.expected_return is None or asset.volatility is None:
                warnings.append(
                    f"Symbol '{asset.symbol}' is not in our default market data. "
                    f"Falling back to generic estimates (return=0.10, vol=0.30). "
                    f"For better results, provide expected_return and volatility."
                )
            else:
                warnings.append(
                    f"Symbol '{asset.symbol}' is not recognized but custom "
                    f"return/volatility values were provided."
                )

    # --- Validate expected_return range ----------------------------------
    for asset in request.assets:
        if asset.expected_return is not None:
            if asset.expected_return < -1.0:
                raise ValidationError(
                    f"Asset '{asset.symbol}' has expected_return={asset.expected_return}. "
                    f"Values below -100% (-1.0) are not realistic."
                )
            if asset.expected_return > 5.0:
                raise ValidationError(
                    f"Asset '{asset.symbol}' has expected_return={asset.expected_return}. "
                    f"Values above 500% (5.0) are not realistic."
                )
            if asset.expected_return > 2.0:
                warnings.append(
                    f"Asset '{asset.symbol}' has a very high expected_return "
                    f"({asset.expected_return:.0%}). Ensure this is intentional."
                )

    # --- Validate volatility range ---------------------------------------
    for asset in request.assets:
        if asset.volatility is not None:
            if asset.volatility < 0.01:
                raise ValidationError(
                    f"Asset '{asset.symbol}' has volatility={asset.volatility}. "
                    f"Minimum realistic volatility is 0.01 (1%)."
                )
            if asset.volatility > 5.0:
                raise ValidationError(
                    f"Asset '{asset.symbol}' has volatility={asset.volatility}. "
                    f"Maximum realistic volatility is 5.0 (500%)."
                )

    # --- Validate allocation constraints ---------------------------------
    if request.min_allocation >= request.max_allocation:
        raise ValidationError(
            f"min_allocation ({request.min_allocation}) must be strictly less than "
            f"max_allocation ({request.max_allocation})."
        )

    n_assets = len(request.assets)
    if request.min_allocation * n_assets > 1.0:
        raise ValidationError(
            f"Infeasible allocation: min_allocation ({request.min_allocation}) * "
            f"num_assets ({n_assets}) = {request.min_allocation * n_assets:.2f} > 1.0. "
            f"Cannot satisfy minimum allocation for all assets."
        )

    # --- Auto-fill missing returns / volatility --------------------------
    for asset in request.assets:
        if asset.expected_return is None:
            asset.expected_return = DEFAULT_RETURNS.get(asset.symbol, 0.10)
        if asset.volatility is None:
            asset.volatility = DEFAULT_VOLATILITY.get(asset.symbol, 0.30)

    # --- Correlation matrix positive-definiteness check ------------------
    n = len(request.assets)
    volatilities = [a.volatility for a in request.assets]  # type: ignore[arg-type]
    vols = np.array(volatilities)

    # Build the same synthetic correlation matrix the optimizer will use
    crypto = {"BTC", "ETH", "SOL", "BNB", "ADA", "DOT", "AVAX", "MATIC", "LINK", "UNI"}
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = symbols[i], symbols[j]
            if (si in crypto and sj in crypto) or (si not in crypto and sj not in crypto):
                corr[i, j] = corr[j, i] = 0.3
            else:
                corr[i, j] = corr[j, i] = 0.1
    cov = np.outer(vols, vols) * corr
    eigenvalues = np.linalg.eigvalsh(cov)
    if np.any(eigenvalues < -1e-10):
        warnings.append(
            "The synthetic covariance matrix is not positive-definite. "
            "Results may be numerically unstable."
        )

    return request, warnings


# ===================================================================
# Route validation & preprocessing
# ===================================================================

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def validate_and_preprocess_route(
    request: RouteRequest,
) -> tuple[RouteRequest, list[str]]:
    """Validate and preprocess a route optimization request.

    Returns:
        A tuple of (cleaned request, list of warning strings).

    Raises:
        ValidationError: On fatal validation issues that prevent computation.
    """
    warnings: list[str] = []
    request = request.model_copy(deep=True)
    locations = request.locations

    # --- Minimum locations -----------------------------------------------
    if len(locations) < 3:
        raise ValidationError(
            f"At least 3 locations are required, got {len(locations)}."
        )

    # --- Basic ocean check -----------------------------------------------
    for loc in locations:
        if _is_likely_ocean(loc.lat, loc.lon):
            warnings.append(
                f"Location '{loc.name}' ({loc.lat}, {loc.lon}) appears to be in "
                f"the middle of the ocean. Verify coordinates are correct."
            )

    # --- Deduplicate near-identical locations (within 100m) --------------
    deduped: list[Location] = []
    for loc in locations:
        is_dup = False
        for existing in deduped:
            dist = _haversine(loc.lat, loc.lon, existing.lat, existing.lon)
            if dist < 0.1:  # 100 meters
                warnings.append(
                    f"Location '{loc.name}' is within 100m of '{existing.name}' "
                    f"and was removed as a duplicate."
                )
                is_dup = True
                break
        if not is_dup:
            deduped.append(loc)

    if len(deduped) < 3:
        raise ValidationError(
            f"After removing near-duplicate locations, only {len(deduped)} "
            f"unique locations remain. At least 3 are required."
        )

    # --- Check for duplicate names (non-fatal) ---------------------------
    name_counts: dict[str, int] = {}
    for loc in deduped:
        name_counts[loc.name] = name_counts.get(loc.name, 0) + 1
    for name, count in name_counts.items():
        if count > 1:
            warnings.append(
                f"Location name '{name}' appears {count} times. "
                f"Consider using unique names for clarity."
            )

    # --- Validate pairwise distances -------------------------------------
    for i in range(len(deduped)):
        for j in range(i + 1, len(deduped)):
            dist = _haversine(
                deduped[i].lat, deduped[i].lon,
                deduped[j].lat, deduped[j].lon,
            )
            if dist > 20_000:
                warnings.append(
                    f"Distance between '{deduped[i].name}' and '{deduped[j].name}' "
                    f"is {dist:.0f} km (> 20,000 km). Verify coordinates."
                )

    # --- Warn if > 10 locations ------------------------------------------
    if len(deduped) > 10:
        warnings.append(
            f"Route has {len(deduped)} locations. Quantum advantage diminishes "
            f"with the simulator beyond ~10 locations; consider reducing."
        )

    # --- Sort for deterministic results ----------------------------------
    deduped.sort(key=lambda loc: (loc.lat, loc.lon, loc.name))

    request.locations = deduped
    return request, warnings


# ===================================================================
# Scheduler validation & preprocessing
# ===================================================================

_SLOT_PATTERN = re.compile(
    r"^(\w+)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$"
)


def _normalize_day(day_str: str) -> str:
    """Normalize a day name to its 3-letter abbreviation.

    Raises ValidationError if the day name is unrecognized.
    """
    key = day_str.strip().lower()
    normalized = DAY_ALIASES.get(key)
    if normalized is None:
        raise ValidationError(
            f"Unrecognized day name '{day_str}'. "
            f"Use Monday/Mon, Tuesday/Tue, etc."
        )
    return normalized


def _parse_slot_strict(slot: str) -> tuple[str, int, int, int, int]:
    """Parse a slot string strictly.

    Returns (normalized_day, start_hour, start_min, end_hour, end_min).
    Raises ValidationError on invalid format.
    """
    slot = slot.strip()
    match = _SLOT_PATTERN.match(slot)
    if not match:
        raise ValidationError(
            f"Invalid time slot format: '{slot}'. "
            f"Expected format: 'Day HH:MM-HH:MM' (e.g., 'Mon 09:00-11:00')."
        )
    day_str = match.group(1)
    day = _normalize_day(day_str)
    start_h, start_m = int(match.group(2)), int(match.group(3))
    end_h, end_m = int(match.group(4)), int(match.group(5))

    if start_h > 23 or end_h > 23 or start_m > 59 or end_m > 59:
        raise ValidationError(
            f"Invalid time in slot '{slot}'. "
            f"Hours must be 0-23 and minutes must be 0-59."
        )

    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m

    if end_total <= start_total:
        raise ValidationError(
            f"In slot '{slot}', end time must be after start time."
        )

    return day, start_h, start_m, end_h, end_m


def _slot_to_minutes(day: str, hour: int, minute: int) -> int:
    """Convert day + time to a single minutes-from-week-start value."""
    return DAY_ORDER[day] * 24 * 60 + hour * 60 + minute


def _normalize_slot_string(day: str, sh: int, sm: int, eh: int, em: int) -> str:
    """Build a canonical slot string."""
    return f"{day} {sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"


def _merge_adjacent_slots(
    slots: list[tuple[str, int, int, int, int]],
) -> list[tuple[str, int, int, int, int]]:
    """Merge adjacent or overlapping time slots on the same day."""
    if not slots:
        return []

    # Group by day
    by_day: dict[str, list[tuple[int, int, int, int]]] = {}
    for day, sh, sm, eh, em in slots:
        by_day.setdefault(day, []).append((sh, sm, eh, em))

    merged: list[tuple[str, int, int, int, int]] = []
    for day in sorted(by_day, key=lambda d: DAY_ORDER.get(d, 99)):
        intervals = sorted(by_day[day], key=lambda t: (t[0], t[1]))
        current_sh, current_sm, current_eh, current_em = intervals[0]
        for sh, sm, eh, em in intervals[1:]:
            start_mins = sh * 60 + sm
            current_end_mins = current_eh * 60 + current_em
            if start_mins <= current_end_mins:
                # Overlapping or adjacent — extend
                end_mins = eh * 60 + em
                if end_mins > current_end_mins:
                    current_eh, current_em = eh, em
            else:
                merged.append((day, current_sh, current_sm, current_eh, current_em))
                current_sh, current_sm, current_eh, current_em = sh, sm, eh, em
        merged.append((day, current_sh, current_sm, current_eh, current_em))

    return merged


def validate_and_preprocess_schedule(
    request: MeetingScheduleRequest,
) -> tuple[MeetingScheduleRequest, list[str]]:
    """Validate and preprocess a meeting schedule request.

    Returns:
        A tuple of (cleaned request, list of warning strings).

    Raises:
        ValidationError: On fatal validation issues that prevent computation.
    """
    warnings: list[str] = []
    request = request.model_copy(deep=True)

    duration_minutes = request.duration_minutes

    # --- Parse and validate every slot strictly --------------------------
    for p in request.participants:
        parsed_available: list[tuple[str, int, int, int, int]] = []
        for slot_str in p.available_slots:
            parsed = _parse_slot_strict(slot_str)
            parsed_available.append(parsed)

        # Check overlapping availability within the same participant
        sorted_slots = sorted(
            parsed_available,
            key=lambda s: _slot_to_minutes(s[0], s[1], s[2]),
        )
        for i in range(len(sorted_slots) - 1):
            s1 = sorted_slots[i]
            s2 = sorted_slots[i + 1]
            if s1[0] == s2[0]:  # same day
                end1 = s1[3] * 60 + s1[4]
                start2 = s2[1] * 60 + s2[2]
                if end1 > start2:
                    warnings.append(
                        f"Participant '{p.name}' has overlapping availability: "
                        f"'{_normalize_slot_string(*s1)}' and "
                        f"'{_normalize_slot_string(*s2)}'."
                    )

        # Check that the meeting duration fits within at least one slot
        has_fitting_slot = False
        for day, sh, sm, eh, em in parsed_available:
            slot_duration = (eh * 60 + em) - (sh * 60 + sm)
            if slot_duration >= duration_minutes:
                has_fitting_slot = True
                break
        if not has_fitting_slot and parsed_available:
            warnings.append(
                f"Participant '{p.name}' has no available slot long enough "
                f"for a {duration_minutes}-minute meeting."
            )

        # Merge adjacent slots
        merged = _merge_adjacent_slots(parsed_available)

        # Normalize day names and rebuild slot strings
        p.available_slots = [
            _normalize_slot_string(day, sh, sm, eh, em)
            for day, sh, sm, eh, em in merged
        ]

        # --- Validate preferences are subset of available_slots ----------
        if p.preferences:
            parsed_prefs: list[tuple[str, int, int, int, int]] = []
            available_set = set(p.available_slots)
            normalized_prefs: list[str] = []
            for pref_str in p.preferences:
                parsed_pref = _parse_slot_strict(pref_str)
                norm = _normalize_slot_string(*parsed_pref)
                # Check if pref falls within any available slot
                pref_start = _slot_to_minutes(parsed_pref[0], parsed_pref[1], parsed_pref[2])
                pref_end = _slot_to_minutes(parsed_pref[0], parsed_pref[3], parsed_pref[4])
                is_covered = False
                for avail in merged:
                    avail_start = _slot_to_minutes(avail[0], avail[1], avail[2])
                    avail_end = _slot_to_minutes(avail[0], avail[3], avail[4])
                    if pref_start >= avail_start and pref_end <= avail_end:
                        is_covered = True
                        break
                if not is_covered:
                    warnings.append(
                        f"Participant '{p.name}' preference '{norm}' is not "
                        f"within their available slots and was removed."
                    )
                else:
                    normalized_prefs.append(norm)
            p.preferences = normalized_prefs

    # --- Remove past slots (best-effort, based on day of week) -----------
    # We use the current weekday to filter out days that have already passed
    # this week. This is a heuristic — we cannot know the exact target week.
    today_weekday = datetime.now().weekday()  # 0=Monday .. 6=Sunday
    for p in request.participants:
        future_slots: list[str] = []
        for slot_str in p.available_slots:
            parsed = _parse_slot_strict(slot_str)
            day_idx = DAY_ORDER.get(parsed[0], 99)
            if day_idx >= today_weekday:
                future_slots.append(slot_str)
            else:
                warnings.append(
                    f"Participant '{p.name}' slot '{slot_str}' appears to be "
                    f"in the past for this week and was removed."
                )
        if future_slots:
            p.available_slots = future_slots
        # If all slots are in the past, keep them to avoid empty schedule

    # --- Check at least 2 participants share an overlapping hour ---------
    # Build a map of participant -> set of (day, hour) pairs
    participant_hours: dict[str, set[tuple[str, int]]] = {}
    for p in request.participants:
        hours: set[tuple[str, int]] = set()
        for slot_str in p.available_slots:
            parsed = _parse_slot_strict(slot_str)
            day, sh, sm, eh, em = parsed
            for h in range(sh, eh):
                hours.add((day, h))
            # If end has minutes, include that hour too
            if em > 0:
                hours.add((day, eh))
        participant_hours[p.name] = hours

    # Check pairwise overlaps
    names = list(participant_hours.keys())
    has_overlap = False
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if participant_hours[names[i]] & participant_hours[names[j]]:
                has_overlap = True
                break
        if has_overlap:
            break

    if not has_overlap:
        warnings.append(
            "No two participants share any overlapping availability. "
            "The scheduler may not find a satisfactory meeting time."
        )

    return request, warnings
