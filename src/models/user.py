"""User model and in-memory storage for Quantum MCP Relayer.

Provides user account management with secure password hashing and API key
binding.  The in-memory dict store is designed to be trivially replaceable
with PostgreSQL / Redis in production — every mutation goes through a
well-defined method boundary.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from src.api.auth import Tier, key_store
from src.config import get_settings

# ---------------------------------------------------------------------------
# Password hashing — PBKDF2-HMAC-SHA256 (stdlib, zero dependencies)
# ---------------------------------------------------------------------------

_HASH_ITERATIONS = 260_000  # OWASP 2023 recommendation for PBKDF2-SHA256


def _hash_password(password: str) -> str:
    """Return ``salt$hash`` using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _HASH_ITERATIONS
    )
    return f"{salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify *password* against a ``salt$hash`` string."""
    salt, expected_hex = stored.split("$", 1)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _HASH_ITERATIONS
    )
    return secrets.compare_digest(dk.hex(), expected_hex)


# ---------------------------------------------------------------------------
# User dataclass
# ---------------------------------------------------------------------------

@dataclass
class User:
    id: str
    email: str
    password_hash: str
    api_key_hash: str  # SHA-256 hash of the user's current API key
    tier: Tier = Tier.free
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    stripe_customer_id: str = ""


# ---------------------------------------------------------------------------
# In-memory user store (MVP) — swap for DB in production
# ---------------------------------------------------------------------------

class UserStore:
    """Dict-backed user store keyed by user id, with secondary indexes on
    email and API-key hash for O(1) lookups."""

    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, str] = {}        # email  -> user.id
        self._by_api_key: dict[str, str] = {}       # key_hash -> user.id

    # -- mutations -----------------------------------------------------------

    def create_user(self, email: str, password: str) -> tuple[User, str]:
        """Create a new user with a freshly generated API key.

        Returns ``(user, raw_api_key)`` — the raw key is shown **once**.

        Raises ``ValueError`` if the email is already registered.
        """
        email = email.strip().lower()
        if email in self._by_email:
            raise ValueError("Email already registered")

        user_id = secrets.token_urlsafe(16)
        password_hash = _hash_password(password)

        # Generate API key via the existing key_store singleton
        raw_api_key = key_store.generate_key(owner=user_id, tier=Tier.free)
        api_key_hash = key_store._hash_key(raw_api_key)

        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            api_key_hash=api_key_hash,
        )

        self._by_id[user.id] = user
        self._by_email[user.email] = user.id
        self._by_api_key[api_key_hash] = user.id

        return user, raw_api_key

    def regenerate_api_key(self, user_id: str) -> str:
        """Revoke the old API key and issue a new one.

        Returns the new raw API key (shown once).
        """
        user = self._by_id.get(user_id)
        if user is None:
            raise ValueError("User not found")

        # Remove old key from indexes
        self._by_api_key.pop(user.api_key_hash, None)
        # Revoke in the key_store (we only have the hash, so remove by hash)
        key_store._records.pop(user.api_key_hash, None)

        # Generate new key
        raw_api_key = key_store.generate_key(owner=user_id, tier=user.tier)
        api_key_hash = key_store._hash_key(raw_api_key)

        user.api_key_hash = api_key_hash
        self._by_api_key[api_key_hash] = user.id

        return raw_api_key

    def update_tier(self, user_id: str, tier: Tier) -> None:
        """Upgrade / change a user's subscription tier."""
        user = self._by_id.get(user_id)
        if user is None:
            raise ValueError("User not found")
        user.tier = tier
        # Also update the API key record in key_store so rate limits match
        record = key_store._records.get(user.api_key_hash)
        if record is not None:
            from src.api.auth import APIKeyRecord
            key_store._records[user.api_key_hash] = APIKeyRecord(
                key_hash=record.key_hash, tier=tier, owner=record.owner
            )

    def set_stripe_customer_id(self, user_id: str, customer_id: str) -> None:
        user = self._by_id.get(user_id)
        if user is None:
            raise ValueError("User not found")
        user.stripe_customer_id = customer_id

    def increment_usage(self, user_id: str) -> int:
        """Increment usage counter and return the new count."""
        user = self._by_id.get(user_id)
        if user is None:
            raise ValueError("User not found")
        user.usage_count += 1
        return user.usage_count

    # -- queries -------------------------------------------------------------

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        uid = self._by_email.get(email.strip().lower())
        return self._by_id.get(uid) if uid else None

    def get_by_api_key_hash(self, api_key_hash: str) -> Optional[User]:
        uid = self._by_api_key.get(api_key_hash)
        return self._by_id.get(uid) if uid else None

    def get_by_stripe_customer(self, customer_id: str) -> Optional[User]:
        for user in self._by_id.values():
            if user.stripe_customer_id == customer_id:
                return user
        return None

    def verify_password(self, email: str, password: str) -> Optional[User]:
        """Return the user if credentials are valid, else ``None``."""
        user = self.get_by_email(email)
        if user is None:
            return None
        if _verify_password(password, user.password_hash):
            return user
        return None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

user_store = UserStore()
