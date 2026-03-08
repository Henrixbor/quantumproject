"""Security middleware stack for Quantum MCP Relayer.

Layers (applied bottom-up by Starlette / FastAPI):

1. **SecurityHeadersMiddleware** -- adds defensive HTTP headers on every
   response (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security,
   Referrer-Policy, Permissions-Policy, Cache-Control for API responses).

2. **RequestLoggingMiddleware** -- structured request/response logging via
   ``structlog``.  Logs method, path, status, and latency.  Sensitive headers
   (Authorization, X-API-Key) are never logged.

3. **APIKeyMiddleware** -- validates the ``X-API-Key`` header, resolves the
   caller's tier, and enforces the sliding-window rate limit.  Unauthenticated
   callers receive 401; rate-limited callers receive 429 with Retry-After.

CORS is configured in this module's ``attach_middleware`` helper so that
``app.py`` only needs a single call site.
"""

from __future__ import annotations

import time
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

import jwt as pyjwt

from src.api.auth import Tier, key_store
from src.api.rate_limit import limiter
from src.config import get_settings

logger = structlog.get_logger("qmr.middleware")

# Paths that do not require an API key.
_PUBLIC_PATHS: frozenset[str] = frozenset({
    "/health", "/docs", "/redoc", "/openapi.json",
    "/api/v1/waitlist",
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/me",
    "/api/v1/auth/regenerate-key",
    "/api/v1/billing/webhook",
    "/api/v1/billing/create-checkout",
    "/api/v1/billing/portal",
})

# Path prefixes that do not require an API key (static assets, etc.)
_PUBLIC_PREFIXES: tuple[str, ...] = ("/static/", "/css/", "/js/", "/img/")

# ---------------------------------------------------------------------------
# 1. Security headers
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects hardened security headers on every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cache-Control"] = "no-store"
        # HSTS -- only meaningful when served over TLS, but safe to set always.
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        return response


# ---------------------------------------------------------------------------
# 2. Structured request logging
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, and latency."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            status = response.status_code if response else 500
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=status,
                latency_ms=elapsed_ms,
                client=request.client.host if request.client else "unknown",
            )


# ---------------------------------------------------------------------------
# 3. API key authentication + rate limiting
# ---------------------------------------------------------------------------

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key and enforces per-tier rate limits.

    Public paths (health check, docs) are exempt.  On failure the middleware
    short-circuits with a JSON error body -- requests never reach the route
    handler.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Let public / preflight / static asset requests through.
        path = request.url.path
        if (
            path in _PUBLIC_PATHS
            or path.startswith(_PUBLIC_PREFIXES)
            or request.method == "OPTIONS"
            or not path.startswith("/api/")
        ):
            return await call_next(request)

        # --- Authentication ------------------------------------------------
        # Accept either X-API-Key or Authorization: Bearer <jwt>
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization", "")
        record = None
        rate_key: str | None = None  # identifier for rate-limit bucket

        if api_key:
            record = key_store.validate_key(api_key)
            if record is None:
                logger.warning("auth_failure", path=request.url.path)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key."},
                )
            rate_key = record.key_hash
        elif auth_header.startswith("Bearer "):
            token = auth_header[7:]
            settings = get_settings()
            try:
                payload = pyjwt.decode(
                    token, settings.jwt_secret, algorithms=["HS256"]
                )
                user_id: str = payload["sub"]
            except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired JWT token."},
                )
            # Resolve user → API key record so we can rate-limit by user
            from src.models.user import user_store

            user = user_store.get_by_id(user_id)
            if user is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "User not found."},
                )
            record = key_store._records.get(user.api_key_hash)
            if record is None:
                # Fallback: build a synthetic record for rate limiting
                from src.api.auth import APIKeyRecord
                record = APIKeyRecord(
                    key_hash=user.api_key_hash,
                    tier=user.tier,
                    owner=user.id,
                )
            rate_key = user.api_key_hash
            # Track usage per user
            user_store.increment_usage(user.id)
        else:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header or Authorization Bearer token."},
            )

        # --- Rate limiting -------------------------------------------------
        result = limiter.check(rate_key, record.tier)
        if not result.allowed:
            retry_after = max(1, int(result.reset_at - time.time()))
            logger.warning(
                "rate_limit_exceeded",
                tier=record.tier.value,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Upgrade your plan or wait."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_at)),
                },
            )

        # Attach rate-limit info to the response.
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_at))
        return response


# ---------------------------------------------------------------------------
# Helper: wire everything up in one call
# ---------------------------------------------------------------------------

def attach_middleware(app: FastAPI) -> None:
    """Register all security middleware on *app*.

    Call this from ``app.py`` **instead of** manually adding CORSMiddleware.
    Middleware is added in reverse order because Starlette processes the
    outermost middleware first.
    """
    settings = get_settings()

    # -- CORS ---------------------------------------------------------------
    # In production, restrict origins to the actual front-end domain(s).
    if settings.environment == "production":
        allowed_origins = [
            "https://quantumrelayer.com",
            "https://app.quantumrelayer.com",
        ]
    else:
        # Development / staging: allow localhost variants.
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type", "Authorization"],
        expose_headers=[
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
        max_age=600,  # preflight cache: 10 minutes
    )

    # Outermost first  ->  SecurityHeaders  ->  Logging  ->  APIKey  ->  route
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
