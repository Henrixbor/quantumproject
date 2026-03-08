from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
