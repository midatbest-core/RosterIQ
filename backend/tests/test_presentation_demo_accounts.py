from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_production_rejection_for_all_demo_endpoints(monkeypatch):
    """Production mode must unconditionally forbid all demo endpoints."""
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "production")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")  # even if flag is true
    get_settings.cache_clear()

    prod_client = TestClient(app)

    # 1. demo-roles rejected in production
    res1 = prod_client.get("/api/v1/auth/demo-roles")
    assert res1.status_code == 403
    assert "production" in res1.json()["error"]["message"].lower()

    # 2. demo-login rejected in production for all roles
    for role in ["ADMIN", "OPERATIONS_MANAGER", "POD_LEAD", "BRAND_USER", "EMPLOYEE"]:
        res2 = prod_client.post("/api/v1/auth/demo-login", json={"role": role})
        assert res2.status_code == 403
        assert "production" in res2.json()["error"]["message"].lower()

    # 3. presentation-demo-accounts rejected in production
    res3 = prod_client.get("/api/v1/auth/presentation-demo-accounts")
    assert res3.status_code == 403
    assert "production" in res3.json()["error"]["message"].lower()

    get_settings.cache_clear()


def test_demo_roles_returns_five_roles_without_passwords(monkeypatch):
    """GET /api/v1/auth/demo-roles must return all 5 roles and NEVER leak passwords."""
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    resp = client.get("/api/v1/auth/demo-roles")
    assert resp.status_code == 200
    roles = resp.json()
    assert len(roles) == 5

    expected_roles = ["ADMIN", "OPERATIONS_MANAGER", "POD_LEAD", "BRAND_USER", "EMPLOYEE"]
    assert [r["role"] for r in roles] == expected_roles

    for r in roles:
        assert "role" in r
        assert "name" in r
        assert "description" in r
        assert "email" in r and "@" in r["email"]
        # CRITICAL: passwords must never be present in the public roles response
        assert "password" not in r
        assert "password_hash" not in r


@pytest.mark.parametrize("role", ["ADMIN", "OPERATIONS_MANAGER", "POD_LEAD", "BRAND_USER", "EMPLOYEE"])
def test_all_five_roles_direct_demo_login(monkeypatch, role):
    """1-Click demo login must authenticate each of the 5 roles directly without password."""
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    test_client = TestClient(app)
    resp = test_client.post("/api/v1/auth/demo-login", json={"role": role})
    assert resp.status_code == 200, f"Demo login failed for role {role}: {resp.text}"

    data = resp.json()
    assert data["user"]["role"] == role
    assert data["user"]["is_active"] is True
    assert "access_token" in resp.cookies
    assert "csrf_token" in resp.cookies

    # Session persistence verification: /auth/me returns this user
    me_resp = test_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == data["user"]["id"]
    assert me_data["role"] == role


def test_demo_login_session_persistence_and_logout(monkeypatch):
    """Full lifecycle: demo login -> authenticated session -> logout -> session termination."""
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    monkeypatch.setenv("ROSTERIQ_ENABLE_DEMO_CREDENTIALS", "true")
    get_settings.cache_clear()

    session_client = TestClient(app)

    # 1. Unauthenticated /me returns 401
    assert session_client.get("/api/v1/auth/me").status_code == 401

    # 2. 1-Click login as Operations Manager
    login_res = session_client.post("/api/v1/auth/demo-login", json={"role": "OPERATIONS_MANAGER"})
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]

    # 3. Session persists across requests
    me_res = session_client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "OPERATIONS_MANAGER"

    # 4. Logout using CSRF token
    logout_res = session_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout_res.status_code == 204

    # 5. Subsequent request is 401
    assert session_client.get("/api/v1/auth/me").status_code == 401


def test_demo_login_invalid_role(monkeypatch):
    """Invalid role parameter returns 400 Bad Request."""
    monkeypatch.setenv("ROSTERIQ_ENVIRONMENT", "staging")
    get_settings.cache_clear()

    resp = client.post("/api/v1/auth/demo-login", json={"role": "SUPERUSER"})
    assert resp.status_code == 400
    assert "invalid" in resp.json()["error"]["message"].lower()


def test_cookie_samesite_modes(monkeypatch):
    """Cross-domain cookie behavior configuration test."""
    monkeypatch.setenv("ROSTERIQ_COOKIE_SECURE", "false")
    get_settings.cache_clear()
    assert get_settings().effective_cookie_samesite == "lax"

    monkeypatch.setenv("ROSTERIQ_COOKIE_SECURE", "true")
    monkeypatch.delenv("ROSTERIQ_COOKIE_SAMESITE", raising=False)
    get_settings.cache_clear()
    assert get_settings().effective_cookie_samesite == "none"
    get_settings.cache_clear()
