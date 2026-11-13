from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import uuid
from datetime import date, time
import pytest
from fastapi.testclient import TestClient
from googleapiclient.errors import HttpError
import httpx
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import Brand, BrandProcess, Process
from app.modules.workforce.models import Employee, Pod, PodLead
from app.modules.roster.models import (
    AllocationType,
    EmployeeShift,
    Roster,
    RosterAllocation,
    RosterStatus,
)


@pytest.fixture
def google_export_fixture(db_session: Session):
    pwd = hash_password("TestSecret123!")

    pod_a = Pod(id=uuid.uuid4(), name="Pod Alpha")
    pod_b = Pod(id=uuid.uuid4(), name="Pod Beta")
    db_session.add_all([pod_a, pod_b])
    db_session.flush()

    emp_a = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-GA01",
        name="Grace Alpha",
        email="grace@alpha.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp_b = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-GB01",
        name="Gabe Beta",
        email="gabe@beta.io",
        pod_id=pod_b.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    db_session.add_all([emp_a, emp_b])
    db_session.flush()

    brand1 = Brand(id=uuid.uuid4(), name="Solaris Brand", code="SOL")
    brand2 = Brand(id=uuid.uuid4(), name="Lunar Brand", code="LUN")
    proc = Process(id=uuid.uuid4(), name="CS Core", code="CSC")
    db_session.add_all([brand1, brand2, proc])
    db_session.flush()

    bp1 = BrandProcess(id=uuid.uuid4(), brand_id=brand1.id, process_id=proc.id)
    bp2 = BrandProcess(id=uuid.uuid4(), brand_id=brand2.id, process_id=proc.id)
    db_session.add_all([bp1, bp2])
    db_session.flush()

    roster = Roster(
        id=uuid.uuid4(),
        name="November 2026 Google Sheets Test",
        month=11,
        year=2026,
        version=1,
        status=RosterStatus.PUBLISHED,
        config_hash="test_google_hash_123",
    )
    db_session.add(roster)
    db_session.flush()

    d1 = date(2026, 11, 1)
    s1 = EmployeeShift(id=uuid.uuid4(), roster_id=roster.id, employee_id=emp_a.id, date=d1, start_time=time(9, 0), end_time=time(18, 0), is_working_day=True)
    db_session.add(s1)
    db_session.flush()

    a1 = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster.id,
        shift_id=s1.id,
        date=d1,
        brand_process_id=bp1.id,
        employee_id=emp_a.id,
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )
    db_session.add(a1)
    db_session.flush()

    u_admin = User(id=uuid.uuid4(), email="g_admin@test.com", password_hash=pwd, role=UserRole.ADMIN, is_active=True)
    u_ops = User(id=uuid.uuid4(), email="g_ops@test.com", password_hash=pwd, role=UserRole.OPERATIONS_MANAGER, is_active=True)
    u_lead = User(id=uuid.uuid4(), email="g_lead@test.com", password_hash=pwd, role=UserRole.POD_LEAD, pod_id=pod_a.id, employee_id=emp_a.id, is_active=True)
    u_brand = User(id=uuid.uuid4(), email="g_brand@test.com", password_hash=pwd, role=UserRole.BRAND_USER, brand_id=brand1.id, is_active=True)
    u_emp = User(id=uuid.uuid4(), email="g_emp@test.com", password_hash=pwd, role=UserRole.EMPLOYEE, employee_id=emp_a.id, pod_id=pod_a.id, is_active=True)

    db_session.add_all([u_admin, u_ops, u_lead, u_brand, u_emp])
    db_session.commit()

    return {
        "roster": roster,
        "pod_a": pod_a,
        "pod_b": pod_b,
        "emp_a": emp_a,
        "emp_b": emp_b,
        "brand1": brand1,
        "brand2": brand2,
        "u_admin": u_admin,
        "u_ops": u_ops,
        "u_lead": u_lead,
        "u_brand": u_brand,
        "u_emp": u_emp,
    }


def login(client: TestClient, email: str) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "TestSecret123!"})
    assert resp.status_code == 200, resp.text


def mock_google_sheets_service():
    mock_service = MagicMock()
    mock_spreadsheets = MagicMock()
    mock_create = MagicMock()
    mock_values = MagicMock()
    mock_update = MagicMock()
    mock_batch = MagicMock()

    mock_service.spreadsheets.return_value = mock_spreadsheets
    mock_spreadsheets.create.return_value = mock_create
    mock_create.execute.return_value = {
        "spreadsheetId": "test_sheet_id_mock_123",
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/test_sheet_id_mock_123/edit",
    }

    mock_spreadsheets.values.return_value = mock_values
    mock_values.update.return_value = mock_update
    mock_update.execute.return_value = {"updatedRows": 61}

    mock_spreadsheets.batchUpdate.return_value = mock_batch
    mock_batch.execute.return_value = {"replies": []}

    return mock_service


# =====================================================================
# 1. Google Sheets Status & Missing Config
# =====================================================================

def test_google_sheets_status_endpoint(client: TestClient, google_export_fixture):
    data = google_export_fixture
    login(client, data["u_admin"].email)

    resp = client.get("/api/v1/rosters/export/google-sheets/status")
    assert resp.status_code == 200
    res = resp.json()
    assert "enabled" in res
    assert "scopes" in res
    assert "https://www.googleapis.com/auth/spreadsheets" in res["scopes"]


def test_google_sheets_missing_config_returns_400(client: TestClient, google_export_fixture):
    data = google_export_fixture
    login(client, data["u_admin"].email)
    r_id = data["roster"].id

    # No access token passed, and no server credentials configured
    with patch("app.modules.roster.sheets_service.get_settings") as mock_settings:
        mock_settings.return_value.google_sheets_enabled = False
        mock_settings.return_value.google_service_account_info = ""
        mock_settings.return_value.google_service_account_file = ""
        mock_settings.return_value.google_client_id = ""

        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "company"},
        )
        assert resp.status_code == 400
        assert "Google Sheets export is not configured" in resp.text


# =====================================================================
# 2. Successful Google Sheets Export Across Roles & Scoping
# =====================================================================

def test_google_sheets_export_all_roles_success_and_scoping(client: TestClient, google_export_fixture):
    data = google_export_fixture
    r_id = data["roster"].id
    mock_svc = mock_google_sheets_service()

    with patch("app.modules.roster.sheets_service.build_sheets_client", return_value=mock_svc):
        # 1. Admin Company Export
        login(client, data["u_admin"].email)
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "company", "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 200, resp.text
        res = resp.json()
        assert res["spreadsheet_id"] == "test_sheet_id_mock_123"
        assert "https://docs.google.com/spreadsheets/d/test_sheet_id_mock_123/edit" in res["spreadsheet_url"]
        assert res["rows_exported"] > 0

        # 2. Ops Manager Pod Export
        login(client, data["u_ops"].email)
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "pod", "filter_id": str(data["pod_a"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 200
        assert resp.json()["spreadsheet_id"] == "test_sheet_id_mock_123"

        # 3. Pod Lead Authorized Pod Export
        login(client, data["u_lead"].email)
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "pod", "filter_id": str(data["pod_a"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 200

        # Pod Lead Foreign Pod Attempt -> 403
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "pod", "filter_id": str(data["pod_b"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 403
        assert "Pod Leads can only export their authorized pod" in resp.text

        # 4. Brand User Authorized Brand Export
        login(client, data["u_brand"].email)
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "brand", "filter_id": str(data["brand1"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 200

        # Brand User Foreign Brand Attempt -> 403
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "brand", "filter_id": str(data["brand2"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 403
        assert "Brand users can only export their own brand" in resp.text

        # 5. Employee User Authorized Export
        login(client, data["u_emp"].email)
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "employee", "filter_id": str(data["emp_a"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 200

        # Employee User Foreign Employee Attempt -> 403
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "employee", "filter_id": str(data["emp_b"].id), "google_access_token": "mock_valid_token_xyz"},
        )
        assert resp.status_code == 403
        assert "Employees can only export their own assignments" in resp.text


# =====================================================================
# 3. API Error Handling: Expired Token, Quota, Server Error
# =====================================================================

def test_google_sheets_expired_auth_returns_401(client: TestClient, google_export_fixture):
    data = google_export_fixture
    r_id = data["roster"].id
    login(client, data["u_admin"].email)

    # Simulate 401 HttpError from Google Sheets API
    resp_mock = MagicMock()
    resp_mock.status = 401
    resp_mock.reason = "Unauthorized / Token Expired"
    err = HttpError(resp=resp_mock, content=b'{"error": {"message": "Invalid Credentials"}}')

    mock_svc = MagicMock()
    mock_svc.spreadsheets.return_value.create.return_value.execute.side_effect = err

    with patch("app.modules.roster.sheets_service.build_sheets_client", return_value=mock_svc):
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "company", "google_access_token": "expired_token_123"},
        )
        assert resp.status_code == 401
        assert "Google authorization has expired or was revoked" in resp.text


def test_google_sheets_quota_exceeded_returns_403(client: TestClient, google_export_fixture):
    data = google_export_fixture
    r_id = data["roster"].id
    login(client, data["u_admin"].email)

    resp_mock = MagicMock()
    resp_mock.status = 403
    resp_mock.reason = "Rate Limit Exceeded"
    err = HttpError(resp=resp_mock, content=b'{"error": {"message": "User Rate Limit Exceeded"}}')

    mock_svc = MagicMock()
    mock_svc.spreadsheets.return_value.create.return_value.execute.side_effect = err

    with patch("app.modules.roster.sheets_service.build_sheets_client", return_value=mock_svc):
        resp = client.post(
            f"/api/v1/rosters/{r_id}/export/google-sheets",
            json={"view_type": "company", "google_access_token": "valid_token_123"},
        )
        assert resp.status_code == 403
        assert "Google API quota exceeded or permission denied" in resp.text


# =====================================================================
# 4. Portal Endpoints for Google Sheets
# =====================================================================

def test_portal_google_sheets_endpoints(client: TestClient, google_export_fixture):
    data = google_export_fixture
    mock_svc = mock_google_sheets_service()

    with patch("app.modules.roster.sheets_service.build_sheets_client", return_value=mock_svc):
        # Brand Portal Google Sheets Export
        login(client, data["u_brand"].email)
        resp = client.post(
            "/api/v1/brand-portal/export/google-sheets",
            json={"google_access_token": "mock_token_brand"},
        )
        assert resp.status_code == 200
        assert resp.json()["spreadsheet_id"] == "test_sheet_id_mock_123"

        # Employee Portal Google Sheets Export
        login(client, data["u_emp"].email)
        resp = client.post(
            "/api/v1/employee-portal/export/google-sheets",
            json={"google_access_token": "mock_token_emp"},
        )
        assert resp.status_code == 200
        assert resp.json()["spreadsheet_id"] == "test_sheet_id_mock_123"

