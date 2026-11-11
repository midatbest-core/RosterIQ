from datetime import date, time
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import csrf_headers


def post(client: TestClient, path: str, payload: dict):
    return client.post(path, json=payload, headers=csrf_headers(client))


def test_reassignment_flows_same_and_cross_pod(authenticated_client: TestClient) -> None:
    client = authenticated_client

    # 1. Setup Pod 1 and Pod 2
    pod1 = post(client, "/api/v1/pods", {"name": "Pod Reassign 1"}).json()
    pod2 = post(client, "/api/v1/pods", {"name": "Pod Reassign 2"}).json()

    proc = post(client, "/api/v1/processes", {"code": "cs_reassign", "name": "CS Reassign"}).json()
    brand = post(client, "/api/v1/brands", {"code": "br_reassign", "name": "Brand Reassign"}).json()
    bp = post(client, "/api/v1/brand-processes", {"brand_id": brand["id"], "process_id": proc["id"]}).json()

    # Primary employee in Pod 1
    emp1 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-REA01",
            "name": "Primary Emp",
            "email": "p_emp@example.com",
            "pod_id": pod1["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    # Same-pod backup employee in Pod 1
    emp2 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-REA02",
            "name": "Same Pod Backup",
            "email": "same_pod@example.com",
            "pod_id": pod1["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    # Cross-pod employee in Pod 2
    emp3 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-REA03",
            "name": "Cross Pod Backup",
            "email": "cross_pod@example.com",
            "pod_id": pod2["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    # Add skills
    for emp_id in [emp1["id"], emp2["id"], emp3["id"]]:
        client.put(
            f"/api/v1/employees/{emp_id}/skills",
            json={"skills": [{"process_id": proc["id"], "proficiency": "ADVANCED", "is_active": True}]},
            headers=csrf_headers(client),
        )

    # Assign emp1 as primary
    post(
        client,
        "/api/v1/assignments",
        {
            "employee_id": emp1["id"],
            "brand_process_id": bp["id"],
            "effective_from": "2026-11-01",
            "priority": 1,
        },
    )

    # Generate roster
    roster = post(
        client,
        "/api/v1/rosters/generate",
        {"name": "November 2026 Reassignment Test", "month": 11, "year": 2026},
    ).json()
    roster_id = roster["id"]

    # 2. Test Reassign Preview for Same-Pod Candidate (emp2)
    preview_same = post(
        client,
        f"/api/v1/rosters/{roster_id}/reassign/preview",
        {
            "date": "2026-11-04",
            "brand_process_id": bp["id"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": emp2["id"],
            "source_employee_id": emp1["id"],
        },
    )
    assert preview_same.status_code == 200, preview_same.text
    assert preview_same.json()["is_eligible"] is True
    assert preview_same.json()["allocation_type"] == "SAME_POD_REASSIGNMENT"
    assert preview_same.json()["requires_ops_manager_approval"] is False

    # 3. Test Reassign Preview for Cross-Pod Candidate (emp3)
    preview_cross = post(
        client,
        f"/api/v1/rosters/{roster_id}/reassign/preview",
        {
            "date": "2026-11-05",
            "brand_process_id": bp["id"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": emp3["id"],
            "source_employee_id": emp1["id"],
        },
    )
    assert preview_cross.status_code == 200, preview_cross.text
    assert preview_cross.json()["is_eligible"] is True
    assert preview_cross.json()["allocation_type"] == "CROSS_POD_REASSIGNMENT"
    assert preview_cross.json()["requires_ops_manager_approval"] is True

    # 4. Unauthorized Cross-Pod Apply (Missing confirm_cross_pod_approval=True) -> Must fail with 403
    unauth_cross = post(
        client,
        f"/api/v1/rosters/{roster_id}/reassign/apply",
        {
            "date": "2026-11-05",
            "brand_process_id": bp["id"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": emp3["id"],
            "source_employee_id": emp1["id"],
            "reason": "Test unauth cross pod",
            "confirm_cross_pod_approval": False,
        },
    )
    assert unauth_cross.status_code == 403
    assert "Cross-pod reassignment requires explicit Operations Manager authorization" in unauth_cross.text

    # 5. Authorized Cross-Pod Apply -> Must succeed with 201
    auth_cross = post(
        client,
        f"/api/v1/rosters/{roster_id}/reassign/apply",
        {
            "date": "2026-11-05",
            "brand_process_id": bp["id"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": emp3["id"],
            "source_employee_id": emp1["id"],
            "reason": "Manager authorized cross pod allocation",
            "confirm_cross_pod_approval": True,
        },
    )
    assert auth_cross.status_code == 201
    assert auth_cross.json()["status"] == "reassigned"

    # 6. Same-Pod Apply -> Succeeds without requiring cross-pod confirmation
    same_apply = post(
        client,
        f"/api/v1/rosters/{roster_id}/reassign/apply",
        {
            "date": "2026-11-04",
            "brand_process_id": bp["id"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": emp2["id"],
            "source_employee_id": emp1["id"],
            "reason": "Same pod backup allocation",
        },
    )
    assert same_apply.status_code == 201

    # 7. Audit Log Retrieval & Verification
    log_res = client.get(f"/api/v1/rosters/{roster_id}/allocation-log?dynamic_only=true")
    assert log_res.status_code == 200
    logs = log_res.json()
    assert len(logs) == 2
    cross_entry = [l for l in logs if l["allocation_type"] == "CROSS_POD_REASSIGNMENT"][0]
    assert cross_entry["is_cross_pod_approved"] is True
    assert cross_entry["approved_by_email"] is not None
    assert cross_entry["approved_at"] is not None
    assert cross_entry["employee_name"] == "Cross Pod Backup"
    assert cross_entry["reassigned_from_employee_name"] == "Primary Emp"


def test_stale_roster_behavior_and_immutability(authenticated_client: TestClient) -> None:
    client = authenticated_client

    # 1. Create entities
    pod = post(client, "/api/v1/pods", {"name": "Pod Stale Test"}).json()
    proc = post(client, "/api/v1/processes", {"code": "pr_stale", "name": "Proc Stale"}).json()
    brand = post(client, "/api/v1/brands", {"code": "br_stale", "name": "Brand Stale"}).json()
    bp = post(client, "/api/v1/brand-processes", {"brand_id": brand["id"], "process_id": proc["id"]}).json()

    emp = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-STL01",
            "name": "Stale Emp",
            "email": "stale@example.com",
            "pod_id": pod["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    client.put(
        f"/api/v1/employees/{emp['id']}/skills",
        json={"skills": [{"process_id": proc["id"], "proficiency": "ADVANCED", "is_active": True}]},
        headers=csrf_headers(client),
    )

    post(
        client,
        "/api/v1/assignments",
        {
            "employee_id": emp["id"],
            "brand_process_id": bp["id"],
            "effective_from": "2026-11-01",
            "priority": 1,
        },
    )

    # Generate draft roster
    roster = post(
        client,
        "/api/v1/rosters/generate",
        {"name": "November 2026 Stale Test Roster", "month": 11, "year": 2026},
    ).json()
    roster_id = roster["id"]
    assert roster["status"] in ("DRAFT", "VALIDATED")

    # 2. Introduce a configuration change (assign a new employee or new primary assignment)
    emp2 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-STL02",
            "name": "Stale Emp 2",
            "email": "stale2@example.com",
            "pod_id": pod["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    post(
        client,
        "/api/v1/assignments",
        {
            "employee_id": emp2["id"],
            "brand_process_id": bp["id"],
            "effective_from": "2026-11-15",
            "priority": 2,
        },
    )

    # 3. List rosters -> must detect config hash mismatch and mark roster STALE
    rosters_list = client.get("/api/v1/rosters").json()
    target_roster = next(r for r in rosters_list if r["id"] == roster_id)
    assert target_roster["status"] == "STALE"

    # 4. Attempt to publish a STALE roster -> must fail with 409
    publish_res = client.post(f"/api/v1/rosters/{roster_id}/publish", headers=csrf_headers(client))
    assert publish_res.status_code == 409
    assert "STALE" in publish_res.text

