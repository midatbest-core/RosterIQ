from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("backend/.env", "../.env", ".env"),
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

    # SMTP Email Configuration
    smtp_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "notifications@rosteriq.internal"
    smtp_from_name: str = "RosterIQ Operations"
    smtp_use_tls: bool = True

    # Google Sheets & OAuth 2.0 Configuration
    google_sheets_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/oauth/google/callback"
    google_service_account_info: str = ""
    google_service_account_file: str = ""

    # Presentation Demo Credentials (Staging / Development only; strictly forbidden in production)
    enable_demo_credentials: bool = False
    demo_credentials_json: str = ""



@lru_cache
def get_settings() -> Settings:
    return Settings()

