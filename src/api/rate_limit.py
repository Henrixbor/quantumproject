"""Sliding-window rate limiter for Quantum MCP Relayer.

Uses an in-memory dict of per-key timestamp lists for the MVP.  The design
is intentionally Redis-ready: replace ``SlidingWindowLimiter`` with a
Redis Sorted-Set implementation and the rest of the stack stays unchanged.

Limits are calendar-month windows expressed as *requests per 30-day rolling
window* so that users never hit a cliff at month boundaries.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.api.auth import Tier
from src.config import get_settings

# 30 days in seconds -- rolling window size
_WINDOW_SECONDS: int = 30 * 24 * 60 * 60


def _tier_limit(tier: Tier) -> int:
    """Look up the configured request cap for *tier*."""
    settings = get_settings()
    return {
        Tier.free: settings.rate_limit_free,
        Tier.starter: settings.rate_limit_starter,
        Tier.pro: settings.rate_limit_pro,
        Tier.business: settings.rate_limit_business,
    }[tier]


# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # epoch timestamp when the oldest request falls off


# ---------------------------------------------------------------------------
# Sliding-window limiter (in-memory MVP)
# ---------------------------------------------------------------------------

@dataclass
class SlidingWindowLimiter:
    """Per-key sliding-window rate limiter backed by a plain dict.

    Each key maps to a sorted list of request timestamps.  On every check
    we prune entries older than the window, then decide allow / deny.
    """

    _buckets: dict[str, list[float]] = field(default_factory=dict)

    def _prune(self, key: str, now: float) -> list[float]:
        """Remove timestamps outside the current window and return the list."""
        cutoff = now - _WINDOW_SECONDS
        timestamps = self._buckets.get(key, [])
        # Binary search would be faster, but list sizes are bounded by the
        # per-tier cap so a simple filter is fine for the MVP.
        pruned = [ts for ts in timestamps if ts > cutoff]
        self._buckets[key] = pruned
        return pruned

    def check(self, key_hash: str, tier: Tier) -> RateLimitResult:
        """Check (and record) a request against the rate limit.

        Parameters
        ----------
        key_hash:
            The SHA-256 hash of the API key -- used as the bucket key so
            that raw secrets never sit in memory longer than necessary.
        tier:
            The caller's subscription tier, used to look up the cap.

        Returns
        -------
        RateLimitResult
            Contains ``allowed=False`` when the caller has exhausted their
            quota for the current window.
        """
        now = time.time()
        limit = _tier_limit(tier)
        timestamps = self._prune(key_hash, now)
        remaining = max(0, limit - len(timestamps))

        # Compute when the oldest request will fall off the window.
        reset_at = (timestamps[0] + _WINDOW_SECONDS) if timestamps else (now + _WINDOW_SECONDS)

        if len(timestamps) >= limit:
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
            )

        # Record this request
        timestamps.append(now)
        self._buckets[key_hash] = timestamps

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining - 1,  # we just consumed one
            reset_at=reset_at,
        )

    def reset(self, key_hash: str) -> None:
        """Clear all recorded requests for a key (useful in tests)."""
        self._buckets.pop(key_hash, None)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

limiter = SlidingWindowLimiter()
