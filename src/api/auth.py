"""API key management for Quantum MCP Relayer.

Handles generation, hashing, validation, and tier detection for API keys.
Keys use the prefix ``qmr_`` followed by 48 hex characters (192-bit entropy).
Only the SHA-256 hash of the key (salted via config) is stored -- the raw key
is returned exactly once at creation time and never persisted.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.config import get_settings

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

class Tier(str, Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    business = "business"


@dataclass(frozen=True)
class APIKeyRecord:
    """Metadata stored alongside the hashed key."""
    key_hash: str
    tier: Tier
    owner: str  # opaque identifier for the key holder


# ---------------------------------------------------------------------------
# In-memory store (MVP) -- swap for Redis / DB in production
# ---------------------------------------------------------------------------

@dataclass
class APIKeyStore:
    """Dict-backed key store keyed by the SHA-256 hash of the API key."""

    _records: dict[str, APIKeyRecord] = field(default_factory=dict)

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """Produce a salted SHA-256 hex digest of *raw_key*."""
        salt = get_settings().api_key_salt
        return hashlib.sha256(f"{salt}:{raw_key}".encode()).hexdigest()

    # -- public API ----------------------------------------------------------

    def generate_key(self, owner: str, tier: Tier = Tier.free) -> str:
        """Create a new API key, store its hash, and return the raw key.

        The raw key is the **only** time the caller can see the plaintext.
        """
        raw_key = f"qmr_{secrets.token_hex(24)}"  # 48 hex chars = 192 bits
        key_hash = self._hash_key(raw_key)
        record = APIKeyRecord(key_hash=key_hash, tier=tier, owner=owner)
        self._records[key_hash] = record
        return raw_key

    def validate_key(self, raw_key: str) -> Optional[APIKeyRecord]:
        """Return the record if the key is valid, else ``None``."""
        if not raw_key or not raw_key.startswith("qmr_"):
            return None
        key_hash = self._hash_key(raw_key)
        return self._records.get(key_hash)

    def revoke_key(self, raw_key: str) -> bool:
        """Revoke a key. Returns ``True`` if it existed."""
        key_hash = self._hash_key(raw_key)
        return self._records.pop(key_hash, None) is not None

    def get_tier(self, raw_key: str) -> Optional[Tier]:
        """Return the tier for *raw_key*, or ``None`` if invalid."""
        record = self.validate_key(raw_key)
        return record.tier if record else None


# ---------------------------------------------------------------------------
# Module-level singleton -- import and use directly
# ---------------------------------------------------------------------------

key_store = APIKeyStore()
