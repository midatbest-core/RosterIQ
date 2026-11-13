import csv
import io
import uuid
from datetime import date, time
import pytest
from fastapi.testclient import TestClient
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
from tests.conftest import csrf_headers


@pytest.fixture
def export_test_fixture(db_session: Session):
    pwd = hash_password("TestSecret123!")

    # 1. Setup Pods
    pod_a = Pod(id=uuid.uuid4(), name="Pod Alpha")
    pod_b = Pod(id=uuid.uuid4(), name="Pod Beta")
    db_session.add_all([pod_a, pod_b])
    db_session.flush()

    # 2. Setup Employees
    emp_a1 = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-A01",
        name="Alice Alpha",
        email="alice@alpha.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp_a2 = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-A02",
        name="Aaron Alpha",
        email="aaron@alpha.io",
        pod_id=pod_a.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp_b1 = Employee(
        id=uuid.uuid4(),
        employee_code="EMP-B01",
        name="Bob Beta",
        email="bob@beta.io",
        pod_id=pod_b.id,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    db_session.add_all([emp_a1, emp_a2, emp_b1])
    db_session.flush()

    # Pod Lead
    db_session.add(PodLead(pod_id=pod_a.id, employee_id=emp_a1.id))
    db_session.add(PodLead(pod_id=pod_b.id, employee_id=emp_b1.id))

    # 3. Brands and Processes
    brand1 = Brand(id=uuid.uuid4(), name="Alpha Brand", code="ALPHABR")
    brand2 = Brand(id=uuid.uuid4(), name="Beta Brand", code="BETABR")
    proc1 = Process(id=uuid.uuid4(), name="Support Tier 1", code="SUP1")
    proc2 = Process(id=uuid.uuid4(), name="Sales Cart", code="CART")
    db_session.add_all([brand1, brand2, proc1, proc2])
    db_session.flush()

    bp1 = BrandProcess(id=uuid.uuid4(), brand_id=brand1.id, process_id=proc1.id)
    bp2 = BrandProcess(id=uuid.uuid4(), brand_id=brand2.id, process_id=proc2.id)
    db_session.add_all([bp1, bp2])
    db_session.flush()

    # 4. Roster
    roster = Roster(
        id=uuid.uuid4(),
        name="November 2026 Export Roster",
        month=11,
        year=2026,
        version=1,
        status=RosterStatus.PUBLISHED,
        config_hash="test_export_hash_123",
    )
    db_session.add(roster)
    db_session.flush()

    # 5. Shifts and Allocations on 2026-11-01 and 2026-11-02
    d1 = date(2026, 11, 1)
    d2 = date(2026, 11, 2)

    # Shift for Alice (working on d1 and d2)
    s_a1 = EmployeeShift(id=uuid.uuid4(), roster_id=roster.id, employee_id=emp_a1.id, date=d1, start_time=time(9, 0), end_time=time(18, 0), is_working_day=True)
    s_a2 = EmployeeShift(id=uuid.uuid4(), roster_id=roster.id, employee_id=emp_a1.id, date=d2, start_time=time(9, 0), end_time=time(18, 0), is_working_day=True)
    # Shift for Aaron (weekly off on d1, working on d2)
    s_aaron1 = EmployeeShift(id=uuid.uuid4(), roster_id=roster.id, employee_id=emp_a2.id, date=d1, start_time=None, end_time=None, is_working_day=False)
    s_aaron2 = EmployeeShift(id=uuid.uuid4(), roster_id=roster.id, employee_id=emp_a2.id, date=d2, start_time=time(9, 0), end_time=time(18, 0), is_working_day=True)
    # Shift for Bob (working on d1)
    s_b1 = EmployeeShift(id=uuid.uuid4(), roster_id=roster.id, employee_id=emp_b1.id, date=d1, start_time=time(9, 0), end_time=time(18, 0), is_working_day=True)

    db_session.add_all([s_a1, s_a2, s_aaron1, s_aaron2, s_b1])
    db_session.flush()

    # Allocations
    # Alice on bp1
    a1 = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster.id,
        shift_id=s_a1.id,
        date=d1,
        brand_process_id=bp1.id,
        employee_id=emp_a1.id,
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )
    a2 = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster.id,
        shift_id=s_a2.id,
        date=d2,
        brand_process_id=bp1.id,
        employee_id=emp_a1.id,
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )
    # Bob on bp2
    a3 = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster.id,
        shift_id=s_b1.id,
        date=d1,
        brand_process_id=bp2.id,
        employee_id=emp_b1.id,
        start_time=time(9, 0),
        end_time=time(18, 0),
        allocation_type=AllocationType.PRIMARY,
    )
    db_session.add_all([a1, a2, a3])
    db_session.flush()

    # 6. Users for all 5 roles
    u_admin = User(id=uuid.uuid4(), email="admin_exp@test.com", password_hash=pwd, role=UserRole.ADMIN, is_active=True)
    u_ops = User(id=uuid.uuid4(), email="ops_exp@test.com", password_hash=pwd, role=UserRole.OPERATIONS_MANAGER, is_active=True)
    u_lead_a = User(id=uuid.uuid4(), email="lead_a_exp@test.com", password_hash=pwd, role=UserRole.POD_LEAD, pod_id=pod_a.id, employee_id=emp_a1.id, is_active=True)
    u_lead_b = User(id=uuid.uuid4(), email="lead_b_exp@test.com", password_hash=pwd, role=UserRole.POD_LEAD, pod_id=pod_b.id, employee_id=emp_b1.id, is_active=True)
    u_brand1 = User(id=uuid.uuid4(), email="brand1_exp@test.com", password_hash=pwd, role=UserRole.BRAND_USER, brand_id=brand1.id, is_active=True)
    u_brand2 = User(id=uuid.uuid4(), email="brand2_exp@test.com", password_hash=pwd, role=UserRole.BRAND_USER, brand_id=brand2.id, is_active=True)
    u_emp_alice = User(id=uuid.uuid4(), email="emp_alice_exp@test.com", password_hash=pwd, role=UserRole.EMPLOYEE, employee_id=emp_a1.id, pod_id=pod_a.id, is_active=True)
    u_emp_bob = User(id=uuid.uuid4(), email="emp_bob_exp@test.com", password_hash=pwd, role=UserRole.EMPLOYEE, employee_id=emp_b1.id, pod_id=pod_b.id, is_active=True)

    db_session.add_all([u_admin, u_ops, u_lead_a, u_lead_b, u_brand1, u_brand2, u_emp_alice, u_emp_bob])
    db_session.commit()

    return {
        "roster": roster,
        "pod_a": pod_a,
        "pod_b": pod_b,
        "emp_a1": emp_a1,
        "emp_a2": emp_a2,
        "emp_b1": emp_b1,
        "brand1": brand1,
        "brand2": brand2,
        "proc1": proc1,
        "proc2": proc2,
        "u_admin": u_admin,
        "u_ops": u_ops,
        "u_lead_a": u_lead_a,
        "u_lead_b": u_lead_b,
        "u_brand1": u_brand1,
        "u_brand2": u_brand2,
        "u_emp_alice": u_emp_alice,
        "u_emp_bob": u_emp_bob,
    }


def parse_csv_response(response) -> list[dict]:
    content = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def login(client: TestClient, email: str) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "TestSecret123!"})
    assert resp.status_code == 200, resp.text


# =====================================================================
# 1. All Supported Views (Admin / Operations Manager)
# =====================================================================

def test_export_all_five_views_admin(client: TestClient, export_test_fixture):
    data = export_test_fixture
    login(client, data["u_admin"].email)
    r_id = data["roster"].id

    # 1. Company View
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=company")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert 'filename="roster_November_2026_Export_Roster_company_v1.csv"' in resp.headers["content-disposition"]
    rows = parse_csv_response(resp)
    assert len(rows) > 0
    # Must have 3 employees * 30 days = 90 rows (since November has 30 days)
    assert len(rows) == 90
    assert any(r["Employee Name"] == "Alice Alpha" and r["Allocation Status"] == "PRIMARY" for r in rows)
    assert any(r["Employee Name"] == "Aaron Alpha" and r["Allocation Status"] == "WEEKLY_OFF" for r in rows)
    assert any(r["Employee Name"] == "Bob Beta" and r["Brand"] == "Beta Brand" for r in rows)

    # 2. Pod View (Pod Alpha)
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=pod&filter_id={data['pod_a'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    # Pod Alpha has 2 employees * 30 days = 60 rows
    assert len(rows) == 60
    assert all(r["Pod"] == "Pod Alpha" for r in rows)
    assert not any(r["Employee Name"] == "Bob Beta" for r in rows)

    # 3. Brand View (Alpha Brand)
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=brand&filter_id={data['brand1'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    # Alpha Brand has 1 BP * 30 days = 30 rows
    assert len(rows) == 30
    assert all(r["Brand"] == "Alpha Brand" for r in rows)
    assert any(r["Allocation Status"] == "PRIMARY" and r["Employee Name"] == "Alice Alpha" for r in rows)

    # 4. Process View (Support Tier 1)
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=process&filter_id={data['proc1'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 30
    assert all(r["Process"] == "Support Tier 1" for r in rows)

    # 5. Employee View (Alice Alpha)
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=employee&filter_id={data['emp_a1'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 30
    assert all(r["Employee Name"] == "Alice Alpha" for r in rows)


def test_export_operations_manager_access(client: TestClient, export_test_fixture):
    data = export_test_fixture
    login(client, data["u_ops"].email)
    r_id = data["roster"].id

    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=company")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 90


# =====================================================================
# 2. RBAC & Object-Level Scoping: Pod Lead
# =====================================================================

def test_pod_lead_scoping_rules(client: TestClient, export_test_fixture):
    data = export_test_fixture
    r_id = data["roster"].id

    # Pod Lead A logs in
    login(client, data["u_lead_a"].email)

    # 1. Authorized Pod Export -> Success
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=pod&filter_id={data['pod_a'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 60
    assert all(r["Pod"] == "Pod Alpha" for r in rows)

    # 2. Unauthorized Foreign Pod Export -> 403 Forbidden
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=pod&filter_id={data['pod_b'].id}")
    assert resp.status_code == 403
    assert "Pod Leads can only export their authorized pod" in resp.text

    # 3. Unauthorized Company View -> 403 Forbidden
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=company")
    assert resp.status_code == 403

    # 4. Unauthorized Brand View -> 403 Forbidden
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=brand")
    assert resp.status_code == 403

    # 5. Authorized Pod Member Employee Export -> Success
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=employee&filter_id={data['emp_a1'].id}")
    assert resp.status_code == 200

    # 6. Unauthorized Foreign Pod Employee Export -> 403 Forbidden
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=employee&filter_id={data['emp_b1'].id}")
    assert resp.status_code == 403


# =====================================================================
# 3. RBAC & Object-Level Scoping: Brand User
# =====================================================================

def test_brand_user_scoping_rules(client: TestClient, export_test_fixture):
    data = export_test_fixture
    r_id = data["roster"].id

    login(client, data["u_brand1"].email)

    # 1. Authorized Brand Export -> Success
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=brand&filter_id={data['brand1'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 30
    assert all(r["Brand"] == "Alpha Brand" for r in rows)

    # 2. Unauthorized Foreign Brand Export -> 403 Forbidden
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=brand&filter_id={data['brand2'].id}")
    assert resp.status_code == 403
    assert "Brand users can only export their own brand" in resp.text

    # 3. Unauthorized Views -> 403 Forbidden
    for v in ["company", "pod", "process", "employee"]:
        resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type={v}")
        assert resp.status_code == 403


# =====================================================================
# 4. RBAC & Object-Level Scoping: Employee
# =====================================================================

def test_employee_scoping_rules(client: TestClient, export_test_fixture):
    data = export_test_fixture
    r_id = data["roster"].id

    login(client, data["u_emp_alice"].email)

    # 1. Authorized Self Export -> Success
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=employee&filter_id={data['emp_a1'].id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 30
    assert all(r["Employee Name"] == "Alice Alpha" for r in rows)

    # 2. Unauthorized Foreign Employee Export -> 403 Forbidden
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=employee&filter_id={data['emp_b1'].id}")
    assert resp.status_code == 403
    assert "Employees can only export their own assignments" in resp.text

    # 3. Unauthorized Views -> 403 Forbidden
    for v in ["company", "pod", "brand", "process"]:
        resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type={v}")
        assert resp.status_code == 403


# =====================================================================
# 5. Direct API Access Without Auth, Malformed Filters, Invalid IDs
# =====================================================================

def test_export_security_and_edge_cases(client: TestClient, export_test_fixture):
    data = export_test_fixture
    r_id = data["roster"].id

    # 1. Unauthenticated -> 401 Unauthorized
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv")
    assert resp.status_code == 401

    # Login as admin
    login(client, data["u_admin"].email)

    # 2. Invalid Roster UUID (not in DB) -> 404 Not Found
    random_id = uuid.uuid4()
    resp = client.get(f"/api/v1/rosters/{random_id}/export/csv")
    assert resp.status_code == 404

    # 3. Malformed UUID string in path -> 422 Unprocessable Entity
    resp = client.get("/api/v1/rosters/not-a-valid-uuid/export/csv")
    assert resp.status_code == 422

    # 4. Invalid View Type -> 422 Unprocessable Entity
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=invalid_view")
    assert resp.status_code == 422

    # 5. Empty Dataset Handling: Filter by a non-existent pod UUID -> Valid CSV with 0 data rows
    empty_pod_id = uuid.uuid4()
    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=pod&filter_id={empty_pod_id}")
    assert resp.status_code == 200
    rows = parse_csv_response(resp)
    assert len(rows) == 0  # Header exists, zero data rows


# =====================================================================
# 6. Verify Column Privacy & Published Data Immutability
# =====================================================================

def test_export_privacy_and_data_immutability(client: TestClient, export_test_fixture, db_session: Session):
    data = export_test_fixture
    r_id = data["roster"].id
    login(client, data["u_admin"].email)

    resp = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=company")
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")

    # Verify no sensitive keywords or passwords leaked
    assert "password" not in content.lower()
    assert "secret" not in content.lower()
    assert "token" not in content.lower()
    assert "hash" not in content.lower()

    # Verify standard columns
    first_line = content.split("\r\n")[0]
    expected_headers = [
        "Date", "Day of Week", "Pod", "Employee Code", "Employee Name",
        "Brand", "Process", "Shift Start", "Shift End", "Allocation Start",
        "Allocation End", "Allocation Status", "Cross-Pod Approved", "Reassigned From"
    ]
    for h in expected_headers:
        assert h in first_line

    # Verify underlying database published roster record is completely unchanged
    roster_db = db_session.get(Roster, r_id)
    assert roster_db.status == RosterStatus.PUBLISHED
    assert roster_db.version == 1
    assert roster_db.config_hash == "test_export_hash_123"


# =====================================================================
# 7. CSV Formula Injection Defense & Dataset Consistency
# =====================================================================

def test_csv_formula_injection_defense_all_prefixes():
    from app.modules.roster.router import sanitize_csv_cell, serialize_dataset_to_csv

    # 1. Unit Test sanitize_csv_cell for every prefix
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert sanitize_csv_cell("+100") == "'+100"
    assert sanitize_csv_cell("-50") == "'-50"
    assert sanitize_csv_cell("-") == "'-"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\tindented") == "'\tindented"
    assert sanitize_csv_cell("\rcarriage") == "'\rcarriage"

    # Normal values remain completely untouched
    assert sanitize_csv_cell("Alice Alpha") == "Alice Alpha"
    assert sanitize_csv_cell("2026-11-01") == "2026-11-01"
    assert sanitize_csv_cell("PRIMARY") == "PRIMARY"
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell(None) == ""
    assert sanitize_csv_cell(123) == "123"

    # 2. Integration Test serialize_dataset_to_csv
    fieldnames = ["PrefixType", "Value", "Notes"]
    rows = [
        {"PrefixType": "Equals", "Value": "=2+5", "Notes": "formula equal"},
        {"PrefixType": "Plus", "Value": "+99", "Notes": "formula plus"},
        {"PrefixType": "Minus", "Value": "-42", "Notes": "formula minus"},
        {"PrefixType": "At", "Value": "@AVG(B1:B5)", "Notes": "formula at"},
        {"PrefixType": "Tab", "Value": "\tLeadingTab", "Notes": "formula tab"},
        {"PrefixType": "CR", "Value": "\rLeadingCR", "Notes": "formula cr"},
        {"PrefixType": "Normal", "Value": "Standard Text", "Notes": "normal text"},
        {"PrefixType": "Escaped", "Value": 'Text with "Quotes" and , comma', "Notes": "escaped text"},
        {"PrefixType": "Unicode", "Value": "Üñîçødé 🚀 Team", "Notes": "multilingual text"},
    ]

    csv_bytes = serialize_dataset_to_csv(fieldnames, rows)

    # Verify UTF-8 BOM
    assert csv_bytes.startswith(b"\xef\xbb\xbf")

    # Decode and parse
    csv_text = csv_bytes.decode("utf-8-sig")
    parsed_rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(parsed_rows) == 9

    # Verify protected prefixes
    assert parsed_rows[0]["Value"] == "'=2+5"
    assert parsed_rows[1]["Value"] == "'+99"
    assert parsed_rows[2]["Value"] == "'-42"
    assert parsed_rows[3]["Value"] == "'@AVG(B1:B5)"
    assert parsed_rows[4]["Value"] == "'\tLeadingTab"
    assert parsed_rows[5]["Value"] == "'\rLeadingCR"

    # Verify normal, escaped and unicode values
    assert parsed_rows[6]["Value"] == "Standard Text"
    assert parsed_rows[7]["Value"] == 'Text with "Quotes" and , comma'
    assert parsed_rows[8]["Value"] == "Üñîçødé 🚀 Team"


def test_csv_and_google_sheets_dataset_consistency(client: TestClient, export_test_fixture, db_session: Session):
    data = export_test_fixture
    r_id = data["roster"].id
    login(client, data["u_admin"].email)

    # 1. Fetch CSV export
    resp_csv = client.get(f"/api/v1/rosters/{r_id}/export/csv?view_type=company")
    assert resp_csv.status_code == 200
    csv_rows = parse_csv_response(resp_csv)

    # 2. Extract shared dataset directly
    from app.modules.roster.router import extract_roster_export_dataset
    roster, fieldnames, raw_rows = extract_roster_export_dataset(
        roster_id=r_id,
        view_type="company",
        filter_id=None,
        db=db_session,
        _user=data["u_admin"],
    )

    # Both datasets have identical row counts
    assert len(csv_rows) == len(raw_rows) == 90

    # For each row, non-formula values match identically
    for csv_r, raw_r in zip(csv_rows, raw_rows):
        assert csv_r["Date"] == raw_r["Date"]
        assert csv_r["Employee Name"] == raw_r["Employee Name"]
        assert csv_r["Employee Code"] == raw_r["Employee Code"]
        assert csv_r["Pod"] == raw_r["Pod"]
        # Database entities remain completely unmutated
        assert not raw_r["Employee Name"].startswith("'")

    # Verify underlying database entities were not modified
    emp = db_session.get(Employee, data["emp_a1"].id)
    assert emp.name == "Alice Alpha"
    assert not emp.name.startswith("'")

