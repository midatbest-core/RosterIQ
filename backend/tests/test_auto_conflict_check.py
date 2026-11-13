import uuid
from datetime import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.operations.models import Brand, Process
from app.modules.workforce.models import Pod, Employee, EmployeeStatus
from tests.conftest import csrf_headers

def test_auto_conflict_check_on_brand_process_link(authenticated_client: TestClient, db_session: Session):
    headers = csrf_headers(authenticated_client)
    b = Brand(code=f"B_{uuid.uuid4().hex[:6]}", name="Test Brand")
    p = Process(code=f"P_{uuid.uuid4().hex[:6]}", name="Test Process")
    db_session.add_all([b, p])
    db_session.commit()

    resp = authenticated_client.post(
        "/api/v1/brand-processes",
        headers=headers,
        json={"brand_id": str(b.id), "process_id": str(p.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "conflict_check" in data
    assert data["conflict_check"] is not None
    assert data["conflict_check"]["checked"] is True
    assert "total_conflicts" in data["conflict_check"]

def test_auto_conflict_check_on_create_employee(authenticated_client: TestClient, db_session: Session):
    headers = csrf_headers(authenticated_client)
    pod = Pod(name=f"Pod_{uuid.uuid4().hex[:6]}")
    db_session.add(pod)
    db_session.commit()

    code = f"E_{uuid.uuid4().hex[:6]}"
    resp = authenticated_client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "employee_code": code,
            "name": "Auto Conflict Test Emp",
            "email": f"{code.lower()}@example.com",
            "pod_id": str(pod.id),
            "standard_start_time": "09:00:00",
            "standard_end_time": "17:00:00",
            "daily_capacity_minutes": 480,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "conflict_check" in data
    assert data["conflict_check"] is not None
    assert data["conflict_check"]["checked"] is True

def test_auto_conflict_check_on_move_employee(authenticated_client: TestClient, db_session: Session):
    headers = csrf_headers(authenticated_client)
    pod1 = Pod(name=f"Pod1_{uuid.uuid4().hex[:6]}")
    pod2 = Pod(name=f"Pod2_{uuid.uuid4().hex[:6]}")
    db_session.add_all([pod1, pod2])
    db_session.commit()

    emp = Employee(
        employee_code=f"EMP_{uuid.uuid4().hex[:6]}",
        name="Movable Employee",
        email=f"movable_{uuid.uuid4().hex[:6]}@example.com",
        pod_id=pod1.id,
        standard_start_time=time(9, 0),
        standard_end_time=time(17, 0),
        daily_capacity_minutes=480,
        status=EmployeeStatus.ACTIVE,
    )
    db_session.add(emp)
    db_session.commit()

    # Move employee to pod2
    resp = authenticated_client.patch(
        f"/api/v1/employees/{emp.id}",
        headers=headers,
        json={"pod_id": str(pod2.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pod_id"] == str(pod2.id)
    assert "conflict_check" in data
    assert data["conflict_check"] is not None
    assert data["conflict_check"]["checked"] is True
