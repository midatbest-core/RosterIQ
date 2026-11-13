"""
Database Cleanup Script for RosterIQ.
Removes old runs, test employees, and unneeded test pods/brands.
Preserves:
- November 2026 Production Roster (Published versions 1 and 2)
- December 2026 Production Roster (Published version 1 and Recent December Work version 2)
"""

import sys
sys.path.insert(0, 'backend')

from uuid import UUID
from app.db.session import SessionLocal
from app.modules.roster.models import Roster, RosterStatus, RosterAllocation, EmployeeShift, RosterConflict
from app.modules.workforce.models import Employee, Pod, EmployeeProcessSkill
from app.modules.workforce.availability_models import EmployeeUnavailability
from app.modules.operations.models import Brand, PrimaryAssignment, BrandProcess
from app.modules.auth.models import User


def run_cleanup():
    db = SessionLocal()
    try:
        # 1. Roster IDs to keep
        KEEP_ROSTER_IDS = {
            UUID('883b27a7-02a2-4323-b99f-6652186d5b02'),  # Nov 2026 (v1) PUBLISHED
            UUID('8ce28e3d-bd7d-4665-926e-01f3b4da386f'),  # Nov 2026 (v2) PUBLISHED
            UUID('6078d9a2-e8b9-4910-a1c4-3c21a6ba6ef8'),  # Dec 2026 (v1) PUBLISHED
            UUID('72cd979b-e285-468c-b275-38bf4536911e'),  # Dec 2026 (v2) Recent Work
        }

        all_rosters = db.query(Roster).all()
        rosters_to_delete = [r for r in all_rosters if r.id not in KEEP_ROSTER_IDS]
        delete_ids = [r.id for r in rosters_to_delete]

        print(f"Found {len(rosters_to_delete)} old/stale rosters to delete...")

        if delete_ids:
            # Delete child allocations, shifts, conflicts
            del_allocs = db.query(RosterAllocation).filter(RosterAllocation.roster_id.in_(delete_ids)).delete(synchronize_session=False)
            del_shifts = db.query(EmployeeShift).filter(EmployeeShift.roster_id.in_(delete_ids)).delete(synchronize_session=False)
            del_conflicts = db.query(RosterConflict).filter(RosterConflict.roster_id.in_(delete_ids)).delete(synchronize_session=False)

            # Delete the rosters
            del_rosters = db.query(Roster).filter(Roster.id.in_(delete_ids)).delete(synchronize_session=False)
            print(f"Deleted: {del_rosters} rosters, {del_allocs} allocations, {del_shifts} shifts, {del_conflicts} conflicts.")

        # Clean up preserved roster names and versions
        r_nov1 = db.get(Roster, UUID('883b27a7-02a2-4323-b99f-6652186d5b02'))
        if r_nov1:
            r_nov1.name = "November 2026 Production Roster"
            r_nov1.version = 1
            r_nov1.status = RosterStatus.PUBLISHED

        r_nov2 = db.get(Roster, UUID('8ce28e3d-bd7d-4665-926e-01f3b4da386f'))
        if r_nov2:
            r_nov2.name = "November 2026 Production Roster"
            r_nov2.version = 2
            r_nov2.status = RosterStatus.PUBLISHED

        r_dec1 = db.get(Roster, UUID('6078d9a2-e8b9-4910-a1c4-3c21a6ba6ef8'))
        if r_dec1:
            r_dec1.name = "December 2026 Production Roster"
            r_dec1.version = 1
            r_dec1.status = RosterStatus.PUBLISHED

        r_dec2 = db.get(Roster, UUID('72cd979b-e285-468c-b275-38bf4536911e'))
        if r_dec2:
            r_dec2.name = "December 2026 Production Roster"
            r_dec2.version = 2
            r_dec2.status = RosterStatus.DRAFT

        # 2. Delete test employees: aditya (EMP55), demo (EMP56), rohit (EMP57), botemp (EMP001)
        test_emps = db.query(Employee).filter(
            Employee.employee_code.in_(['EMP55', 'EMP56', 'EMP57', 'EMP001'])
        ).all()
        test_emp_ids = [e.id for e in test_emps]
        print(f"Found {len(test_emps)} test employees to delete: {[e.name for e in test_emps]}")

        if test_emp_ids:
            # Delete child allocations, shifts, skills, unavailabilities, primary assignments
            db.query(RosterAllocation).filter(RosterAllocation.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeShift).filter(EmployeeShift.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(RosterConflict).filter(RosterConflict.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeProcessSkill).filter(EmployeeProcessSkill.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(EmployeeUnavailability).filter(EmployeeUnavailability.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(PrimaryAssignment).filter(PrimaryAssignment.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.employee_id.in_(test_emp_ids)).delete(synchronize_session=False)
            db.query(Employee).filter(Employee.id.in_(test_emp_ids)).delete(synchronize_session=False)
            print(f"Deleted {len(test_emp_ids)} test employee records and associated accounts.")

        # 3. Delete NEW POD
        new_pods = db.query(Pod).filter(Pod.name.ilike('%NEW POD%')).all()
        for p in new_pods:
            # Detach any employees
            db.query(Employee).filter(Employee.pod_id == p.id).update({'pod_id': None}, synchronize_session=False)
            db.query(User).filter(User.pod_id == p.id).update({'pod_id': None}, synchronize_session=False)
            db.delete(p)
            print(f"Deleted pod '{p.name}'.")

        # 4. Delete any brand matching 'NEW BRAND'
        new_brands = db.query(Brand).filter(Brand.name.ilike('%NEW BRAND%')).all()
        for b in new_brands:
            bps = db.query(BrandProcess).filter(BrandProcess.brand_id == b.id).all()
            bp_ids = [bp.id for bp in bps]
            if bp_ids:
                db.query(PrimaryAssignment).filter(PrimaryAssignment.brand_process_id.in_(bp_ids)).delete(synchronize_session=False)
                db.query(RosterAllocation).filter(RosterAllocation.brand_process_id.in_(bp_ids)).delete(synchronize_session=False)
                db.query(BrandProcess).filter(BrandProcess.id.in_(bp_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.brand_id == b.id).update({'brand_id': None}, synchronize_session=False)
            db.delete(b)
            print(f"Deleted brand '{b.name}'.")

        db.commit()
        print("Cleanup successfully committed!")

        # Verify final state
        remaining_rosters = db.query(Roster).all()
        print("\nREMAINING ROSTERS:")
        for r in remaining_rosters:
            print(f"  - {r.name} (v{r.version}) [{r.month}/{r.year}] — {r.status.value}")

        remaining_emps = db.query(Employee).all()
        print(f"\nREMAINING ACTIVE EMPLOYEES: {len(remaining_emps)}")

    except Exception as e:
        db.rollback()
        print("Error during cleanup:", e)
        raise
    finally:
        db.close()


if __name__ == '__main__':
    run_cleanup()
