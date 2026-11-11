from datetime import time
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from tests.conftest import csrf_headers
from app.modules.auth.dependencies import check_brand_scope, check_employee_scope, check_pod_scope
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import Brand
from app.modules.workforce.models import Employee, Pod
from app.core.security import hash_password
from app.core.errors import AppError


def test_multi_role_login_and_me(client: TestClient, db_session: Session) -> None:
    # Setup test entities in db_session
    pod = Pod(id=uuid.uuid4(), name="Pod Alpha Test")
    brand = Brand(id=uuid.uuid4(), code="brand_alpha", name="Brand Alpha Test")
    db_session.add_all([pod, brand])
    db_session.flush()

    emp_lead = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-L01",
        name="Lead Alice",
        email="lead.alice@example.com",
        pod_id=pod.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp_staff = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-S01",
        name="Staff Bob",
        email="bob.staff@example.com",
        pod_id=pod.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    db_session.add_all([emp_lead, emp_staff])
    db_session.flush()

    # Seed users
    admin = User(email="admin@example.com", password_hash=hash_password("AdminPass123!"), role=UserRole.ADMIN)
    ops = User(email="ops@example.com", password_hash=hash_password("OpsManager123!"), role=UserRole.OPERATIONS_MANAGER)
    lead = User(
        email="lead@example.com",
        password_hash=hash_password("PodLeadPass123!"),
        role=UserRole.POD_LEAD,
        pod_id=pod.id,
        employee_id=emp_lead.id,
    )
    brand_user = User(
        email="brand@example.com",
        password_hash=hash_password("BrandPass123!"),
        role=UserRole.BRAND_USER,
        brand_id=brand.id,
    )
    emp_user = User(
        email="bob.staff@example.com",
        password_hash=hash_password("EmployeePass123!"),
        role=UserRole.EMPLOYEE,
        employee_id=emp_staff.id,
        pod_id=pod.id,
    )
    db_session.add_all([admin, ops, lead, brand_user, emp_user])
    db_session.commit()

    # 1. Admin login & me
    res = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"})
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "ADMIN"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"

    # 2. Ops Manager login & me
    res = client.post("/api/v1/auth/login", json={"email": "ops@example.com", "password": "OpsManager123!"})
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "OPERATIONS_MANAGER"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "OPERATIONS_MANAGER"

    # 3. Pod Lead login & me
    res = client.post("/api/v1/auth/login", json={"email": "lead@example.com", "password": "PodLeadPass123!"})
    assert res.status_code == 200
    lu = res.json()["user"]
    assert lu["role"] == "POD_LEAD"
    assert lu["pod_id"] == str(pod.id)
    assert lu["employee_id"] == str(emp_lead.id)

    # 4. Brand User login & me
    res = client.post("/api/v1/auth/login", json={"email": "brand@example.com", "password": "BrandPass123!"})
    assert res.status_code == 200
    bu = res.json()["user"]
    assert bu["role"] == "BRAND_USER"
    assert bu["brand_id"] == str(brand.id)

    # 5. Employee login & me
    res = client.post("/api/v1/auth/login", json={"email": "bob.staff@example.com", "password": "EmployeePass123!"})
    assert res.status_code == 200
    eu = res.json()["user"]
    assert eu["role"] == "EMPLOYEE"
    assert eu["employee_id"] == str(emp_staff.id)

    # 6. Test demo accounts endpoint
    demo_res = client.get("/api/v1/auth/demo-accounts")
    assert demo_res.status_code == 200
    data = demo_res.json()
    assert len(data["admins"]) >= 1
    assert len(data["operations_managers"]) >= 1
    assert len(data["pod_leads"]) >= 1
    assert len(data["brand_users"]) >= 1
    assert "Pod Alpha Test" in data["employees_by_pod"]


def test_tenant_and_role_scoping_rules() -> None:
    brand1 = uuid.uuid4()
    brand2 = uuid.uuid4()
    emp1 = uuid.uuid4()
    emp2 = uuid.uuid4()
    pod1 = uuid.uuid4()
    pod2 = uuid.uuid4()

    # Brand scoping: Brand User can only access their own brand
    bu = User(id=uuid.uuid4(), email="b@example.com", password_hash="x", role=UserRole.BRAND_USER, brand_id=brand1)
    check_brand_scope(bu, brand1)  # OK
    with pytest.raises(AppError) as exc:
        check_brand_scope(bu, brand2)
    assert exc.value.status_code == 403

    # Employee scoping: Employee can only access their own profile
    eu = User(id=uuid.uuid4(), email="e@example.com", password_hash="x", role=UserRole.EMPLOYEE, employee_id=emp1)
    check_employee_scope(eu, emp1)  # OK
    with pytest.raises(AppError) as exc:
        check_employee_scope(eu, emp2)
    assert exc.value.status_code == 403

    # Pod scoping: Pod Lead can only access resources in their own pod
    pl = User(id=uuid.uuid4(), email="pl@example.com", password_hash="x", role=UserRole.POD_LEAD, pod_id=pod1)
    check_pod_scope(pl, pod1)  # OK
    with pytest.raises(AppError) as exc:
        check_pod_scope(pl, pod2)
    assert exc.value.status_code == 403

    # Admins and Ops Managers bypass tenant check
    admin = User(id=uuid.uuid4(), email="a@example.com", password_hash="x", role=UserRole.ADMIN)
    check_brand_scope(admin, brand2)
    check_employee_scope(admin, emp2)
    check_pod_scope(admin, pod2)
