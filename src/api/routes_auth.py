"""Authentication endpoints for Quantum MCP Relayer.

Provides signup, login (JWT), profile retrieval, and API-key regeneration.
All JWT tokens are signed with HS256 using the configured ``jwt_secret``.
"""

from __future__ import annotations

import time
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Header

from src.config import get_settings
from src.models.schemas import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    UserProfile,
)
from src.models.user import User, user_store

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"


def _create_token(user_id: str) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)``."""
    settings = get_settings()
    expires_in = settings.jwt_expiry_hours * 3600
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)
    return token, expires_in


def _decode_token(token: str) -> str:
    """Return the ``sub`` (user id) or raise 401."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        user_id: str = payload["sub"]
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


def _get_current_user(authorization: Annotated[str, Header()]) -> User:
    """FastAPI dependency: extract and validate JWT from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'.")
    token = authorization[7:]
    user_id = _decode_token(token)
    user = user_store.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signup", response_model=SignupResponse)
async def signup(body: SignupRequest) -> SignupResponse:
    """Create a new account and return a one-time API key."""
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid email address.")

    try:
        user, raw_api_key = user_store.create_user(email, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return SignupResponse(
        id=user.id,
        email=user.email,
        api_key=raw_api_key,
        tier=user.tier.value,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate with email + password and receive a JWT."""
    user = user_store.verify_password(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token, expires_in = _create_token(user.id)
    return LoginResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(_get_current_user)) -> UserProfile:
    """Return the authenticated user's profile."""
    # Mask the API key — show only the last 8 chars
    # We cannot recover the raw key from the hash, so we store a hint.
    # The hint is derived from the hash itself (safe to expose a fragment).
    api_key_hint = f"qmr_...{user.api_key_hash[-8:]}"

    return UserProfile(
        id=user.id,
        email=user.email,
        tier=user.tier.value,
        usage_count=user.usage_count,
        api_key_hint=api_key_hint,
        stripe_customer_id=user.stripe_customer_id,
        created_at=user.created_at,
    )


@router.post("/regenerate-key")
async def regenerate_key(user: User = Depends(_get_current_user)) -> dict:
    """Invalidate the current API key and issue a new one (shown once)."""
    raw_key = user_store.regenerate_api_key(user.id)
    return {
        "api_key": raw_key,
        "message": "New API key generated. The old key is now invalid. Save this — it will not be shown again.",
    }
