from datetime import time
import uuid
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from tests.conftest import csrf_headers
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import Brand, Process, BrandProcess
from app.modules.operations.pattern_models import OperatingPattern
from app.modules.workforce.models import Pod
from app.modules.roster.models import Roster, RosterStatus
from app.core.security import hash_password


def test_brand_portal_scoping_and_lifecycle(client: TestClient, db_session: Session) -> None:
    # 1. Setup test fixture
    pod = Pod(id=uuid.uuid4(), name=f"Brand Pod {uuid.uuid4().hex[:6]}")
    db_session.add(pod)
    db_session.flush()

    brand_a = Brand(id=uuid.uuid4(), name=f"Brand Alpha {uuid.uuid4().hex[:6]}", code=f"BA_{uuid.uuid4().hex[:4]}")
    brand_b = Brand(id=uuid.uuid4(), name=f"Brand Beta {uuid.uuid4().hex[:6]}", code=f"BB_{uuid.uuid4().hex[:4]}")
    db_session.add_all([brand_a, brand_b])
    db_session.flush()

    proc = Process(id=uuid.uuid4(), name=f"Support Proc {uuid.uuid4().hex[:6]}", code=f"SP_{uuid.uuid4().hex[:4]}")
    db_session.add(proc)
    db_session.flush()

    bp_a = BrandProcess(id=uuid.uuid4(), brand_id=brand_a.id, process_id=proc.id)
    bp_b = BrandProcess(id=uuid.uuid4(), brand_id=brand_b.id, process_id=proc.id)
    db_session.add_all([bp_a, bp_b])
    db_session.flush()

    op_a = OperatingPattern(
        id=uuid.uuid4(),
        brand_process_id=bp_a.id,
        operating_days="0,1,2,3,4",  # Mon-Fri as comma-separated string
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=2,
        min_staffing_weekend=0,
        holiday_behavior="CLOSED",
    )
    db_session.add(op_a)

    # Users
    manager_pwd = hash_password("SecretPass123!")
    manager_user = User(
        id=uuid.uuid4(),
        email=f"ops_mgr_{uuid.uuid4().hex[:6]}@rosteriq.io",
        password_hash=manager_pwd,
        role=UserRole.OPERATIONS_MANAGER,
        is_active=True,
    )
    brand_a_user = User(
        id=uuid.uuid4(),
        email=f"brand_a_{uuid.uuid4().hex[:6]}@brand.com",
        password_hash=manager_pwd,
        role=UserRole.BRAND_USER,
        brand_id=brand_a.id,
        is_active=True,
    )
    brand_b_user = User(
        id=uuid.uuid4(),
        email=f"brand_b_{uuid.uuid4().hex[:6]}@brand.com",
        password_hash=manager_pwd,
        role=UserRole.BRAND_USER,
        brand_id=brand_b.id,
        is_active=True,
    )
    db_session.add_all([manager_user, brand_a_user, brand_b_user])
    db_session.commit()

    # 2. Login Brand A
    resp = client.post("/api/v1/auth/login", json={"email": brand_a_user.email, "password": "SecretPass123!"})
    assert resp.status_code == 200

    # 3. Brand A inspects own profile
    resp = client.get("/api/v1/brand-portal/me")
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["brand_id"] == str(brand_a.id)
    assert len(profile["processes"]) == 1
    assert profile["processes"][0]["brand_process_id"] == str(bp_a.id)
    assert profile["processes"][0]["operating_days"] == [0, 1, 2, 3, 4]

    # 4. IDOR Check: Brand A submits change request for Brand B's process -> 403 Forbidden
    idor_req = client.post(
        "/api/v1/brand-portal/requests",
        json={
            "brand_process_id": str(bp_b.id),
            "request_type": "OPERATING_DAYS",
            "operating_days": [0, 1, 2, 3, 4, 5, 6],
            "reason": "Attempting cross-brand unauthorized modification",
        },
        headers=csrf_headers(client),
    )
    assert idor_req.status_code == 403
    assert "does not belong to your brand" in (idor_req.json().get("error", {}).get("message") or str(idor_req.json()))

    # 5. Valid Request Submission: Brand A requests 365-day operation (adding Sat & Sun)
    submit_resp = client.post(
        "/api/v1/brand-portal/requests",
        json={
            "brand_process_id": str(bp_a.id),
            "request_type": "OPERATING_DAYS",
            "operating_days": [0, 1, 2, 3, 4, 5, 6],
            "reason": "Brand A expanding to 365-day customer support",
        },
        headers=csrf_headers(client),
    )
    assert submit_resp.status_code == 201
    created_req = submit_resp.json()
    req_id = created_req["id"]
    assert created_req["status"] == "PENDING"
    assert created_req["brand_id"] == str(brand_a.id)

    # Verify Brand A's active OperatingPattern has NOT changed immediately
    resp = client.get("/api/v1/brand-portal/me")
    assert resp.json()["processes"][0]["operating_days"] == [0, 1, 2, 3, 4]

    # 6. IDOR Check: Login Brand B and attempt to view Brand A's request
    client.post("/api/v1/auth/login", json={"email": brand_b_user.email, "password": "SecretPass123!"})
    resp = client.get(f"/api/v1/brand-portal/requests/{req_id}")
    assert resp.status_code == 403

    # Switch back to Brand A
    client.post("/api/v1/auth/login", json={"email": brand_a_user.email, "password": "SecretPass123!"})
    resp = client.get(f"/api/v1/brand-portal/requests/{req_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == req_id

    # 7. Brand User CANNOT self-approve (requires Ops Manager)
    unauth_approve = client.post(
        f"/api/v1/brand-portal/requests/{req_id}/approve",
        json={"manager_notes": "Self approval attempt"},
        headers=csrf_headers(client),
    )
    assert unauth_approve.status_code == 403

    # 8. Login as Operations Manager
    client.post("/api/v1/auth/login", json={"email": manager_user.email, "password": "SecretPass123!"})

    # Preview Impact as Ops Manager
    preview_resp = client.post(f"/api/v1/brand-portal/requests/{req_id}/preview-impact", headers=csrf_headers(client))
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["request_id"] == req_id
    assert preview["brand_id"] == str(brand_a.id)

    # Ops Manager Approves: transitions to ROSTER_PENDING, updates OperatingPattern
    approve_resp = client.post(
        f"/api/v1/brand-portal/requests/{req_id}/approve",
        json={"manager_notes": "Approved for Q4 expansion"},
        headers=csrf_headers(client),
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "ROSTER_PENDING"
    assert approved_data["review_notes"] == "Approved for Q4 expansion"

    # Verify active OperatingPattern IS NOW UPDATED to "0,1,2,3,4,5,6"
    db_session.expire_all()
    op_updated = db_session.query(OperatingPattern).filter(OperatingPattern.brand_process_id == bp_a.id).first()
    assert op_updated.operating_days == "0,1,2,3,4,5,6"

    # 9. Mark Implemented (Lifecycle completion after roster publication)
    target_r_id = approved_data.get("implemented_roster_id")
    if target_r_id:
        target_r = db_session.get(Roster, target_r_id)
        target_r.status = RosterStatus.PUBLISHED
        db_session.commit()
    else:
        pub_r = Roster(
            id=uuid.uuid4(),
            name="Nov 2026 Published",
            month=11,
            year=2026,
            version=1,
            status=RosterStatus.PUBLISHED,
            created_by="ops@rosteriq.io",
        )
        db_session.add(pub_r)
        db_session.commit()
        target_r_id = pub_r.id

    impl_resp = client.post(
        f"/api/v1/brand-portal/requests/{req_id}/mark-implemented?roster_id={target_r_id}",
        headers=csrf_headers(client),
    )
    assert impl_resp.status_code == 200
    assert impl_resp.json()["status"] == "IMPLEMENTED"
    assert impl_resp.json()["status"] == "IMPLEMENTED"
