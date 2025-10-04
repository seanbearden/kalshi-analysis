"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Kalshi Market Insights"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"  # Comma-separated list

    # Database
    db_url: PostgresDsn
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False  # SQL query logging

    # Kalshi API
    kalshi_api_base: str = "https://demo-api.kalshi.co/trade-api/v2"
    kalshi_ws_url: str = "wss://demo-api.kalshi.co/trade-api/ws/v2"
    kalshi_poll_interval_seconds: int = 5
    kalshi_request_timeout_seconds: int = 10
    kalshi_max_retries: int = 3

    # Kalshi Authentication (optional - for production API access)
    kalshi_api_key_id: str | None = None
    kalshi_private_key_path: str | None = None

    # Rate Limiting
    rate_limit_per_minute: int = 60

    @field_validator("db_url", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        """Ensure database URL is valid."""
        if not v:
            raise ValueError("DB_URL must be set")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are loaded once and reused.
    """
    return Settings()
