from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_DEFAULTS = {"dev-salt-change-me", "dev-jwt-secret-change-me-in-production"}


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    log_level: str = "info"

    redis_url: str = "redis://localhost:6379/0"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    quantum_backend: str = "simulator"
    originqc_api_key: str = ""
    originqc_endpoint: str = ""

    rate_limit_free: int = 10
    rate_limit_starter: int = 100
    rate_limit_pro: int = 1000
    rate_limit_business: int = 10000

    api_key_salt: str = Field(default="dev-salt-change-me")

    # JWT
    jwt_secret: str = Field(default="dev-jwt-secret-change-me-in-production")
    jwt_expiry_hours: int = 24

    # Stripe price IDs — set these to your live/test Stripe Price objects
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        """Refuse to start in production with insecure default secrets."""
        if self.environment == "production":
            if self.jwt_secret in _INSECURE_DEFAULTS:
                raise ValueError(
                    "jwt_secret must be changed from its default value in production"
                )
            if self.api_key_salt in _INSECURE_DEFAULTS:
                raise ValueError(
                    "api_key_salt must be changed from its default value in production"
                )
            if not self.stripe_webhook_secret:
                logger.warning(
                    "stripe_webhook_secret is empty in production -- "
                    "webhook signature verification is DISABLED"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
