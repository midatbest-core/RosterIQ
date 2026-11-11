from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("\n--- 1. Authenticating Admin User ---")
login_res = client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'AdminPass123!'})
print("Login status:", login_res.status_code, login_res.json()["user"]["email"])

csrf_token = client.cookies.get('csrf_token')
headers = {'X-CSRF-Token': csrf_token}

print("\n--- 2. Verifying Seeded Master Data ---")
emps = client.get('/api/v1/employees').json()
pods = client.get('/api/v1/pods').json()
brands = client.get('/api/v1/brands').json()
bps = client.get('/api/v1/brand-processes').json()
print(f"Loaded: {len(emps)} Employees, {len(pods)} Pods, {len(brands)} Brands, {len(bps)} Brand-Processes.")
assert len(emps) >= 30, "Must have at least 30 employees"

print("\n--- 3. Deterministic Roster Generation (Nov 2026) ---")
gen_res = client.post(
    '/api/v1/rosters/generate',
    json={'name': 'Nov 2026 Production Roster', 'month': 11, 'year': 2026},
    headers=headers,
)
assert gen_res.status_code == 201
roster = gen_res.json()
roster_id = roster['id']
print(f"Generated Roster: '{roster['name']}' (v{roster['version']})")
print(f"Shifts: {roster['total_shifts']} | Allocations: {roster['total_allocations']} | Hard Conflicts: {roster['hard_violations_count']}")

print("\n--- 4. Validating All 5 Required Viewing Modes ---")
for mode in ['company', 'pod', 'brand', 'process', 'employee']:
    grid_res = client.get(f'/api/v1/rosters/{roster_id}/grid?view_type={mode}')
    assert grid_res.status_code == 200
    grid = grid_res.json()
    print(f"Mode [{mode:8}]: {len(grid['rows']):2} rows rendered across {len(grid['dates'])} calendar days.")

print("\n--- 5. Detecting Expected Conflicts (Assessment Scenario 4.F) ---")
grid = client.get(f'/api/v1/rosters/{roster_id}/grid?view_type=company').json()
conflicts = grid['summary_conflicts']
print(f"Total conflicts detected: {len(conflicts)}")
for c in conflicts[:3]:
    print(f" - [{c['conflict_type']}] on {c['date']}: {c['description']}")

print("\n--- 6. Reassignment Workflow: Finding Backup Candidates ---")
kavya_brand = [b for b in brands if b["code"] == "KAVYA"][0]
kavya_bp = [bp for bp in bps if bp["brand_id"] == kavya_brand["id"]][0]
kavya_bp_id = kavya_bp["id"]

candidates = client.get(
    f'/api/v1/rosters/{roster_id}/backup-candidates?brand_process_id={kavya_bp_id}&target_date=2026-11-04&start_time=09:00:00&end_time=18:00:00'
).json()
print(f"Found {len(candidates)} backup candidates for Kavya CS on 2026-11-04:")
top_cand = candidates[0]
print(f"Top candidate: {top_cand['name']} (Same Pod: {top_cand['is_same_pod']}, Requires Approval: {top_cand['requires_approval']})")

print("\n--- 7. Applying Authorized Reassignment ---")
reassign_res = client.post(
    f'/api/v1/rosters/{roster_id}/reassign/apply',
    json={
        'date': '2026-11-04',
        'brand_process_id': kavya_bp_id,
        'start_time': '09:00:00',
        'end_time': '18:00:00',
        'target_employee_id': top_cand['employee_id'],
        'reason': 'Cover Diya Patel approved medical absence',
        'confirm_cross_pod_approval': True,
    },
    headers=headers,
)
assert reassign_res.status_code == 201
print("Reassignment applied successfully:", reassign_res.json())

print("\n--- 8. Verifying Persistence on Database ---")
updated_grid = client.get(f'/api/v1/rosters/{roster_id}/grid?view_type=brand').json()
kavya_row = [r for r in updated_grid['rows'] if kavya_brand['name'] in r['title']][0]
nov4_cell = kavya_row['days']['2026-11-04']
print(f"Allocations in Kavya row on 2026-11-04: {len(nov4_cell['allocations'])}")
assert len(nov4_cell['allocations']) > 0
print("Allocated employee:", nov4_cell['allocations'][0]['employee_name'], f"({nov4_cell['allocations'][0]['allocation_type']})")

print("\n--- 9. Spawning Child Roster Version ---")
child_res = client.post(f'/api/v1/rosters/{roster_id}/create-child-version', headers=headers)
assert child_res.status_code == 200
child = child_res.json()
print(f"Spawned child version: '{child['name']}' (v{child['version']}), Status: {child['status']}")

print("\n🎉 ALL 9 END-TO-END WORKFLOWS VERIFIED SUCCESSFULLY!")
