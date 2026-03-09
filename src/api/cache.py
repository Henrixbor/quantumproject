"""LRU cache with TTL for quantum computation results.

Provides a simple in-memory cache that stores computation results
keyed by request hash. Entries expire after a configurable TTL
(default 60 seconds). Uses an OrderedDict for LRU eviction.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """Single cache entry with value and expiration timestamp."""
    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe LRU cache with time-to-live expiration.

    Args:
        max_size: Maximum number of entries. Oldest evicted first.
        ttl_seconds: Time-to-live in seconds for each entry.
    """

    def __init__(self, max_size: int = 128, ttl_seconds: float = 60.0):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _make_key(request_obj: Any) -> str:
        """Create a stable hash key from a Pydantic model or dict.

        Serializes the request to sorted JSON and hashes it with SHA-256
        for a compact, collision-resistant key.
        """
        if hasattr(request_obj, "model_dump"):
            data = request_obj.model_dump()
        elif hasattr(request_obj, "dict"):
            data = request_obj.dict()
        else:
            data = request_obj

        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get(self, request_obj: Any) -> Any | None:
        """Look up a cached result. Returns None on miss or expiration."""
        key = self._make_key(request_obj)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            if time.monotonic() > entry.expires_at:
                # Expired -- remove and return miss
                del self._store[key]
                return None

            # Move to end (most recently used)
            self._store.move_to_end(key)
            return entry.value

    def put(self, request_obj: Any, value: Any) -> None:
        """Store a result in the cache."""
        key = self._make_key(request_obj)
        now = time.monotonic()

        with self._lock:
            if key in self._store:
                # Update existing
                self._store[key] = CacheEntry(value=value, expires_at=now + self._ttl)
                self._store.move_to_end(key)
            else:
                # Evict oldest if at capacity
                while len(self._store) >= self._max_size:
                    self._store.popitem(last=False)
                self._store[key] = CacheEntry(value=value, expires_at=now + self._ttl)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Current number of entries (including expired but not yet evicted)."""
        return len(self._store)


# Shared cache instances for each endpoint
portfolio_cache = TTLCache(max_size=64, ttl_seconds=60.0)
route_cache = TTLCache(max_size=64, ttl_seconds=60.0)
schedule_cache = TTLCache(max_size=64, ttl_seconds=60.0)
