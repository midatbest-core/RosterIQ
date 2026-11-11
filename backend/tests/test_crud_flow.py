from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import csrf_headers


def post(client: TestClient, path: str, payload: dict):
    return client.post(path, json=payload, headers=csrf_headers(client))


def patch(client: TestClient, path: str, payload: dict):
    return client.patch(path, json=payload, headers=csrf_headers(client))


def test_phase_one_crud_flow(authenticated_client: TestClient) -> None:
    client = authenticated_client

    pod_response = post(client, "/api/v1/pods", {"name": "Pod Alpha"})
    assert pod_response.status_code == 201, pod_response.text
    pod = pod_response.json()

    employee_response = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "emp-001",
            "name": "Asha Rao",
            "email": "asha@example.com",
            "pod_id": pod["id"],
            "daily_capacity_minutes": 480,
            "standard_start_time": "09:00:00",
            "standard_end_time": "17:00:00"
        },
    )
    assert employee_response.status_code == 201, employee_response.text
    employee = employee_response.json()
    assert employee["employee_code"] == "EMP-001"

    lead_response = patch(
        client,
        f"/api/v1/pods/{pod['id']}",
        {"lead_employee_id": employee["id"]},
    )
    assert lead_response.status_code == 200, lead_response.text
    assert lead_response.json()["lead_employee_id"] == employee["id"]

    process_response = post(
        client,
        "/api/v1/processes",
        {"code": "cs", "name": "Customer Support", "description": "Customer care"},
    )
    assert process_response.status_code == 201, process_response.text
    process = process_response.json()

    skill_response = client.put(
        f"/api/v1/employees/{employee['id']}/skills",
        json={
            "skills": [
                {
                    "process_id": process["id"],
                    "proficiency": "ADVANCED",
                    "is_active": True,
                }
            ]
        },
        headers=csrf_headers(client),
    )
    assert skill_response.status_code == 200, skill_response.text
    assert skill_response.json()[0]["process_id"] == process["id"]

    brand_response = post(
        client,
        "/api/v1/brands",
        {"code": "acme", "name": "Acme Direct"},
    )
    assert brand_response.status_code == 201, brand_response.text
    brand = brand_response.json()

    brand_process_response = post(
        client,
        "/api/v1/brand-processes",
        {
            "brand_id": brand["id"],
            "process_id": process["id"],
            "timezone": "Asia/Kolkata",
            "holiday_behavior": "REDUCED",
            "holiday_min_employees": 1,
        },
    )
    assert brand_process_response.status_code == 201, brand_process_response.text
    brand_process = brand_process_response.json()

    assignment_response = post(
        client,
        "/api/v1/assignments",
        {
            "employee_id": employee["id"],
            "brand_process_id": brand_process["id"],
            "effective_from": date.today().isoformat(),
            "priority": 1,
        },
    )
    assert assignment_response.status_code == 201, assignment_response.text
    assignment = assignment_response.json()

    overlapping = post(
        client,
        "/api/v1/assignments",
        {
            "employee_id": employee["id"],
            "brand_process_id": brand_process["id"],
            "effective_from": date.today().isoformat(),
            "priority": 2,
        },
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["error"]["code"] == "ASSIGNMENT_DATE_OVERLAP"

    assert client.get("/api/v1/employees").json()[0]["id"] == employee["id"]
    assert client.get("/api/v1/brands").json()[0]["id"] == brand["id"]
    assert client.get("/api/v1/processes").json()[0]["id"] == process["id"]
    assert client.get("/api/v1/brand-processes").json()[0]["id"] == brand_process["id"]
    assert client.get("/api/v1/assignments").json()[0]["id"] == assignment["id"]


def test_validation_and_unique_constraint_errors(authenticated_client: TestClient) -> None:
    client = authenticated_client
    invalid_shift = post(
        client,
        "/api/v1/employees",
        {
            "employee_code": "EMP-002",
            "name": "Invalid Shift",
            "email": "invalid@example.com",
            "daily_capacity_minutes": 480,
            "standard_start_time": "17:00:00",
            "standard_end_time": "09:00:00",
        },
    )
    assert invalid_shift.status_code == 422
    assert invalid_shift.json()["error"]["code"] == "VALIDATION_ERROR"

    first = post(client, "/api/v1/brands", {"code": "DUP", "name": "First Brand"})
    assert first.status_code == 201
    duplicate = post(client, "/api/v1/brands", {"code": "DUP", "name": "Second Brand"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"

