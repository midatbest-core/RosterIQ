import uuid
from datetime import time, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.operations.models import Brand, Process, BrandProcess, PrimaryAssignment
from app.modules.workforce.models import Pod, Employee, EmployeeStatus, EmployeeProcessSkill
from app.modules.roster.models import Roster, RosterStatus, RosterConflict, ConflictType, ConflictSeverity
from tests.conftest import csrf_headers

def test_delete_pod_relocates_employees_to_least_populated_pod(authenticated_client: TestClient, db_session: Session):
    headers = csrf_headers(authenticated_client)

    # Create 3 pods: PodA (to delete, 2 emps), PodB (3 emps), PodC (1 emp - the least!)
    pod_a = Pod(name=f"PodA_{uuid.uuid4().hex[:6]}")
    pod_b = Pod(name=f"PodB_{uuid.uuid4().hex[:6]}")
    pod_c = Pod(name=f"PodC_{uuid.uuid4().hex[:6]}")
    db_session.add_all([pod_a, pod_b, pod_c])
    db_session.commit()

    # 2 emps in Pod A
    emp_a1 = Employee(
        employee_code=f"EA1_{uuid.uuid4().hex[:6]}",
        name="Emp A1",
        email=f"ea1_{uuid.uuid4().hex[:6]}@example.com",
        pod_id=pod_a.id,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        daily_capacity_minutes=540,
        status=EmployeeStatus.ACTIVE,
    )
    emp_a2 = Employee(
        employee_code=f"EA2_{uuid.uuid4().hex[:6]}",
        name="Emp A2",
        email=f"ea2_{uuid.uuid4().hex[:6]}@example.com",
        pod_id=pod_a.id,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        daily_capacity_minutes=540,
        status=EmployeeStatus.ACTIVE,
    )

    # 3 emps in Pod B
    for i in range(3):
        db_session.add(
            Employee(
                employee_code=f"EB{i}_{uuid.uuid4().hex[:6]}",
                name=f"Emp B{i}",
                email=f"eb{i}_{uuid.uuid4().hex[:6]}@example.com",
                pod_id=pod_b.id,
                standard_start_time=time(9, 0),
                standard_end_time=time(18, 0),
                daily_capacity_minutes=540,
                status=EmployeeStatus.ACTIVE,
            )
        )

    # 1 emp in Pod C (least populated)
    db_session.add(
        Employee(
            employee_code=f"EC1_{uuid.uuid4().hex[:6]}",
            name="Emp C1",
            email=f"ec1_{uuid.uuid4().hex[:6]}@example.com",
            pod_id=pod_c.id,
            standard_start_time=time(9, 0),
            standard_end_time=time(18, 0),
            daily_capacity_minutes=540,
            status=EmployeeStatus.ACTIVE,
        )
    )
    db_session.add_all([emp_a1, emp_a2])
    db_session.commit()

    # Delete Pod A
    resp = authenticated_client.delete(f"/api/v1/pods/{pod_a.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["deleted_pod_id"] == str(pod_a.id)
    assert data["target_pod_id"] == str(pod_c.id)  # Relocated to Pod C (least members)
    assert data["moved_employees_count"] == 2

    # Verify Pod A is deleted from database
    assert db_session.get(Pod, pod_a.id) is None

    # Verify employees A1 and A2 are now in Pod C
    db_session.refresh(emp_a1)
    db_session.refresh(emp_a2)
    assert emp_a1.pod_id == pod_c.id
    assert emp_a2.pod_id == pod_c.id


def test_delete_brand_deletes_brand_and_processes(authenticated_client: TestClient, db_session: Session):
    headers = csrf_headers(authenticated_client)

    # Create Brand and 2 Processes
    brand = Brand(code=f"BR_{uuid.uuid4().hex[:6]}", name=f"Brand_{uuid.uuid4().hex[:6]}")
    proc1 = Process(code=f"PR1_{uuid.uuid4().hex[:6]}", name="Process 1")
    proc2 = Process(code=f"PR2_{uuid.uuid4().hex[:6]}", name="Process 2")
    db_session.add_all([brand, proc1, proc2])
    db_session.commit()

    bp1 = BrandProcess(brand_id=brand.id, process_id=proc1.id)
    bp2 = BrandProcess(brand_id=brand.id, process_id=proc2.id)
    db_session.add_all([bp1, bp2])
    db_session.commit()

    # Delete Brand
    resp = authenticated_client.delete(f"/api/v1/brands/{brand.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["deleted_brand_id"] == str(brand.id)
    assert data["deleted_processes_count"] == 2

    # Verify Brand and BrandProcesses are deleted
    assert db_session.get(Brand, brand.id) is None
    assert db_session.get(BrandProcess, bp1.id) is None
    assert db_session.get(BrandProcess, bp2.id) is None

    # Processes themselves remain intact
    assert db_session.get(Process, proc1.id) is not None
    assert db_session.get(Process, proc2.id) is not None


def test_roster_conflicts_display_skill_pod_and_process(authenticated_client: TestClient, db_session: Session):
    headers = csrf_headers(authenticated_client)

    # Create Pod, Brand, Process, BrandProcess
    pod = Pod(name=f"AlphaPod_{uuid.uuid4().hex[:6]}")
    brand = Brand(code=f"B_{uuid.uuid4().hex[:6]}", name=f"AlphaBrand_{uuid.uuid4().hex[:6]}")
    proc = Process(code=f"P_{uuid.uuid4().hex[:6]}", name=f"VoiceSupport_{uuid.uuid4().hex[:6]}")
    db_session.add_all([pod, brand, proc])
    db_session.commit()

    bp = BrandProcess(brand_id=brand.id, process_id=proc.id)
    emp = Employee(
        employee_code=f"EMP_{uuid.uuid4().hex[:6]}",
        name="Alpha Lead",
        email=f"alpha_{uuid.uuid4().hex[:6]}@example.com",
        pod_id=pod.id,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        daily_capacity_minutes=540,
        status=EmployeeStatus.ACTIVE,
    )
    db_session.add_all([bp, emp])
    db_session.commit()

    # Link primary assignment so bp maps to pod
    pa = PrimaryAssignment(
        employee_id=emp.id,
        brand_process_id=bp.id,
        priority=1,
        effective_from=date(2026, 11, 1),
        is_active=True,
    )
    db_session.add(pa)

    # Create Roster & Conflict
    roster = Roster(
        id=uuid.uuid4(),
        name=f"Test Roster {uuid.uuid4().hex[:6]}",
        month=12,
        year=2026,
        version=1,
        status=RosterStatus.DRAFT,
        created_by="test@example.com",
    )
    db_session.add(roster)
    db_session.commit()

    conflict = RosterConflict(
        roster_id=roster.id,
        date=date(2026, 12, 1),
        brand_process_id=bp.id,
        severity=ConflictSeverity.HARD_VIOLATION,
        conflict_type=ConflictType.UNCOVERED_SLOT,
        description="Uncovered demand on 2026-12-01: required 1 employees, assigned 0.",
        is_resolved=False,
    )
    db_session.add(conflict)
    db_session.commit()

    # Call get_roster_grid
    resp = authenticated_client.get(f"/api/v1/rosters/{roster.id}/grid?view_type=company")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary_conflicts" in data
    assert len(data["summary_conflicts"]) == 1
    c_item = data["summary_conflicts"][0]

    # Verify structured fields
    assert c_item["brand_name"] == brand.name
    assert c_item["process_name"] == proc.name
    assert c_item["required_skill"] == proc.name
    assert c_item["pod_name"] == pod.name
    assert c_item["pod_id"] == str(pod.id)
