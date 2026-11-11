from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_prefix="ROSTERIQ_",
        extra="ignore",
    )

    app_name: str = "RosterIQ API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://rosteriq:rosteriq@localhost:5432/rosteriq"
    jwt_secret: str = "development-only-change-me-at-least-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=60, ge=5, le=1440)
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

