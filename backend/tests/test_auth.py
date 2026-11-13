from fastapi.testclient import TestClient

from app.modules.auth.models import User
from tests.conftest import csrf_headers


def test_health_and_authentication(client: TestClient, admin_user: User) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    unauthenticated = client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "NOT_AUTHENTICATED"

    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "WrongPass123!"},
    )
    assert invalid.status_code == 401

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123!"},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["role"] == "ADMIN"
    assert client.cookies.get("access_token")
    assert client.cookies.get("csrf_token")

    current = client.get("/api/v1/auth/me")
    assert current.status_code == 200
    assert current.json()["email"] == admin_user.email

    csrf_rejected = client.post("/api/v1/auth/logout")
    assert csrf_rejected.status_code == 403
    assert csrf_rejected.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"

    logged_out = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert logged_out.status_code == 204


def test_logout_succeeds_even_with_cross_tab_csrf_drift(client: TestClient, admin_user: User) -> None:
    """When multiple tabs are used, tab 1 might hold an older CSRF token while the cookie jar was updated by tab 2.
    Logout must still succeed and clear cookies without trapping the user."""
    client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123!"},
    )
    # Simulate mismatched header from a different tab
    headers = {"X-CSRF-Token": "cross-tab-drifted-token-12345"}
    res = client.post("/api/v1/auth/logout", headers=headers)
    assert res.status_code == 204
    # Cookie should be cleared
    assert not client.cookies.get("access_token")



def test_protected_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/employees")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"

