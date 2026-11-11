from datetime import date, time
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from tests.conftest import csrf_headers
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import Brand, Process, BrandProcess
from app.modules.workforce.models import Employee, Pod, PodLead
from app.modules.workforce.availability_models import AbsenceReasonType, EmployeeUnavailability
from app.modules.workforce.request_models import EmployeeAvailabilityRequest
from app.modules.roster.models import Roster, EmployeeShift, RosterAllocation, AllocationType, RosterStatus
from app.core.security import hash_password


def test_employee_portal_scoping_and_workflow(client: TestClient, db_session: Session) -> None:
    # 1. Setup fixture
    pod_a = Pod(id=uuid.uuid4(), name=f"Pod Alpha {uuid.uuid4().hex[:6]}")
    pod_b = Pod(id=uuid.uuid4(), name=f"Pod Beta {uuid.uuid4().hex[:6]}")
    db_session.add_all([pod_a, pod_b])
    db_session.flush()

    emp_lead = Employee(
        id=uuid.uuid4(),
        employee_code=f"L_{uuid.uuid4().hex[:4]}",
        name="Lead Alpha",
        email=f"lead_{uuid.uuid4().hex[:6]}@rosteriq.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp_alice = Employee(
        id=uuid.uuid4(),
        employee_code=f"E_{uuid.uuid4().hex[:4]}",
        name="Alice Walker",
        email=f"alice_{uuid.uuid4().hex[:6]}@rosteriq.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp_bob = Employee(
        id=uuid.uuid4(),
        employee_code=f"B_{uuid.uuid4().hex[:4]}",
        name="Bob Smith",
        email=f"bob_{uuid.uuid4().hex[:6]}@rosteriq.io",
        pod_id=pod_b.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    db_session.add_all([emp_lead, emp_alice, emp_bob])
    db_session.flush()

    pod_lead_link = PodLead(pod_id=pod_a.id, employee_id=emp_lead.id)
    db_session.add(pod_lead_link)

    # Users
    pwd = hash_password("Pass1234!")
    u_alice = User(
        id=uuid.uuid4(),
        email=emp_alice.email,
        password_hash=pwd,
        role=UserRole.EMPLOYEE,
        employee_id=emp_alice.id,
        pod_id=pod_a.id,
        is_active=True,
    )
    u_bob = User(
        id=uuid.uuid4(),
        email=emp_bob.email,
        password_hash=pwd,
        role=UserRole.EMPLOYEE,
        employee_id=emp_bob.id,
        pod_id=pod_b.id,
        is_active=True,
    )
    u_lead = User(
        id=uuid.uuid4(),
        email=emp_lead.email,
        password_hash=pwd,
        role=UserRole.POD_LEAD,
        employee_id=emp_lead.id,
        pod_id=pod_a.id,
        is_active=True,
    )
    u_mgr = User(
        id=uuid.uuid4(),
        email=f"mgr_{uuid.uuid4().hex[:6]}@rosteriq.io",
        password_hash=pwd,
        role=UserRole.OPERATIONS_MANAGER,
        is_active=True,
    )
    db_session.add_all([u_alice, u_bob, u_lead, u_mgr])

    # Roster & Allocation for Alice
    brand = Brand(id=uuid.uuid4(), name=f"Brand {uuid.uuid4().hex[:4]}", code=f"B_{uuid.uuid4().hex[:4]}")
    proc = Process(id=uuid.uuid4(), name=f"Process {uuid.uuid4().hex[:4]}", code=f"P_{uuid.uuid4().hex[:4]}")
    db_session.add_all([brand, proc])
    db_session.flush()

    bp = BrandProcess(id=uuid.uuid4(), brand_id=brand.id, process_id=proc.id)
    db_session.add(bp)
    db_session.flush()

    roster = Roster(
        id=uuid.uuid4(),
        name="November 2026 Operational Draft",
        month=11,
        year=2026,
        version=1,
        status=RosterStatus.DRAFT,
        config_hash="abc12345",
    )
    db_session.add(roster)
    db_session.flush()

    target_date = date(2026, 11, 15)
    shift = EmployeeShift(
        id=uuid.uuid4(),
        roster_id=roster.id,
        employee_id=emp_alice.id,
        date=target_date,
        start_time=time(9, 0),
        end_time=time(18, 0),
        is_working_day=True,
    )
    db_session.add(shift)
    db_session.flush()

    alloc = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster.id,
        shift_id=shift.id,
        date=target_date,
        brand_process_id=bp.id,
        employee_id=emp_alice.id,
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )
    db_session.add(alloc)
    db_session.commit()

    # 2. Alice logs in and checks profile
    resp = client.post("/api/v1/auth/login", json={"email": emp_alice.email, "password": "Pass1234!"})
    assert resp.status_code == 200

    resp = client.get("/api/v1/employee-portal/me")
    assert resp.status_code == 200
    prof = resp.json()
    assert prof["employee_id"] == str(emp_alice.id)
    assert prof["name"] == "Alice Walker"
    assert prof["pod_name"] == pod_a.name
    assert prof["pod_lead_name"] == "Lead Alpha"

    # 3. Alice views tasks / checklist
    resp = client.get("/api/v1/employee-portal/tasks?month=11&year=2026")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) == 1
    assert tasks[0]["date"] == "2026-11-15"
    assert tasks[0]["brand_name"] == brand.name
    assert tasks[0]["process_name"] == proc.name

    # 4. Alice submits leave request for 2026-11-15
    submit_resp = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "request_type": "LEAVE",
            "start_date": "2026-11-15",
            "end_date": "2026-11-15",
            "reason_type": "PLANNED_LEAVE",
            "notes": "Family vacation",
        },
        headers=csrf_headers(client),
    )
    assert submit_resp.status_code == 201
    req_data = submit_resp.json()
    req_id = req_data["id"]
    assert req_data["status"] == "PENDING"

    # Verify that EmployeeUnavailability was NOT created yet (pending approval)
    unavail = db_session.query(EmployeeUnavailability).filter(
        EmployeeUnavailability.employee_id == emp_alice.id,
        EmployeeUnavailability.date == target_date,
    ).first()
    assert unavail is None

    # 5. IDOR Scoping Check: Bob logs in and tries to access Alice's request -> 403 Forbidden
    client.post("/api/v1/auth/login", json={"email": emp_bob.email, "password": "Pass1234!"})
    resp = client.get(f"/api/v1/employee-portal/requests/{req_id}")
    assert resp.status_code == 403

    # Pod Lead logs in (same pod as Alice) -> can view request
    client.post("/api/v1/auth/login", json={"email": emp_lead.email, "password": "Pass1234!"})
    resp = client.get(f"/api/v1/employee-portal/requests/{req_id}")
    assert resp.status_code == 200

    # Pod Lead previews impact
    resp = client.post(f"/api/v1/employee-portal/requests/{req_id}/preview-impact", headers=csrf_headers(client))
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["conflicting_allocations_count"] == 1
    assert preview["requires_reassignment"] is True

    # 6. Operations Manager logs in and approves request
    client.post("/api/v1/auth/login", json={"email": u_mgr.email, "password": "Pass1234!"})
    approve_resp = client.post(
        f"/api/v1/employee-portal/requests/{req_id}/approve",
        json={"manager_notes": "Approved by Ops Manager"},
        headers=csrf_headers(client),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "ROSTER_PENDING"

    # Verify EmployeeUnavailability IS NOW CREATED
    db_session.expire_all()
    unavail = db_session.query(EmployeeUnavailability).filter(
        EmployeeUnavailability.employee_id == emp_alice.id,
        EmployeeUnavailability.date == target_date,
    ).first()
    assert unavail is not None
    assert unavail.is_approved is True
    assert unavail.reason_type == AbsenceReasonType.PLANNED_LEAVE

    # 7. Complete lifecycle to IMPLEMENTED
    impl_resp = client.post(f"/api/v1/employee-portal/requests/{req_id}/mark-implemented", headers=csrf_headers(client))
    assert impl_resp.status_code == 200
    assert impl_resp.json()["status"] == "IMPLEMENTED"
