from __future__ import annotations

import json
from functools import lru_cache

from pydantic import Field, field_validator
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
    cookie_samesite: str = ""
    cors_origins: list[str] | str = ["http://localhost:5173"]

    @property
    def effective_cookie_samesite(self) -> str:
        """Returns the appropriate SameSite attribute.
        
        When cookie_secure is True (HTTPS), defaults to 'none' for cross-domain SPA deployments (e.g. Vercel -> Render).
        When cookie_secure is False (local HTTP), defaults to 'lax' since browsers reject SameSite=None on HTTP.
        """
        if not self.cookie_secure:
            return "lax"
        if self.cookie_samesite:
            s = self.cookie_samesite.strip().lower()
            if s in ("lax", "strict", "none"):
                return s
        return "none"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if (v.startswith("[") and v.endswith("]")) or (v.startswith("{") and v.endswith("}")):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if item]
                except Exception:
                    # Also handle single-quoted array notation like ['https://domain.com']
                    if v.startswith("[") and v.endswith("]"):
                        inner = v[1:-1]
                        return [
                            item.strip().strip("'\"")
                            for item in inner.split(",")
                            if item.strip().strip("'\"")
                        ]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
        return ["http://localhost:5173"]

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

