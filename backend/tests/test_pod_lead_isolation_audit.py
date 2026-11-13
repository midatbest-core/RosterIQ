from datetime import date, time
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import csrf_headers
from app.core.security import hash_password
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import Brand, Process, BrandProcess, PrimaryAssignment
from app.modules.workforce.models import Employee, EmployeeProcessSkill, EmployeeStatus, Pod, PodLead
from app.modules.workforce.availability_models import EmployeeUnavailability, AbsenceReasonType
from app.modules.workforce.request_models import EmployeeAvailabilityRequest, RequestStatus
from app.modules.roster.models import Roster, EmployeeShift, RosterAllocation, AllocationType, RosterStatus


@pytest.fixture()
def audit_fixture(db_session: Session):
    """Sets up a complete two-pod fixture with Lead A, Lead B, Employee A, Employee B, and Draft/Published rosters."""
    pod_a = Pod(id=uuid.uuid4(), name="Pod Alpha Audit")
    pod_b = Pod(id=uuid.uuid4(), name="Pod Beta Audit")
    db_session.add_all([pod_a, pod_b])
    db_session.flush()

    brand = Brand(id=uuid.uuid4(), code="brand_audit", name="Brand Audit")
    proc = Process(id=uuid.uuid4(), code="proc_audit", name="Process Audit")
    db_session.add_all([brand, proc])
    db_session.flush()

    bp = BrandProcess(id=uuid.uuid4(), brand_id=brand.id, process_id=proc.id)
    db_session.add(bp)
    db_session.flush()

    # Employees
    emp_lead_a = Employee(
        id=uuid.uuid4(),
        employee_code="LA01",
        name="Lead Alpha",
        email="lead.alpha@rosteriq.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        status=EmployeeStatus.ACTIVE,
    )
    emp_lead_b = Employee(
        id=uuid.uuid4(),
        employee_code="LB01",
        name="Lead Beta",
        email="lead.beta@rosteriq.io",
        pod_id=pod_b.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        status=EmployeeStatus.ACTIVE,
    )
    emp_a = Employee(
        id=uuid.uuid4(),
        employee_code="EA01",
        name="Worker Alpha",
        email="worker.alpha@rosteriq.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        status=EmployeeStatus.ACTIVE,
    )
    emp_b = Employee(
        id=uuid.uuid4(),
        employee_code="EB01",
        name="Worker Beta",
        email="worker.beta@rosteriq.io",
        pod_id=pod_b.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        status=EmployeeStatus.ACTIVE,
    )
    db_session.add_all([emp_lead_a, emp_lead_b, emp_a, emp_b])
    db_session.flush()

    # Skills
    for emp in [emp_lead_a, emp_lead_b, emp_a, emp_b]:
        db_session.add(
            EmployeeProcessSkill(
                employee_id=emp.id,
                process_id=proc.id,
                proficiency="ADVANCED",
                is_active=True,
            )
        )
    db_session.flush()

    # Pod Leads
    db_session.add(PodLead(pod_id=pod_a.id, employee_id=emp_lead_a.id))
    db_session.add(PodLead(pod_id=pod_b.id, employee_id=emp_lead_b.id))

    # Users
    pwd = hash_password("Secret123!")
    u_admin = User(email="admin@rosteriq.io", password_hash=pwd, role=UserRole.ADMIN, is_active=True)
    u_ops = User(email="ops@rosteriq.io", password_hash=pwd, role=UserRole.OPERATIONS_MANAGER, is_active=True)
    u_lead_a = User(
        email="lead.alpha@rosteriq.io",
        password_hash=pwd,
        role=UserRole.POD_LEAD,
        pod_id=pod_a.id,
        employee_id=emp_lead_a.id,
        is_active=True,
    )
    u_lead_b = User(
        email="lead.beta@rosteriq.io",
        password_hash=pwd,
        role=UserRole.POD_LEAD,
        pod_id=pod_b.id,
        employee_id=emp_lead_b.id,
        is_active=True,
    )
    u_emp_a = User(
        email="worker.alpha@rosteriq.io",
        password_hash=pwd,
        role=UserRole.EMPLOYEE,
        pod_id=pod_a.id,
        employee_id=emp_a.id,
        is_active=True,
    )
    u_emp_b = User(
        email="worker.beta@rosteriq.io",
        password_hash=pwd,
        role=UserRole.EMPLOYEE,
        pod_id=pod_b.id,
        employee_id=emp_b.id,
        is_active=True,
    )
    db_session.add_all([u_admin, u_ops, u_lead_a, u_lead_b, u_emp_a, u_emp_b])
    db_session.flush()

    # Primary assignment
    db_session.add(
        PrimaryAssignment(
            employee_id=emp_a.id,
            brand_process_id=bp.id,
            effective_from=date(2026, 11, 1),
            priority=1,
        )
    )

    # Roster Draft & Published
    roster_draft = Roster(
        id=uuid.uuid4(),
        name="November 2026 Draft Audit",
        month=11,
        year=2026,
        version=1,
        status=RosterStatus.DRAFT,
        created_by="ops@rosteriq.io",
    )
    roster_pub = Roster(
        id=uuid.uuid4(),
        name="November 2026 Published Audit",
        month=11,
        year=2026,
        version=2,
        status=RosterStatus.PUBLISHED,
        created_by="ops@rosteriq.io",
    )
    db_session.add_all([roster_draft, roster_pub])
    db_session.flush()

    # Shifts & Allocations in Draft
    shift_a = EmployeeShift(
        id=uuid.uuid4(),
        roster_id=roster_draft.id,
        employee_id=emp_a.id,
        date=date(2026, 11, 18),
        start_time=time(9, 0),
        end_time=time(18, 0),
        is_working_day=True,
    )
    alloc_a = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster_draft.id,
        shift_id=shift_a.id,
        brand_process_id=bp.id,
        employee_id=emp_a.id,
        date=date(2026, 11, 18),
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )

    # Shifts & Allocations in Published
    shift_pub_a = EmployeeShift(
        id=uuid.uuid4(),
        roster_id=roster_pub.id,
        employee_id=emp_a.id,
        date=date(2026, 11, 19),
        start_time=time(9, 0),
        end_time=time(18, 0),
        is_working_day=True,
    )
    alloc_pub_a = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster_pub.id,
        shift_id=shift_pub_a.id,
        brand_process_id=bp.id,
        employee_id=emp_a.id,
        date=date(2026, 11, 19),
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )

    db_session.add_all([shift_a, alloc_a, shift_pub_a, alloc_pub_a])
    db_session.commit()

    return {
        "pod_a": pod_a,
        "pod_b": pod_b,
        "emp_lead_a": emp_lead_a,
        "emp_lead_b": emp_lead_b,
        "emp_a": emp_a,
        "emp_b": emp_b,
        "bp": bp,
        "roster_draft": roster_draft,
        "roster_pub": roster_pub,
    }


def login_as(client: TestClient, email: str) -> None:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Secret123!"})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"


# =====================================================================
# Phase 2: Pod Lead Authorization & Data Isolation
# =====================================================================

def test_pod_lead_retrieves_own_pod_members_only(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    res = client.get("/api/v1/employees")
    assert res.status_code == 200
    emps = res.json()
    assert len(emps) == 2
    assert all(e["pod_id"] == str(audit_fixture["pod_a"].id) for e in emps)


def test_pod_lead_idor_query_param_bypass(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    res = client.get(f"/api/v1/employees?pod_id={audit_fixture['pod_b'].id}")
    assert res.status_code == 200
    emps = res.json()
    # Must never return Beta employees
    assert not any(e["pod_id"] == str(audit_fixture["pod_b"].id) for e in emps)
    assert all(e["pod_id"] == str(audit_fixture["pod_a"].id) for e in emps)


def test_pod_lead_analytics_strictly_scoped(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    roster_id = audit_fixture["roster_draft"].id
    res = client.get(f"/api/v1/rosters/{roster_id}/analytics")
    assert res.status_code == 200
    data = res.json()
    assert len(data["pods"]) == 1
    assert data["pods"][0]["pod_id"] == str(audit_fixture["pod_a"].id)


def test_pod_lead_calendar_grid_scoped(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    roster_id = audit_fixture["roster_draft"].id
    # Lead requesting own pod
    res = client.get(f"/api/v1/rosters/{roster_id}/grid?view_type=pod&filter_id={audit_fixture['pod_a'].id}")
    assert res.status_code == 200

    # IDOR attempt: Lead requesting Beta pod
    res_idor = client.get(f"/api/v1/rosters/{roster_id}/grid?view_type=pod&filter_id={audit_fixture['pod_b'].id}")
    assert res_idor.status_code == 200
    rows = res_idor.json().get("rows", [])
    assert not any(r.get("group_id") == str(audit_fixture["pod_b"].id) for r in rows)


def test_pod_lead_manager_mutations_forbidden(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    roster_id = audit_fixture["roster_draft"].id
    assert client.post(f"/api/v1/rosters/{roster_id}/publish").status_code == 403
    assert client.post("/api/v1/rosters/generate", json={"month": 11, "year": 2026}).status_code == 403
    assert client.post(f"/api/v1/rosters/{roster_id}/create-child-version").status_code == 403


# =====================================================================
# Phase 3: Conflict Resolution & Reassignment
# =====================================================================

def test_backup_candidates_strictly_same_pod(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    roster_id = audit_fixture["roster_draft"].id
    bp_id = audit_fixture["bp"].id
    res = client.get(
        f"/api/v1/rosters/{roster_id}/backup-candidates?brand_process_id={bp_id}&target_date=2026-11-20&start_time=09:00:00&end_time=18:00:00"
    )
    assert res.status_code == 200
    cands = res.json()
    assert all(c["pod_id"] == str(audit_fixture["pod_a"].id) for c in cands)


def test_pod_lead_cannot_reassign_to_foreign_pod(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    roster_id = audit_fixture["roster_draft"].id
    bp_id = audit_fixture["bp"].id
    foreign_emp_id = audit_fixture["emp_b"].id

    # Preview rejection
    res_prev = client.post(
        f"/api/v1/rosters/{roster_id}/reassign/preview",
        json={
            "brand_process_id": str(bp_id),
            "date": "2026-11-20",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": str(foreign_emp_id),
        },
    )
    assert res_prev.status_code == 200
    assert res_prev.json()["is_eligible"] is False

    # Apply rejection
    res_apply = client.post(
        f"/api/v1/rosters/{roster_id}/reassign/apply",
        json={
            "brand_process_id": str(bp_id),
            "date": "2026-11-20",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": str(foreign_emp_id),
            "confirm_cross_pod_approval": True,
        },
    )
    assert res_apply.status_code == 403


def test_reassignment_on_published_roster_immutable(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    pub_roster_id = audit_fixture["roster_pub"].id
    bp_id = audit_fixture["bp"].id
    emp_a_id = audit_fixture["emp_a"].id

    res = client.post(
        f"/api/v1/rosters/{pub_roster_id}/reassign/apply",
        json={
            "brand_process_id": str(bp_id),
            "date": "2026-11-20",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": str(emp_a_id),
        },
    )
    assert res.status_code == 400
    assert "immutable" in res.text.lower()


# =====================================================================
# Phase 4: Employee Portal Workflows
# =====================================================================

def test_employee_sees_only_own_published_shifts(client: TestClient, audit_fixture: dict):
    login_as(client, "worker.alpha@rosteriq.io")
    res = client.get("/api/v1/employee-portal/tasks?published_only=true")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1
    assert tasks[0]["date"] == "2026-11-19"  # Published shift date


def test_employee_pod_allocations_isolation(client: TestClient, audit_fixture: dict):
    login_as(client, "worker.alpha@rosteriq.io")
    res = client.get("/api/v1/employee-portal/pod-allocations")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 1


def test_employee_absence_validation(client: TestClient, audit_fixture: dict):
    login_as(client, "worker.alpha@rosteriq.io")
    # End before start
    res = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "request_type": "LEAVE",
            "reason_type": "PLANNED_LEAVE",
            "start_date": "2026-11-28",
            "end_date": "2026-11-20",
            "notes": "Invalid range",
        },
    )
    assert res.status_code in (400, 422)

    # Self-approval blocked
    res_appr = client.post(
        f"/api/v1/employee-portal/requests/{uuid.uuid4()}/approve",
        json={"manager_notes": "Attempt"},
    )
    assert res_appr.status_code == 403


# =====================================================================
# Phase 5: Pod Lead Absence Submission on Behalf of Employees
# =====================================================================

def test_pod_lead_submits_for_pod_member_allowed(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    emp_a_id = audit_fixture["emp_a"].id
    res = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "employee_id": str(emp_a_id),
            "request_type": "LEAVE",
            "reason_type": "PLANNED_LEAVE",
            "start_date": "2026-11-25",
            "end_date": "2026-11-25",
            "notes": "Pod Lead authorized submission",
        },
    )
    assert res.status_code == 201
    assert res.json()["employee_id"] == str(emp_a_id)


def test_pod_lead_submits_for_foreign_pod_blocked(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    emp_b_id = audit_fixture["emp_b"].id
    res = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "employee_id": str(emp_b_id),
            "request_type": "LEAVE",
            "reason_type": "PLANNED_LEAVE",
            "start_date": "2026-11-25",
            "end_date": "2026-11-25",
            "notes": "Illegal foreign pod submission",
        },
    )
    assert res.status_code == 403
    assert "own pod" in res.text.lower()


def test_pod_lead_cannot_approve_absence(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    res = client.post(
        f"/api/v1/employee-portal/requests/{uuid.uuid4()}/approve",
        json={"manager_notes": "Lead trying to approve"},
    )
    assert res.status_code == 403


def test_pod_lead_cannot_reject_absence(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    res = client.post(
        f"/api/v1/employee-portal/requests/{uuid.uuid4()}/reject",
        json={"manager_notes": "Lead trying to reject"},
    )
    assert res.status_code == 403


def test_pod_lead_cannot_preview_impact(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    res = client.post(
        f"/api/v1/employee-portal/requests/{uuid.uuid4()}/preview-impact",
    )
    assert res.status_code == 403


def test_ops_manager_and_admin_leave_approval_workflow(client: TestClient, audit_fixture: dict):
    emp_a = audit_fixture["emp_a"]
    # 1. Pod Lead submits request for own pod member
    login_as(client, "lead.alpha@rosteriq.io")
    sub_res = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "employee_id": str(emp_a.id),
            "request_type": "LEAVE",
            "reason_type": "PLANNED_LEAVE",
            "start_date": "2026-11-20",
            "end_date": "2026-11-20",
            "notes": "Annual medical checkup submitted by Lead",
        },
    )
    assert sub_res.status_code == 201
    req_id = sub_res.json()["id"]

    # 2. Pod Lead is forbidden from approving
    res_lead_appr = client.post(
        f"/api/v1/employee-portal/requests/{req_id}/approve",
        json={"manager_notes": "Lead unauthorized approval"},
    )
    assert res_lead_appr.status_code == 403

    # 3. Ops Manager approves successfully
    login_as(client, "ops@rosteriq.io")
    res_ops_appr = client.post(
        f"/api/v1/employee-portal/requests/{req_id}/approve",
        json={"manager_notes": "Approved by Ops Manager"},
    )
    assert res_ops_appr.status_code == 200
    assert res_ops_appr.json()["status"] in ("APPROVED", "ROSTER_PENDING")

    # 4. Create second request and verify System Admin can review and reject
    login_as(client, "lead.alpha@rosteriq.io")
    sub_res2 = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "employee_id": str(emp_a.id),
            "request_type": "LEAVE",
            "reason_type": "SICK_LEAVE",
            "start_date": "2026-11-21",
            "end_date": "2026-11-21",
            "notes": "Second leave request",
        },
    )
    assert sub_res2.status_code == 201
    req2_id = sub_res2.json()["id"]

    # 5. System Admin rejects with mandatory review notes
    login_as(client, "admin@rosteriq.io")
    res_admin_rej = client.post(
        f"/api/v1/employee-portal/requests/{req2_id}/reject",
        json={"manager_notes": "Staffing minimum threshold reached for this shift."},
    )
    assert res_admin_rej.status_code == 200
    assert res_admin_rej.json()["status"] == "REJECTED"


def test_unconfigured_google_sheets_does_not_break_csv_export(client: TestClient, audit_fixture: dict):
    login_as(client, "ops@rosteriq.io")
    r_id = audit_fixture["roster_draft"].id

    # Verify CSV export succeeds with 200 and text/csv even without Google Sheets configuration
    csv_resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=company")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    assert len(csv_resp.text) > 0



# =====================================================================
# Post-Audit Regression Fixes: Direct IDOR and Cross-Pod Defect Tests
# =====================================================================

def test_pod_lead_cannot_view_foreign_employee_profile_or_skills(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    emp_a_id = audit_fixture["emp_a"].id
    emp_b_id = audit_fixture["emp_b"].id

    # Own pod member profile: Allowed
    res_a = client.get(f"/api/v1/employees/{emp_a_id}")
    assert res_a.status_code == 200
    assert res_a.json()["id"] == str(emp_a_id)

    # Foreign pod member profile: Forbidden
    res_b = client.get(f"/api/v1/employees/{emp_b_id}")
    assert res_b.status_code == 403
    assert "permission" in res_b.text.lower() or "other pods" in res_b.text.lower()

    # Foreign pod member skills: Forbidden
    res_b_skills = client.get(f"/api/v1/employees/{emp_b_id}/skills")
    assert res_b_skills.status_code == 403


def test_pod_lead_grid_company_view_strictly_scoped(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    r_id = audit_fixture["roster_draft"].id
    pod_a_id = audit_fixture["pod_a"].id

    res = client.get(f"/api/v1/rosters/{r_id}/grid?view_type=company")
    assert res.status_code == 200
    data = res.json()
    # All returned grid rows must belong to Pod Alpha
    assert len(data["rows"]) > 0
    for row in data["rows"]:
        assert row["group_id"] == str(pod_a_id)


def test_pod_lead_cannot_access_primary_assignments(client: TestClient, audit_fixture: dict):
    # Pod Lead: Forbidden
    login_as(client, "lead.alpha@rosteriq.io")
    res_lead = client.get("/api/v1/assignments")
    assert res_lead.status_code == 403

    # Ops Manager: Allowed
    login_as(client, "ops@rosteriq.io")
    res_ops = client.get("/api/v1/assignments")
    assert res_ops.status_code == 200


def test_pod_lead_allocation_log_strictly_scoped(client: TestClient, audit_fixture: dict):
    login_as(client, "lead.alpha@rosteriq.io")
    r_id = audit_fixture["roster_draft"].id
    pod_a_name = audit_fixture["pod_a"].name

    res = client.get(f"/api/v1/rosters/{r_id}/allocation-log")
    assert res.status_code == 200
    data = res.json()
    for item in data:
        assert item["employee_pod_name"] == pod_a_name


# =====================================================================
# Closure Requirement 1: Negative & Security Tests for mark-implemented
# =====================================================================

def test_mark_implemented_forbidden_for_employee_and_lead(client: TestClient, audit_fixture: dict):
    req_id = uuid.uuid4()
    # Employee forbidden
    login_as(client, "worker.alpha@rosteriq.io")
    res_emp = client.post(f"/api/v1/employee-portal/requests/{req_id}/mark-implemented")
    assert res_emp.status_code == 403

    # Pod Lead forbidden
    login_as(client, "lead.alpha@rosteriq.io")
    res_lead = client.post(f"/api/v1/employee-portal/requests/{req_id}/mark-implemented")
    assert res_lead.status_code == 403


def test_mark_implemented_integrity_checks(client: TestClient, audit_fixture: dict, db_session: Session):
    emp_a = audit_fixture["emp_a"]
    roster_draft = audit_fixture["roster_draft"]
    roster_pub = audit_fixture["roster_pub"]
    u_emp_a = db_session.scalar(select(User).where(User.email == "worker.alpha@rosteriq.io"))

    # 1. Create request in PENDING state
    req_pending = EmployeeAvailabilityRequest(
        id=uuid.uuid4(),
        employee_id=emp_a.id,
        requested_by_user_id=u_emp_a.id,
        request_type="LEAVE",
        reason_type="PLANNED_LEAVE",
        start_date=date(2026, 11, 25),
        end_date=date(2026, 11, 25),
        status=RequestStatus.PENDING.value,
    )
    # 2. Create request in REJECTED state
    req_rejected = EmployeeAvailabilityRequest(
        id=uuid.uuid4(),
        employee_id=emp_a.id,
        requested_by_user_id=u_emp_a.id,
        request_type="LEAVE",
        reason_type="PLANNED_LEAVE",
        start_date=date(2026, 11, 26),
        end_date=date(2026, 11, 26),
        status=RequestStatus.REJECTED.value,
    )
    # 3. Create approved request with draft roster as target
    req_approved = EmployeeAvailabilityRequest(
        id=uuid.uuid4(),
        employee_id=emp_a.id,
        requested_by_user_id=u_emp_a.id,
        request_type="LEAVE",
        reason_type="PLANNED_LEAVE",
        start_date=date(2026, 11, 27),
        end_date=date(2026, 11, 27),
        status=RequestStatus.ROSTER_PENDING.value,
        implemented_roster_id=roster_draft.id,
    )
    db_session.add_all([req_pending, req_rejected, req_approved])
    db_session.commit()

    login_as(client, "ops@rosteriq.io")

    # Negative Check A: Marking PENDING request implemented -> 409 Conflict
    res_pend = client.post(f"/api/v1/employee-portal/requests/{req_pending.id}/mark-implemented")
    assert res_pend.status_code == 409
    assert "pending" in res_pend.text.lower()

    # Negative Check B: Marking REJECTED request implemented -> 409 Conflict
    res_rej = client.post(f"/api/v1/employee-portal/requests/{req_rejected.id}/mark-implemented")
    assert res_rej.status_code == 409
    assert "rejected" in res_rej.text.lower()

    # Negative Check C: Marking implemented before publication (target roster is DRAFT) -> 400 Bad Request
    res_draft = client.post(f"/api/v1/employee-portal/requests/{req_approved.id}/mark-implemented")
    assert res_draft.status_code == 400
    assert "published" in res_draft.text.lower()

    # Negative Check D: Marking implemented against wrong roster (wrong month/year)
    wrong_roster = Roster(
        id=uuid.uuid4(),
        name="Dec 2026 Published",
        month=12,
        year=2026,
        version=1,
        status=RosterStatus.PUBLISHED,
        created_by="ops@rosteriq.io",
    )
    db_session.add(wrong_roster)
    db_session.commit()

    res_wrong = client.post(
        f"/api/v1/employee-portal/requests/{req_approved.id}/mark-implemented?roster_id={wrong_roster.id}"
    )
    assert res_wrong.status_code == 400
    assert "lineage" in res_wrong.text.lower() or "period" in res_wrong.text.lower()

    # Negative Check E: Marking implemented with blocking conflicts remaining on published roster
    from app.modules.roster.models import RosterConflict, ConflictSeverity
    blocking_cf = RosterConflict(
        id=uuid.uuid4(),
        roster_id=roster_pub.id,
        date=date(2026, 11, 25),
        conflict_type="UNAVAILABLE_ALLOCATION",
        severity=ConflictSeverity.HARD_VIOLATION,
        description="Blocking conflict on published roster",
    )
    db_session.add(blocking_cf)
    db_session.commit()

    # Set req_approved target to published roster for testing conflict check
    req_approved.implemented_roster_id = roster_pub.id
    db_session.commit()

    res_cf = client.post(f"/api/v1/employee-portal/requests/{req_approved.id}/mark-implemented")
    assert res_cf.status_code == 409
    assert "blocking conflicts" in res_cf.text.lower()

    # Clean up blocking conflict
    db_session.delete(blocking_cf)
    db_session.commit()

    # Positive: Marking implemented succeeds when roster is published and clean
    res_ok = client.post(f"/api/v1/employee-portal/requests/{req_approved.id}/mark-implemented")
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "IMPLEMENTED"

    # Negative Check F: Repeating operation when already IMPLEMENTED -> 409 Conflict
    res_repeat = client.post(f"/api/v1/employee-portal/requests/{req_approved.id}/mark-implemented")
    assert res_repeat.status_code == 409
    assert "already" in res_repeat.text.lower()


# =====================================================================
# Closure Requirement 2: Employee Cross-Resource IDOR Suite
# =====================================================================

def test_employee_idor_security_suite(client: TestClient, audit_fixture: dict, db_session: Session):
    emp_a = audit_fixture["emp_a"]
    emp_b = audit_fixture["emp_b"]
    u_emp_b = db_session.scalar(select(User).where(User.email == "worker.beta@rosteriq.io"))

    # Create private absence request for Employee B
    req_b = EmployeeAvailabilityRequest(
        id=uuid.uuid4(),
        employee_id=emp_b.id,
        requested_by_user_id=u_emp_b.id,
        request_type="LEAVE",
        reason_type="SICK_LEAVE",
        start_date=date(2026, 11, 28),
        end_date=date(2026, 11, 28),
        notes="Confidential medical treatment",
        status=RequestStatus.PENDING.value,
    )
    db_session.add(req_b)
    db_session.commit()

    # Login as Employee A
    login_as(client, "worker.alpha@rosteriq.io")

    # 1. URL Path IDOR: Employee A accessing Employee B's profile
    res_profile = client.get(f"/api/v1/employees/{emp_b.id}")
    assert res_profile.status_code == 403

    # 2. URL Path IDOR: Employee A accessing Employee B's confidential absence request
    res_req = client.get(f"/api/v1/employee-portal/requests/{req_b.id}")
    assert res_req.status_code == 403
    assert "medical treatment" not in res_req.text

    # 3. Query Parameter IDOR: Employee A trying to fetch Employee B's requests via list
    res_list = client.get(f"/api/v1/employee-portal/requests?employee_id={emp_b.id}")
    assert res_list.status_code == 200
    requests_data = res_list.json()
    # Must never return Employee B's request
    assert not any(r["id"] == str(req_b.id) for r in requests_data)

    # 4. Query Parameter IDOR: Employee A trying to fetch Employee B's shifts
    res_shifts = client.get(f"/api/v1/employee-portal/tasks?employee_id={emp_b.id}")
    assert res_shifts.status_code == 200
    shifts_data = res_shifts.json()
    assert all(s["employee_id"] == str(emp_a.id) for s in shifts_data)

    # 5. Privilege Escalation: Employee A trying to approve/reject Employee B's request
    res_appr = client.post(
        f"/api/v1/employee-portal/requests/{req_b.id}/approve",
        json={"manager_notes": "Employee self-approving colleague"},
    )
    assert res_appr.status_code == 403

    res_rej = client.post(
        f"/api/v1/employee-portal/requests/{req_b.id}/reject",
        json={"manager_notes": "Employee rejecting colleague"},
    )
    assert res_rej.status_code == 403

    # 6. Request Body ID Manipulation: Employee A submitting leave with Employee B's ID
    res_spoof = client.post(
        "/api/v1/employee-portal/requests",
        json={
            "employee_id": str(emp_b.id),
            "request_type": "LEAVE",
            "reason_type": "PLANNED_LEAVE",
            "start_date": "2026-11-29",
            "end_date": "2026-11-29",
            "notes": "Spoofed submission",
        },
    )
    # The endpoint either rejects with 403 or safely binds to Employee A's own ID
    if res_spoof.status_code == 201:
        assert res_spoof.json()["employee_id"] == str(emp_a.id)
    else:
        assert res_spoof.status_code == 403

    # 7. Pod Allocations Scope: Employee A viewing pod allocations sees only Alpha pod
    res_pod = client.get("/api/v1/employee-portal/pod-allocations")
    assert res_pod.status_code == 200
    pod_tasks = res_pod.json()
    assert not any(t.get("employee_id") == str(emp_b.id) for t in pod_tasks)
