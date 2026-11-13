from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_presentation_demo_accounts_disabled_in_production(monkeypatch):
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "production")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    response = client.get("/api/v1/auth/presentation-demo-accounts")
    assert response.status_code == 403
    data = response.json()
    assert "disabled in production" in data["error"]["message"].lower()


def test_presentation_demo_accounts_disabled_when_flag_false(monkeypatch):
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "development")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "false")
    get_settings.cache_clear()

    response = client.get("/api/v1/auth/presentation-demo-accounts")
    assert response.status_code == 403
    data = response.json()
    assert "disabled" in data["error"]["message"].lower()


def test_presentation_demo_accounts_returns_five_accounts_when_enabled(monkeypatch):
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "development")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    response = client.get("/api/v1/auth/presentation-demo-accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 5

    roles = [a["role"] for a in accounts]
    assert roles == ["ADMIN", "OPERATIONS_MANAGER", "POD_LEAD", "BRAND_USER", "EMPLOYEE"]

    for acc in accounts:
        assert "role_name" in acc
        assert "email" in acc and "@" in acc["email"]
        assert "password" in acc and len(acc["password"]) >= 10
        assert "description" in acc


def test_presentation_demo_accounts_login_succeeds(monkeypatch):
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "development")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    response = client.get("/api/v1/auth/presentation-demo-accounts")
    assert response.status_code == 200
    accounts = response.json()

    for acc in accounts:
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": acc["email"], "password": acc["password"]},
        )
        assert login_resp.status_code == 200, f"Login failed for {acc['role']} ({acc['email']})"
        data = login_resp.json()
        assert data["user"]["email"] == acc["email"]
        assert data["user"]["role"] == acc["role"]


def test_unauthenticated_me_returns_401(monkeypatch):
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    get_settings.cache_clear()
    unauth_client = TestClient(app)
    resp = unauth_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_staging_login_followed_by_authenticated_me(monkeypatch):
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    auth_client = TestClient(app)
    # Fetch demo account
    demo_resp = auth_client.get("/api/v1/auth/presentation-demo-accounts")
    assert demo_resp.status_code == 200
    admin_acc = next(a for a in demo_resp.json() if a["role"] == "ADMIN")

    # Perform login
    login_resp = auth_client.post(
        "/api/v1/auth/login",
        json={"email": admin_acc["email"], "password": admin_acc["password"]},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies

    # Test authenticated /me
    me_resp = auth_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    user_info = me_resp.json()
    assert user_info["email"] == admin_acc["email"]
    assert user_info["role"] == "ADMIN"


def test_cookie_samesite_cross_domain_modes(monkeypatch):
    # Case 1: In local development (cookie_secure=False) => SameSite=lax
    monkeypatch.setenv("ROSTERIQ_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    dev_settings = get_settings()
    assert dev_settings.effective_cookie_samesite == "lax"

    # Case 2: In hosted staging/production (cookie_secure=True) => defaults to SameSite=none for cross-domain Vercel->Render
    monkeypatch.setenv("ROSTERIQ_COOKIE_SECURE", "true")
    monkeypatch.delenv("ROSTERIQ_COOKIE_SAMESITE", raising=False)
    get_settings.cache_clear()
    hosted_settings = get_settings()
    assert hosted_settings.effective_cookie_samesite == "none"

    # Case 3: Explicit override
    monkeypatch.setenv("ROSTERIQ_COOKIE_SAMESITE", "strict")
    get_settings.cache_clear()
    assert get_settings().effective_cookie_samesite == "strict"
    get_settings.cache_clear()


def test_presentation_demo_accounts_fallback_json_parsing(monkeypatch, tmp_path):
    import json
    mock_creds = [
        {"role": "ADMIN", "email": "fallback.admin@test.com", "password": "fallbackpwd123!", "description": "Fallback Admin"},
        {"role": "EMPLOYEE", "email": "fallback.emp@test.com", "password": "fallbackpwd456!", "description": "Fallback Employee"},
    ]
    # Set environment variables
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    monkeypatch.setenv("ROSTERIQ_DEMO_CREDENTIALS_JSON", json.dumps(mock_creds))
    get_settings.cache_clear()

    # Mock os.path.exists to simulate running on hosted environment without local credentials file
    orig_exists = os.path.exists
    def mock_exists(p):
        if ".staging_test_credentials.local" in str(p):
            return False
        return orig_exists(p)
    monkeypatch.setattr("os.path.exists", mock_exists)

    resp = client.get("/api/v1/auth/presentation-demo-accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["email"] == "fallback.admin@test.com"
    assert data[0]["role_name"] == "System Admin"
    assert data[1]["email"] == "fallback.emp@test.com"
    assert data[1]["role_name"] == "Employee"
