from __future__ import annotations

from pydantic import BaseModel, Field


# --- Portfolio Optimizer ---

class Asset(BaseModel):
    symbol: str = Field(description="Asset ticker symbol, e.g. BTC, ETH, AAPL")
    expected_return: float | None = Field(
        default=None, description="Expected annual return (0.0-1.0). Auto-fetched if omitted."
    )
    volatility: float | None = Field(
        default=None, description="Annual volatility (0.0-1.0). Auto-fetched if omitted."
    )


class PortfolioRequest(BaseModel):
    assets: list[Asset] = Field(min_length=2, max_length=20, description="Assets to optimize")
    risk_tolerance: float = Field(
        default=0.5, ge=0.0, le=1.0, description="0=conservative, 1=aggressive"
    )
    min_allocation: float = Field(
        default=0.05, ge=0.0, le=0.5, description="Minimum allocation per asset"
    )
    max_allocation: float = Field(
        default=0.80, ge=0.1, le=1.0, description="Maximum allocation per asset"
    )


class PortfolioResult(BaseModel):
    allocations: dict[str, float] = Field(description="Optimal allocation per asset (sums to 1.0)")
    expected_return: float = Field(description="Portfolio expected annual return")
    volatility: float = Field(description="Portfolio annual volatility")
    sharpe_ratio: float = Field(description="Risk-adjusted return metric")
    method: str = Field(description="Optimization method used")
    qubit_count: int = Field(description="Number of qubits used")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal validation warnings")


# --- Route Optimizer (TSP) ---

class Location(BaseModel):
    name: str = Field(description="Location name or address")
    lat: float = Field(ge=-90, le=90, description="Latitude")
    lon: float = Field(ge=-180, le=180, description="Longitude")


class RouteRequest(BaseModel):
    locations: list[Location] = Field(
        min_length=3, max_length=15, description="Locations to visit"
    )
    return_to_start: bool = Field(default=True, description="Return to starting location")


class RouteResult(BaseModel):
    route: list[str] = Field(description="Ordered list of location names")
    total_distance_km: float = Field(description="Total route distance in km")
    improvement_vs_naive: float = Field(
        description="Percentage improvement vs sequential ordering"
    )
    method: str
    qubit_count: int
    warnings: list[str] = Field(default_factory=list, description="Non-fatal validation warnings")


# --- Meeting Scheduler ---

class MeetingParticipant(BaseModel):
    name: str = Field(description="Participant name")
    available_slots: list[str] = Field(
        description="Available time slots, e.g. ['Mon 9:00-11:00', 'Tue 14:00-16:00']"
    )
    priority: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Priority weight (higher = more important)"
    )
    preferences: list[str] = Field(
        default_factory=list,
        description="Preferred slots (subset of available_slots)",
    )


class MeetingScheduleRequest(BaseModel):
    participants: list[MeetingParticipant] = Field(
        min_length=2, max_length=20, description="Meeting participants"
    )
    duration_minutes: int = Field(default=60, ge=15, le=480, description="Meeting duration")
    num_meetings: int = Field(default=1, ge=1, le=10, description="Number of meetings to schedule")


class MeetingScheduleResult(BaseModel):
    scheduled_slots: list[str] = Field(description="Optimal meeting time slots")
    attendance: dict[str, list[str]] = Field(
        description="Who attends each slot"
    )
    satisfaction_score: float = Field(
        ge=0.0, le=1.0, description="Overall satisfaction (0-1)"
    )
    method: str
    qubit_count: int
    warnings: list[str] = Field(default_factory=list, description="Non-fatal validation warnings")


# --- Auth & Billing Schemas ------------------------------------------------

class SignupRequest(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (min 8 characters)")


class SignupResponse(BaseModel):
    id: str
    email: str
    api_key: str = Field(description="Your API key — shown only once, store it securely")
    tier: str
    message: str = "Account created. Save your API key — it will not be shown again."


class LoginRequest(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(description="Account password")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")


class UserProfile(BaseModel):
    id: str
    email: str
    tier: str
    usage_count: int
    api_key_hint: str = Field(description="Masked API key (last 8 chars visible)")
    stripe_customer_id: str = ""
    created_at: float


class CheckoutRequest(BaseModel):
    tier: str = Field(description="Target tier: starter, pro, or business")
