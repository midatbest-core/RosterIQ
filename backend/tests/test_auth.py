from fastapi.testclient import TestClient

from app.modules.auth.models import User, UserRole
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


def test_independent_tab_sessions_via_bearer_tokens(client: TestClient, admin_user: User, db_session: Session) -> None:
    """Simulates independent browser tabs operating concurrently with different user sessions.
    Each tab uses its own Authorization: Bearer token from sessionStorage."""
    import uuid
    from app.core.security import hash_password

    # Create additional users for Tab 2 and Tab 3
    brand_user = User(
        id=uuid.uuid4(),
        email="brand.tabtest@example.com",
        password_hash=hash_password("BrandPass123!"),
        role=UserRole.BRAND_USER,
    )
    emp_user = User(
        id=uuid.uuid4(),
        email="employee.tabtest@example.com",
        password_hash=hash_password("EmployeePass123!"),
        role=UserRole.EMPLOYEE,
    )
    db_session.add_all([brand_user, emp_user])
    db_session.commit()

    # 1. Tab 1 logs in as Admin
    res1 = client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123!"},
    )
    assert res1.status_code == 200
    token1 = res1.json()["access_token"]
    assert token1 is not None

    # 2. Tab 2 logs in as Brand User
    res2 = client.post(
        "/api/v1/auth/login",
        json={"email": "brand.tabtest@example.com", "password": "BrandPass123!"},
    )
    assert res2.status_code == 200
    token2 = res2.json()["access_token"]
    assert token2 is not None

    # 3. Tab 3 logs in as Employee
    res3 = client.post(
        "/api/v1/auth/login",
        json={"email": "employee.tabtest@example.com", "password": "EmployeePass123!"},
    )
    assert res3.status_code == 200
    token3 = res3.json()["access_token"]
    assert token3 is not None

    # Verify Tab 1 (Admin) still works and returns Admin user
    tab1_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert tab1_me.status_code == 200
    assert tab1_me.json()["role"] == "ADMIN"

    # Verify Tab 2 (Brand User) works and returns BRAND_USER
    tab2_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert tab2_me.status_code == 200
    assert tab2_me.json()["role"] == "BRAND_USER"

    # Verify Tab 3 (Employee) works and returns EMPLOYEE
    tab3_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token3}"})
    assert tab3_me.status_code == 200
    assert tab3_me.json()["role"] == "EMPLOYEE"

    # Verify RBAC isolation: Tab 1 (Admin) can list employees, but Tab 3 (Employee) cannot list all employees
    tab1_ops = client.get("/api/v1/employees", headers={"Authorization": f"Bearer {token1}"})
    assert tab1_ops.status_code == 200

    tab3_ops = client.get("/api/v1/employees", headers={"Authorization": f"Bearer {token3}"})
    assert tab3_ops.status_code == 403

    # Logout from Tab 2 does NOT affect Tab 1 or Tab 3
    tab2_logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token2}"})
    assert tab2_logout.status_code == 204

    tab1_check = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert tab1_check.status_code == 200
    assert tab1_check.json()["role"] == "ADMIN"

    tab3_check = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token3}"})
    assert tab3_check.status_code == 200
    assert tab3_check.json()["role"] == "EMPLOYEE"


