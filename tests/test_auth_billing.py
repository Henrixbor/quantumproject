"""Tests for authentication flows, billing webhooks, and rate limiting.

Covers critical paths that were previously untested:
- Signup with invalid/duplicate emails
- Login and JWT token lifecycle
- API key regeneration
- Billing webhook processing (tier upgrades)
- Rate limiter edge cases
- Waitlist email validation
"""

from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import APIKeyRecord, Tier, key_store
from src.api.rate_limit import SlidingWindowLimiter
from src.models.user import user_store


client = TestClient(app)


# ---------------------------------------------------------------------------
# Auth: Signup
# ---------------------------------------------------------------------------


class TestSignup:
    def test_signup_success(self):
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "test-auth-1@example.com", "password": "SecurePass123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test-auth-1@example.com"
        assert data["api_key"].startswith("qmr_")
        assert data["tier"] == "free"
        assert "id" in data

    def test_signup_duplicate_email(self):
        client.post(
            "/api/v1/auth/signup",
            json={"email": "dup-test@example.com", "password": "SecurePass123!"},
        )
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "dup-test@example.com", "password": "DifferentPass456!"},
        )
        assert resp.status_code == 409

    def test_signup_invalid_email_no_domain(self):
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "nodomain@", "password": "SecurePass123!"},
        )
        assert resp.status_code == 422

    def test_signup_invalid_email_no_tld(self):
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "user@domain", "password": "SecurePass123!"},
        )
        assert resp.status_code == 422

    def test_signup_invalid_email_just_at(self):
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "@", "password": "SecurePass123!"},
        )
        assert resp.status_code == 422

    def test_signup_short_password(self):
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "short-pass@example.com", "password": "short"},
        )
        assert resp.status_code == 422  # Pydantic min_length=8


# ---------------------------------------------------------------------------
# Auth: Login + JWT
# ---------------------------------------------------------------------------


class TestLogin:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.email = f"login-test-{id(self)}@example.com"
        self.password = "TestPassword123!"
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": self.email, "password": self.password},
        )
        self.api_key = resp.json()["api_key"]

    def test_login_success(self):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "Whatever123!"},
        )
        assert resp.status_code == 401

    def test_me_with_jwt(self):
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
        )
        token = login_resp.json()["access_token"]

        me_resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["email"] == self.email
        assert data["tier"] == "free"
        assert "api_key_hint" in data

    def test_me_without_auth(self):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 422)  # missing header

    def test_me_with_invalid_jwt(self):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auth: API Key Regeneration
# ---------------------------------------------------------------------------


class TestRegenerateKey:
    def test_regenerate_key(self):
        # Sign up
        signup_resp = client.post(
            "/api/v1/auth/signup",
            json={"email": f"regen-{id(self)}@example.com", "password": "TestPass123!"},
        )
        old_key = signup_resp.json()["api_key"]

        # Login to get JWT
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": f"regen-{id(self)}@example.com", "password": "TestPass123!"},
        )
        token = login_resp.json()["access_token"]

        # Regenerate
        regen_resp = client.post(
            "/api/v1/auth/regenerate-key",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert regen_resp.status_code == 200
        data = regen_resp.json()
        assert "api_key" in data
        new_key = data["api_key"]
        assert new_key.startswith("qmr_")
        assert new_key != old_key

        # Old key should no longer work for API calls
        old_record = key_store.validate_key(old_key)
        assert old_record is None

        # New key should work
        new_record = key_store.validate_key(new_key)
        assert new_record is not None


# ---------------------------------------------------------------------------
# Billing: Webhook
# ---------------------------------------------------------------------------


class TestBillingWebhook:
    def test_webhook_checkout_completed(self):
        # Create a user first
        signup_resp = client.post(
            "/api/v1/auth/signup",
            json={"email": f"webhook-{id(self)}@example.com", "password": "TestPass123!"},
        )
        user_id = signup_resp.json()["id"]

        # Simulate Stripe webhook (dev mode, no signature verification)
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "metadata": {
                        "user_id": user_id,
                        "tier": "pro",
                    },
                    "customer": "cus_test_456",
                },
            },
        }
        resp = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

        # Verify user tier was upgraded
        user = user_store.get_by_id(user_id)
        assert user is not None
        assert user.tier == Tier.pro
        assert user.stripe_customer_id == "cus_test_456"

    def test_webhook_missing_metadata(self):
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_no_meta",
                    "metadata": {},
                },
            },
        }
        resp = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
        )
        # Should still return 200 (webhook acknowledged) but log a warning
        assert resp.status_code == 200

    def test_webhook_unknown_event_type(self):
        event = {
            "type": "customer.subscription.updated",
            "data": {"object": {}},
        }
        resp = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    def test_webhook_invalid_tier(self):
        signup_resp = client.post(
            "/api/v1/auth/signup",
            json={"email": f"webhook-bad-tier-{id(self)}@example.com", "password": "TestPass123!"},
        )
        user_id = signup_resp.json()["id"]

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_bad_tier",
                    "metadata": {
                        "user_id": user_id,
                        "tier": "nonexistent_tier",
                    },
                },
            },
        }
        resp = client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200  # Acknowledged but tier not changed

        user = user_store.get_by_id(user_id)
        assert user.tier == Tier.free  # unchanged


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_basic_rate_limit(self):
        limiter = SlidingWindowLimiter()
        # With limit of 10 for free tier, first 10 should pass
        for i in range(10):
            result = limiter.check("test-key-1", Tier.free)
            assert result.allowed, f"Request {i+1} should be allowed"

        # 11th should be denied
        result = limiter.check("test-key-1", Tier.free)
        assert not result.allowed
        assert result.remaining == 0

    def test_rate_limit_remaining_count(self):
        limiter = SlidingWindowLimiter()
        result = limiter.check("test-key-2", Tier.free)
        assert result.allowed
        assert result.remaining == 9  # 10 limit - 1 used = 9 remaining

    def test_rate_limit_reset(self):
        limiter = SlidingWindowLimiter()
        limiter.check("test-key-3", Tier.free)
        limiter.reset("test-key-3")
        result = limiter.check("test-key-3", Tier.free)
        assert result.allowed
        assert result.remaining == 9  # fresh start

    def test_rate_limit_reset_at(self):
        limiter = SlidingWindowLimiter()
        result = limiter.check("test-key-4", Tier.free)
        assert result.reset_at > time.time()  # should be in the future


# ---------------------------------------------------------------------------
# Waitlist email validation
# ---------------------------------------------------------------------------


class TestWaitlist:
    def test_waitlist_valid_email(self):
        resp = client.post(
            "/api/v1/waitlist",
            json={"email": "valid-waitlist@example.com"},
        )
        assert resp.status_code == 200

    def test_waitlist_duplicate_email(self):
        email = "waitlist-dup@example.com"
        client.post("/api/v1/waitlist", json={"email": email})
        resp = client.post("/api/v1/waitlist", json={"email": email})
        assert resp.status_code == 200
        assert "already" in resp.json()["message"].lower()

    def test_waitlist_invalid_email_no_tld(self):
        resp = client.post(
            "/api/v1/waitlist",
            json={"email": "invalid@nodomain"},
        )
        assert resp.status_code == 422

    def test_waitlist_invalid_email_empty(self):
        resp = client.post(
            "/api/v1/waitlist",
            json={"email": ""},
        )
        assert resp.status_code == 422

    def test_waitlist_invalid_email_just_at(self):
        resp = client.post(
            "/api/v1/waitlist",
            json={"email": "@"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# JWT auth on protected API endpoints
# ---------------------------------------------------------------------------


class TestJWTOnProtectedEndpoints:
    """Test that JWT tokens work for accessing protected optimization endpoints."""

    def test_portfolio_with_jwt(self):
        # Signup + login
        email = f"jwt-api-{id(self)}@example.com"
        client.post(
            "/api/v1/auth/signup",
            json={"email": email, "password": "TestPass123!"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "TestPass123!"},
        )
        token = login_resp.json()["access_token"]

        # Use JWT to call portfolio endpoint
        resp = client.post(
            "/api/v1/portfolio/optimize",
            json={
                "assets": [{"symbol": "BTC"}, {"symbol": "ETH"}],
                "risk_tolerance": 0.5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "allocations" in resp.json()
