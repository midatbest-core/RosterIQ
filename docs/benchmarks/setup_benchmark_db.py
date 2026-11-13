import sys
import os
import uuid
from datetime import date, time as dtime

sys.path.insert(0, os.path.abspath("backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.core.security import hash_password
from app.modules.auth.models import User, UserRole
from app.modules.auth.notification_models import Notification
from app.modules.workforce.models import Pod, Employee, PodLead
from app.modules.operations.models import Brand, Process, BrandProcess, HolidayCalendar, Holiday
from app.modules.operations.pattern_models import OperatingPattern
from app.modules.roster.models import Roster, RosterStatus, EmployeeShift, RosterAllocation, AllocationType

BENCH_DB_PATH = os.path.abspath("scratch/benchmarks/bench_isolated.db")
BENCH_DB_URL = f"sqlite+pysqlite:///{BENCH_DB_PATH.replace(os.sep, '/')}"

def setup_bench_database():
    if os.path.exists(BENCH_DB_PATH):
        os.remove(BENCH_DB_PATH)

    engine = create_engine(BENCH_DB_URL, connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    
    with Session() as db:
        pwd = hash_password("BenchSecret123!")
        
        # 1. Pods
        pod_a = Pod(id=uuid.uuid4(), name="Bench Pod Alpha")
        pod_b = Pod(id=uuid.uuid4(), name="Bench Pod Beta")
        db.add_all([pod_a, pod_b])
        db.flush()

        # 2. Employees
        emp_lead = Employee(
            id=uuid.uuid4(),
            employee_code="EMP-L01",
            name="Laura Lead",
            email="lead@bench.io",
            pod_id=pod_a.id,
            daily_capacity_minutes=540,
            standard_start_time=dtime(9, 0),
            standard_end_time=dtime(18, 0),
        )
        emp_regular = Employee(
            id=uuid.uuid4(),
            employee_code="EMP-E01",
            name="Eric Employee",
            email="emp@bench.io",
            pod_id=pod_a.id,
            daily_capacity_minutes=540,
            standard_start_time=dtime(9, 0),
            standard_end_time=dtime(18, 0),
        )
        db.add_all([emp_lead, emp_regular])
        db.flush()

        db.add(PodLead(pod_id=pod_a.id, employee_id=emp_lead.id))

        # 3. Brands and Processes
        brand1 = Brand(id=uuid.uuid4(), name="Bench Solar", code="BSOL")
        brand2 = Brand(id=uuid.uuid4(), name="Bench Health", code="BHLT")
        proc1 = Process(id=uuid.uuid4(), name="Support Tier 1", code="SUP1")
        proc2 = Process(id=uuid.uuid4(), name="Retention", code="RET")
        db.add_all([brand1, brand2, proc1, proc2])
        db.flush()

        bp1 = BrandProcess(id=uuid.uuid4(), brand_id=brand1.id, process_id=proc1.id)
        bp2 = BrandProcess(id=uuid.uuid4(), brand_id=brand2.id, process_id=proc2.id)
        db.add_all([bp1, bp2])
        db.flush()

        # 4. Users (5 Roles)
        u_admin = User(id=uuid.uuid4(), email="admin@bench.io", password_hash=pwd, role=UserRole.ADMIN, is_active=True)
        u_ops = User(id=uuid.uuid4(), email="ops@bench.io", password_hash=pwd, role=UserRole.OPERATIONS_MANAGER, is_active=True)
        u_lead = User(id=uuid.uuid4(), email="lead@bench.io", password_hash=pwd, role=UserRole.POD_LEAD, pod_id=pod_a.id, employee_id=emp_lead.id, is_active=True)
        u_brand = User(id=uuid.uuid4(), email="brand@bench.io", password_hash=pwd, role=UserRole.BRAND_USER, brand_id=brand1.id, is_active=True)
        u_emp = User(id=uuid.uuid4(), email="emp@bench.io", password_hash=pwd, role=UserRole.EMPLOYEE, employee_id=emp_regular.id, pod_id=pod_a.id, is_active=True)
        db.add_all([u_admin, u_ops, u_lead, u_brand, u_emp])
        db.flush()

        # 5. Roster
        roster = Roster(
            id=uuid.uuid4(),
            name="November 2026 Benchmark Roster",
            month=11,
            year=2026,
            version=1,
            status=RosterStatus.PUBLISHED,
            config_hash="bench_hash_123",
        )
        db.add(roster)
        db.flush()

        # Shifts and Allocations for November 1 to 30
        for d in range(1, 31):
            curr_date = date(2026, 11, d)
            s1 = EmployeeShift(
                id=uuid.uuid4(),
                roster_id=roster.id,
                employee_id=emp_regular.id,
                date=curr_date,
                start_time=dtime(9, 0),
                end_time=dtime(18, 0),
                is_working_day=(d % 7 != 0),
            )
            db.add(s1)
            db.flush()
            if d % 7 != 0:
                a1 = RosterAllocation(
                    id=uuid.uuid4(),
                    roster_id=roster.id,
                    shift_id=s1.id,
                    date=curr_date,
                    brand_process_id=bp1.id,
                    employee_id=emp_regular.id,
                    start_time=dtime(9, 0),
                    end_time=dtime(18, 0),
                    allocation_type=AllocationType.PRIMARY,
                )
                db.add(a1)

        # 6. Notifications
        for u in [u_admin, u_ops, u_lead, u_brand, u_emp]:
            for i in range(5):
                db.add(Notification(
                    id=uuid.uuid4(),
                    user_id=u.id,
                    title=f"Notification {i+1}",
                    message="Roster schedule updated.",
                    notification_type="SYSTEM",
                    is_read=False,
                ))

        roster_id_str = str(roster.id)
        db.commit()

    print(f"Isolated benchmark database created at: {BENCH_DB_PATH}")
    print(f"Roster ID: {roster_id_str}")
    return roster_id_str

if __name__ == "__main__":
    setup_bench_database()
