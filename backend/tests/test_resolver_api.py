from datetime import date, time
import uuid
import pytest
from fastapi.testclient import TestClient
from tests.conftest import csrf_headers


def post(client: TestClient, path: str, payload: dict):
    return client.post(path, json=payload, headers=csrf_headers(client))


def test_conflict_resolver_preview_and_apply_api(authenticated_client: TestClient) -> None:
    client = authenticated_client

    # 1. Setup Pod, Employees, Brand, Process, OperatingPattern
    pod = post(client, "/api/v1/pods", {"name": "Pod Resolver Test"}).json()

    emp1 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-RES01",
            "name": "Alice Solver",
            "email": "alice@example.com",
            "pod_id": pod["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    emp2 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-RES02",
            "name": "Bob Solver",
            "email": "bob@example.com",
            "pod_id": pod["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    proc = post(client, "/api/v1/processes", {"code": "cs_res", "name": "CS Resolver"}).json()

    # Give both employees the skill
    client.put(
        f"/api/v1/employees/{emp1['id']}/skills",
        json={"skills": [{"process_id": proc["id"], "proficiency": "ADVANCED", "is_active": True}]},
        headers=csrf_headers(client),
    )
    client.put(
        f"/api/v1/employees/{emp2['id']}/skills",
        json={"skills": [{"process_id": proc["id"], "proficiency": "ADVANCED", "is_active": True}]},
        headers=csrf_headers(client),
    )

    brand = post(client, "/api/v1/brands", {"code": "br_res", "name": "Brand Resolver"}).json()

    bp = post(
        client,
        "/api/v1/brand-processes",
        {"brand_id": brand["id"], "process_id": proc["id"]},
    ).json()

    # Assign primary to Alice
    post(
        client,
        "/api/v1/primary-assignments",
        {"employee_id": emp1["id"], "brand_process_id": bp["id"]},
    )

    # Operating pattern: Mon-Fri, 9am-6pm, required staff 1
    post(
        client,
        "/api/v1/operating-patterns",
        {
            "brand_process_id": bp["id"],
            "operating_days": [0, 1, 2, 3, 4],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "required_staff": 1,
            "min_staff": 1,
        },
    )

    # Generate draft roster for November 2026
    gen_res = post(
        client,
        "/api/v1/rosters/generate",
        {"month": 11, "year": 2026, "name": "Roster Resolver Test"},
    )
    assert gen_res.status_code in (200, 201)
    roster_id = gen_res.json()["id"]

    # Now add an unavailability for Alice on a specific date (Nov 4, 2026 - Wednesday)
    unavail_res = post(
        client,
        f"/api/v1/employees/{emp1['id']}/unavailability",
        {
            "date": "2026-11-04",
            "reason_type": "PLANNED_LEAVE",
            "is_approved": True,
            "notes": "Family emergency",
        },
    )
    assert unavail_res.status_code in (200, 201)

    # 2. Preview conflict resolutions
    preview_res = post(client, f"/api/v1/rosters/{roster_id}/resolver/preview", {})
    assert preview_res.status_code == 200
    preview_data = preview_res.json()

    assert preview_data["roster_id"] == roster_id
    assert preview_data["status"] in ("OPTIMAL", "FEASIBLE")
    assert "coverage_before_pct" in preview_data
    assert "coverage_after_pct" in preview_data
    assert preview_data["coverage_after_pct"] >= preview_data["coverage_before_pct"]
    assert len(preview_data["passes"]) >= 1

    # 3. Apply conflict resolutions on draft roster
    apply_res = post(
        client,
        f"/api/v1/rosters/{roster_id}/resolver/apply",
        {
            "roster_id": roster_id,
            "approve_cross_pod": True,
            "create_child_if_published": True,
        },
    )
    assert apply_res.status_code == 200
    apply_data = apply_res.json()

    assert apply_data["status"] == "SUCCESS"
    assert apply_data["roster_id"] == roster_id
    assert apply_data["applied_changes_count"] >= 0
    assert apply_data["validation_passed"] is True
    assert apply_data["is_new_version"] is False

    # 4. Now publish the roster and verify child revision creation upon resolving
    pub_res = post(client, f"/api/v1/rosters/{roster_id}/publish", {})
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["status"] == "PUBLISHED"

    # Add another leave for Bob on Nov 5
    post(
        client,
        f"/api/v1/employees/{emp2['id']}/unavailability",
        {
            "date": "2026-11-05",
            "reason_type": "PLANNED_LEAVE",
            "is_approved": True,
            "notes": "Doctor appointment",
        },
    )

    # Preview on published roster
    pub_preview = post(client, f"/api/v1/rosters/{roster_id}/resolver/preview", {})
    assert pub_preview.status_code == 200
    assert pub_preview.json()["is_published"] is True
    assert pub_preview.json()["requires_child_revision"] is True

    # Apply on published roster with create_child_if_published=True
    pub_apply = post(
        client,
        f"/api/v1/rosters/{roster_id}/resolver/apply",
        {
            "roster_id": roster_id,
            "approve_cross_pod": True,
            "create_child_if_published": True,
        },
    )
    assert pub_apply.status_code == 200
    pub_apply_data = pub_apply.json()
    assert pub_apply_data["is_new_version"] is True
    assert pub_apply_data["version"] == 2
    assert pub_apply_data["roster_id"] != roster_id

    # Verify original roster v1 remains unchanged and PUBLISHED
    v1_get = client.get(f"/api/v1/rosters/{roster_id}")
    assert v1_get.status_code == 200
    assert v1_get.json()["status"] == "PUBLISHED"
    assert v1_get.json()["version"] == 1
