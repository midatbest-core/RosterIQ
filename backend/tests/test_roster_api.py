from datetime import date, time
import uuid

from fastapi.testclient import TestClient

from tests.conftest import csrf_headers


def post(client: TestClient, path: str, payload: dict):
    return client.post(path, json=payload, headers=csrf_headers(client))


def test_roster_generation_and_grid_api(authenticated_client: TestClient) -> None:
    client = authenticated_client

    # 1. Setup Pod, Employees, Brand, Process, OperatingPattern
    pod = post(client, "/api/v1/pods", {"name": "Pod Roster"}).json()

    emp1 = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-R01",
            "name": "Devansh",
            "email": "devansh@example.com",
            "pod_id": pod["id"],
            "daily_capacity_minutes": 540,
            "standard_start_time": "09:00:00",
            "standard_end_time": "18:00:00",
        },
    ).json()

    proc = post(client, "/api/v1/processes", {"code": "cs_r", "name": "CS Roster"}).json()

    client.put(
        f"/api/v1/employees/{emp1['id']}/skills",
        json={"skills": [{"process_id": proc["id"], "proficiency": "ADVANCED", "is_active": True}]},
        headers=csrf_headers(client),
    )

    brand = post(client, "/api/v1/brands", {"code": "br_r", "name": "Brand Roster"}).json()

    bp = post(
        client,
        "/api/v1/brand-processes",
        {"brand_id": brand["id"], "process_id": proc["id"]},
    ).json()

    # Assign primary
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

    # 2. Generate Roster for Nov 2026
    gen_res = post(
        client,
        "/api/v1/rosters/generate",
        {"name": "November 2026 Operational Roster", "month": 11, "year": 2026},
    )
    assert gen_res.status_code == 201, gen_res.text
    roster_data = gen_res.json()
    roster_id = roster_data["id"]
    assert roster_data["version"] == 1
    assert roster_data["total_shifts"] > 0

    # 3. Test Unified Grid API (all 5 modes)
    for mode in ["company", "pod", "brand", "process", "employee"]:
        grid_res = client.get(f"/api/v1/rosters/{roster_id}/grid?view_type={mode}")
        assert grid_res.status_code == 200, f"Failed on mode {mode}: {grid_res.text}"
        grid_data = grid_res.json()
        assert grid_data["view_type"] == mode
        assert len(grid_data["dates"]) == 30
        assert len(grid_data["rows"]) > 0

    # 4. Test Immutability and Publish
    publish_res = client.post(f"/api/v1/rosters/{roster_id}/publish", headers=csrf_headers(client))
    assert publish_res.status_code == 200
    assert publish_res.json()["status"] == "PUBLISHED"

    # Cannot publish again
    pub_again = client.post(f"/api/v1/rosters/{roster_id}/publish", headers=csrf_headers(client))
    assert pub_again.status_code == 400

    # Cannot reassign on a published roster
    reassign_attempt = client.post(
        f"/api/v1/rosters/{roster_id}/reassign/apply",
        json={
            "date": "2026-11-05",
            "brand_process_id": bp["id"],
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": emp1["id"],
        },
        headers=csrf_headers(client),
    )
    assert reassign_attempt.status_code == 400

    # 5. Create Child Version
    child_res = client.post(
        f"/api/v1/rosters/{roster_id}/create-child-version", headers=csrf_headers(client)
    )
    assert child_res.status_code == 200
    child_data = child_res.json()
    assert child_data["version"] == 2
    assert child_data["parent_roster_id"] == roster_id
    assert child_data["status"] == "DRAFT"

