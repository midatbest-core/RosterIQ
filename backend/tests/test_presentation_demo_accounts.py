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
