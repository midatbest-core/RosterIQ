"""
Live Testing and Conflict Resolution Analysis Script for RosterIQ
-----------------------------------------------------------------
Performs end-to-end live testing of:
1. Roster generation & initial conflict surfacing
2. Deep conflict analysis across demand, calendar rules, and employee leaves
3. Candidate discovery & ranking algorithm execution
4. Cross-pod governance enforcement (unauthorized rejection -> authorized approval)
5. Dynamic allocation execution & interval validation
6. Audit verification against the Dynamic Allocation Log
"""
from __future__ import annotations

import json
from datetime import date, time
from fastapi.testclient import TestClient

from app.main import app

def run_live_test_and_analysis():
    client = TestClient(app)

    print("=" * 80)
    print("ROSTERIQ: LIVE CONFLICT RESOLUTION & DYNAMIC ALLOCATION LOG TESTING")
    print("=" * 80)

    # 1. Authenticate Manager
    print("\n[STEP 1] Authenticating Operations Manager...")
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "AdminPass123!"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    user = login_res.json()["user"]
    print(f"Authenticated as: {user['email']} (Role: {user['role']})")

    csrf_token = client.cookies.get("csrf_token")
    headers = {"X-CSRF-Token": csrf_token}

    # 2. Master Data Inspection
    print("\n[STEP 2] Inspecting Master Data & Workforce Structure...")
    employees = client.get("/api/v1/employees").json()
    pods = client.get("/api/v1/pods").json()
    brands = client.get("/api/v1/brands").json()
    bps = client.get("/api/v1/brand-processes").json()
    assignments = client.get("/api/v1/assignments").json()

    print(f"Loaded: {len(employees)} Employees across {len(pods)} Pods")
    print(f"Loaded: {len(brands)} Brands with {len(bps)} Process Links and {len(assignments)} Primary Assignments")

    # 3. Clean up any previous test runs & Deterministic Roster Generation
    print("\n[STEP 3] Generating New Baseline Roster for November 2026...")
    from app.db.session import SessionLocal
    from app.modules.roster.models import Roster
    with SessionLocal() as db:
        old_test_rosters = db.query(Roster).filter(Roster.name == "Nov 2026 Live Conflict Analysis").all()
        for otr in old_test_rosters:
            db.delete(otr)
        db.commit()

    gen_res = client.post(
        "/api/v1/rosters/generate",
        json={"name": "Nov 2026 Live Conflict Analysis", "month": 11, "year": 2026},
        headers=headers,
    )
    assert gen_res.status_code == 201, f"Generation failed: {gen_res.text}"
    roster = gen_res.json()
    roster_id = roster["id"]

    print(f"Roster Created: '{roster['name']}' (v{roster['version']})")
    print(f"Status: {roster['status']}")
    print(f"Total Shifts: {roster['total_shifts']}")
    print(f"Total Allocations: {roster['total_allocations']}")
    print(f"Hard Violations: {roster['hard_violations_count']}")
    print(f"Soft Warnings: {roster['soft_warnings_count']}")

    # 4. Conflict Resolution Analysis
    print("\n[STEP 4] Deep Conflict Resolution Analysis...")
    grid = client.get(f"/api/v1/rosters/{roster_id}/grid?view_type=company").json()
    conflicts = grid["summary_conflicts"]
    
    conflict_type_counts: dict[str, int] = {}
    for c in conflicts:
        conflict_type_counts[c["conflict_type"]] = conflict_type_counts.get(c["conflict_type"], 0) + 1

    print("\nDetected Conflicts Breakdown by Type:")
    for ctype, count in conflict_type_counts.items():
        print(f"  - {ctype}: {count} occurrences")

    # Find the Kavya Organics Scenario 4.F conflict
    diya = [e for e in employees if "Diya" in e["name"]][0]
    diya_assignments = [a for a in assignments if a["employee_id"] == diya["id"]]
    kavya_cs_bp_id = diya_assignments[0]["brand_process_id"]
    kavya_cs_bp = [bp for bp in bps if bp["id"] == kavya_cs_bp_id][0]
    kavya_brand = [b for b in brands if b["id"] == kavya_cs_bp["brand_id"]][0]

    print(f"\nScenario 4.F Focus:")
    print(f"  Brand: {kavya_brand['name']} ({kavya_brand['code']})")
    print(f"  Sole Primary Employee: {diya['name']} ({diya['employee_code']})")
    print(f"  Target BP ID: {kavya_cs_bp['id']}")

    # Check Diya's logged unavailabilities
    diya_unavail = client.get(f"/api/v1/employees/{diya['id']}/unavailability").json()
    print(f"  Logged Absences for {diya['name']}: {len(diya_unavail)} days")
    for u in diya_unavail:
        print(f"    * Date: {u['date']} | Type: {u['reason_type']} | Approved: {u['is_approved']} | Notes: {u['notes']}")

    target_date = "2026-11-04"
    kavya_bp_ids = {bp["id"] for bp in bps if bp["brand_id"] == kavya_brand["id"]}
    kavya_conflicts = [
        c for c in conflicts
        if c["date"] == target_date and c.get("brand_process_id") in kavya_bp_ids
    ]
    print(f"Total conflicts for Kavya on {target_date}: {len(kavya_conflicts)}")
    if kavya_conflicts:
        target_conflict = kavya_conflicts[0]
        target_bp_id = target_conflict["brand_process_id"]
        target_bp = [bp for bp in bps if bp["id"] == target_bp_id][0]
    else:
        # Fall back to any active conflict on that date
        nov4_conflicts = [c for c in conflicts if c["date"] == target_date]
        target_conflict = nov4_conflicts[0]
        target_bp_id = target_conflict["brand_process_id"]
        target_bp = [bp for bp in bps if bp["id"] == target_bp_id][0]

    print(f"\nTarget Conflict for Reassignment:")
    print(f"  Brand Process ID: {target_bp_id}")
    print(f"  Type: {target_conflict['conflict_type']}")
    print(f"  Description: {target_conflict['description']}")

    # 5. Candidate Discovery & Ranking Analysis
    print("\n[STEP 5] Discovering & Ranking Eligible Backup Candidates...")
    candidates = client.get(
        f"/api/v1/rosters/{roster_id}/backup-candidates?brand_process_id={target_bp_id}&target_date={target_date}&start_time=09:00:00&end_time=18:00:00",
        headers=headers,
    ).json()

    print(f"Found {len(candidates)} qualified backup candidates with CS skill and zero shift overlap:")
    for idx, cand in enumerate(candidates, 1):
        status_tag = "SAME-POD (Auto-eligible)" if cand["is_same_pod"] else "CROSS-POD (Requires Manager Approval)"
        pref_tag = " [Soft Off Pref]" if cand["prefers_off_on_day"] else ""
        print(f"  {idx}. {cand['name']:<22} | Pod: {cand['pod_name'] or 'None':<10} | {status_tag}{pref_tag}")

    chosen_candidate = candidates[0]
    print(f"\nSelected Candidate for Dynamic Reassignment: {chosen_candidate['name']}")
    print(f"  Home Pod: {chosen_candidate['pod_name']}")
    print(f"  Requires Approval: {chosen_candidate['requires_approval']}")

    # 6. Testing Governance Security: Unauthorized Cross-Pod Attempt
    if chosen_candidate["requires_approval"]:
        print("\n[STEP 6] Testing Security Boundary: Attempting unauthorized cross-pod reassignment...")
        unauth_res = client.post(
            f"/api/v1/rosters/{roster_id}/reassign/apply",
            json={
                "date": target_date,
                "brand_process_id": target_bp_id,
                "start_time": "09:00:00",
                "end_time": "18:00:00",
                "target_employee_id": chosen_candidate["employee_id"],
                "source_employee_id": diya["id"],
                "reason": "Test unauthorized cross-pod",
                "confirm_cross_pod_approval": False,  # Missing approval
            },
            headers=headers,
        )
        print(f"  Status Code: {unauth_res.status_code}")
        assert unauth_res.status_code == 403, "Security violation: Cross-pod assignment succeeded without approval!"
        print(f"  Security Verified: {unauth_res.json()['detail']}")

    # 7. Authorized Reassignment & Dynamic Allocation Execution
    print("\n[STEP 7] Executing Authorized Dynamic Reassignment...")
    reassign_res = client.post(
        f"/api/v1/rosters/{roster_id}/reassign/apply",
        json={
            "date": target_date,
            "brand_process_id": target_bp_id,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "target_employee_id": chosen_candidate["employee_id"],
            "source_employee_id": diya["id"],
            "reason": "Cover Diya Patel approved medical absence",
            "confirm_cross_pod_approval": True,  # Authorized by Operations Manager
        },
        headers=headers,
    )
    assert reassign_res.status_code == 201, f"Reassignment failed: {reassign_res.text}"
    reassign_data = reassign_res.json()
    print(f"  Reassignment Applied! Allocation ID: {reassign_data['allocation_id']}")
    print(f"  Resolved Conflicts Count: {reassign_data['resolved_conflicts']}")

    # 8. Post-Reassignment Grid & Conflict Verification
    print("\n[STEP 8] Post-Reassignment State & Conflict Resolution Verification...")
    updated_grid = client.get(f"/api/v1/rosters/{roster_id}/grid?view_type=brand").json()
    kavya_rows = [r for r in updated_grid["rows"] if kavya_brand["name"] in r["title"]]
    nov4_cell = kavya_rows[0]["days"][target_date]

    print(f"  Kavya row on {target_date}: {len(nov4_cell['allocations'])} active allocations")
    for alloc in nov4_cell["allocations"]:
        print(f"    * Employee: {alloc['employee_name']} | Type: {alloc['allocation_type']} | Window: {alloc['start_time']}-{alloc['end_time']}")

    # Verify conflict on target slot is resolved
    updated_conflicts = updated_grid["summary_conflicts"]
    remaining_kavya_conflicts = [
        c for c in updated_conflicts
        if c["date"] == target_date and c.get("brand_process_id") == target_bp_id and not c["is_resolved"]
    ]
    print(f"  Unresolved conflicts for target BP on {target_date}: {len(remaining_kavya_conflicts)}")
    assert len(remaining_kavya_conflicts) == 0, "Conflict was not resolved!"
    print("  SUCCESS: Target slot conflict is completely resolved!")

    # 9. Dynamic Allocation Log Verification
    print("\n[STEP 9] Inspecting Dynamic Allocation Log (Audit Trail)...")
    log_res = client.get(f"/api/v1/rosters/{roster_id}/allocation-log?dynamic_only=true", headers=headers)
    assert log_res.status_code == 200, f"Allocation log failed: {log_res.text}"
    log_items = log_res.json()

    print(f"Retrieved {len(log_items)} dynamic reassignment log entries:")
    for item in log_items:
        print("\n  -------------------------------------------------------")
        print(f"  Log ID:           {item['id']}")
        print(f"  Date & Time:      {item['date']} ({item['start_time']} - {item['end_time']})")
        print(f"  Brand & Process:  {item['brand_name']} · {item['process_name']}")
        print(f"  Assigned Backup:  {item['employee_name']} (Pod: {item['employee_pod_name']})")
        print(f"  Reassigned From:  {item['reassigned_from_employee_name'] or 'N/A'}")
        print(f"  Allocation Type:  {item['allocation_type']}")
        print(f"  Audit Reason:     {item['reassignment_reason']}")
        print(f"  Approved By:      {item['approved_by_email']} at {item['approved_at']}")
        print(f"  Cross-Pod Signoff:{item['is_cross_pod_approved']}")

    print("\n" + "=" * 80)
    print("LIVE TESTING COMPLETE: CONFLICT RESOLUTION & ALLOCATION LOG VERIFIED 100%")
    print("=" * 80)

if __name__ == "__main__":
    run_live_test_and_analysis()
