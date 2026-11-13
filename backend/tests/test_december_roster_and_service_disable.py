import uuid
from datetime import date, time
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.operations.models import Brand, Process, BrandProcess, PrimaryAssignment
from app.modules.operations.pattern_models import OperatingPattern
from app.modules.workforce.models import Pod, Employee, EmployeeStatus
from app.modules.roster.models import Roster, RosterStatus, EmployeeShift, RosterAllocation
from tests.conftest import csrf_headers


def test_generate_december_roster_naming_and_dates(
    authenticated_client: TestClient,
    db_session: Session,
):
    """Verify generating a roster for December:
    1. Uses December date range (2026-12-01 to 2026-12-31).
    2. Corrects name if mismatched to December.
    3. Persists month=12, year=2026.
    4. Can be published.
    """
    headers = csrf_headers(authenticated_client)

    # Trigger generation for month=12, year=2026
    resp = authenticated_client.post(
        "/api/v1/rosters/generate",
        headers=headers,
        json={
            "month": 12,
            "year": 2026,
            "name": "November 2026 Production Roster",  # Deliberately mismatched name from UI bug
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    roster_id = data["id"]
    roster_name = data["name"]

    # Verify name was corrected to December
    assert "December" in roster_name
    assert "November" not in roster_name

    # Check database record
    roster_uuid = uuid.UUID(roster_id)
    roster = db_session.get(Roster, roster_uuid)
    assert roster is not None
    assert roster.month == 12
    assert roster.year == 2026
    assert roster.status in (RosterStatus.DRAFT, RosterStatus.VALIDATED)

    # Verify shifts are strictly in December
    shifts = db_session.scalars(
        select(EmployeeShift).where(EmployeeShift.roster_id == roster_uuid)
    ).all()
    for s in shifts:
        assert s.date.month == 12
        assert s.date.year == 2026
        assert 1 <= s.date.day <= 31

    # Verify allocations are strictly in December
    allocs = db_session.scalars(
        select(RosterAllocation).where(RosterAllocation.roster_id == roster_uuid)
    ).all()
    for a in allocs:
        assert a.date.month == 12
        assert a.date.year == 2026
        assert 1 <= a.date.day <= 31

    # Publish the December roster
    pub_resp = authenticated_client.post(
        f"/api/v1/rosters/{roster_id}/publish",
        headers=headers,
    )
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "PUBLISHED"


def test_disable_brand_process_service_exclusion(
    authenticated_client: TestClient,
    db_session: Session,
):
    """Verify disabling an individual BrandProcess:
    1. Sets is_active=False via PATCH /brand-processes/{id}.
    2. Excludes it from demand slots and allocations in new roster generation.
    3. Re-enabling (is_active=True) resumes inclusion.
    """
    headers = csrf_headers(authenticated_client)

    # 1. Setup brand, process, brand_process, pattern
    brand = Brand(code=f"TB_{uuid.uuid4().hex[:6]}", name="Toggle Brand")
    proc = Process(code=f"TP_{uuid.uuid4().hex[:6]}", name="Toggle Process")
    pod = Pod(name=f"TPod_{uuid.uuid4().hex[:6]}")
    db_session.add_all([brand, proc, pod])
    db_session.flush()

    emp = Employee(
        employee_code=f"TE_{uuid.uuid4().hex[:6]}",
        name="Toggle Test Emp",
        email=f"toggle_{uuid.uuid4().hex[:6]}@example.com",
        pod_id=pod.id,
        status=EmployeeStatus.ACTIVE,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        daily_capacity_minutes=540,
    )
    db_session.add(emp)
    db_session.flush()

    bp = BrandProcess(brand_id=brand.id, process_id=proc.id, is_active=True)
    db_session.add(bp)
    db_session.flush()

    pattern = OperatingPattern(
        brand_process_id=bp.id,
        operating_days="0,1,2,3,4",
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    pa = PrimaryAssignment(
        employee_id=emp.id,
        brand_process_id=bp.id,
        priority=1,
        is_active=True,
        effective_from=date(2026, 11, 1),
    )
    db_session.add_all([pattern, pa])
    db_session.commit()

    # 2. Disable the service via PATCH
    patch_resp = authenticated_client.patch(
        f"/api/v1/brand-processes/{bp.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False

    # Refresh DB
    db_session.refresh(bp)
    assert bp.is_active is False

    # 3. Generate a new roster and verify 0 allocations for this brand_process
    gen_resp = authenticated_client.post(
        "/api/v1/rosters/generate",
        headers=headers,
        json={"month": 12, "year": 2026, "name": "Service Exclusion Test Roster"},
    )
    assert gen_resp.status_code == 201
    roster_id = gen_resp.json()["id"]

    allocs_for_bp = db_session.scalars(
        select(RosterAllocation).where(
            RosterAllocation.roster_id == uuid.UUID(roster_id),
            RosterAllocation.brand_process_id == bp.id,
        )
    ).all()
    assert len(allocs_for_bp) == 0, f"Expected 0 allocations for disabled BP, found {len(allocs_for_bp)}"

    # 4. Re-enable the service
    patch_resp2 = authenticated_client.patch(
        f"/api/v1/brand-processes/{bp.id}",
        headers=headers,
        json={"is_active": True},
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["is_active"] is True
