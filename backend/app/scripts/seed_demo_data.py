from __future__ import annotations

from datetime import date, time
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import (
    Brand,
    BrandProcess,
    Holiday,
    HolidayBehavior,
    HolidayCalendar,
    PrimaryAssignment,
    Process,
    RecordStatus,
)
from app.modules.operations.pattern_models import (
    OperatingOverride,
    OperatingPattern,
)
from app.modules.workforce.availability_models import (
    AbsenceReasonType,
    EmployeePreference,
    EmployeeUnavailability,
)
from app.modules.workforce.models import (
    Employee,
    EmployeeProcessSkill,
    EmployeeStatus,
    Pod,
    PodLead,
    SkillProficiency,
)


def seed_data() -> None:
    print("🌱 Starting RosterIQ deterministic seed data generation...")

    with SessionLocal() as db:
        # 1. Admin & Operations Manager Users
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        if not admin:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("AdminPass123!"),
                role=UserRole.ADMIN,
            )
            db.add(admin)

        ops = db.scalar(select(User).where(User.email == "ops@example.com"))
        if not ops:
            ops = User(
                email="ops@example.com",
                password_hash=hash_password("OpsManager123!"),
                role=UserRole.OPERATIONS_MANAGER,
            )
            db.add(ops)
        db.flush()

        # 2. Holiday Calendar & Indian Public Holidays
        cal = db.scalar(select(HolidayCalendar).where(HolidayCalendar.name == "India National Calendar"))
        if not cal:
            cal = HolidayCalendar(name="India National Calendar", region="India")
            db.add(cal)
            db.flush()

            holidays = [
                (date(2026, 1, 26), "Republic Day"),
                (date(2026, 8, 15), "Independence Day"),
                (date(2026, 10, 2), "Gandhi Jayanti"),
                (date(2026, 11, 9), "Diwali (Deepavali)"),
                (date(2026, 11, 10), "Diwali Govardhan Puja"),
                (date(2026, 12, 25), "Christmas Day"),
            ]
            for h_date, h_name in holidays:
                db.add(Holiday(holiday_calendar_id=cal.id, date=h_date, name=h_name))
            db.flush()

        # 3. Core Operational Processes
        processes_data = [
            ("CS", "Customer Support", "Inbound omnichannel customer support via chat, email, phone"),
            ("ACC", "Abandoned Cart Conversions", "Outbound high-intent abandoned checkout recovery"),
            ("NDR", "Non-Delivery Report Management", "Logistics NDR follow-up, re-attempt coordination"),
            ("RETENTION", "Customer Retention", "Proactive subscriber engagement and churn mitigation"),
            ("ESCALATIONS", "L2 Escalations & Grievance", "Priority grievance and executive resolution"),
        ]
        proc_map: dict[str, Process] = {}
        for code, name, desc in processes_data:
            p = db.scalar(select(Process).where(Process.code == code))
            if not p:
                p = Process(code=code, name=name, description=desc, status=RecordStatus.ACTIVE)
                db.add(p)
                db.flush()
            proc_map[code] = p

        # 4. Pods
        pods_data = [
            "Pod Alpha - Fast Fashion & Apparel",
            "Pod Beta - Beauty & Personal Care",
            "Pod Gamma - Health & Nutrition",
            "Pod Delta - Electronics & Home",
        ]
        pod_map: dict[str, Pod] = {}
        for pod_name in pods_data:
            pod = db.scalar(select(Pod).where(Pod.name == pod_name))
            if not pod:
                pod = Pod(name=pod_name, is_active=True)
                db.add(pod)
                db.flush()
            pod_map[pod_name] = pod

        # 5. Employees (32 realistic employees across the 4 pods)
        employees_spec = [
            # Pod Alpha (8)
            ("EMP-001", "Aarav Sharma", "aarav@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", True),
            ("EMP-002", "Diya Patel", "diya@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-003", "Rohan Verma", "rohan@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-004", "Ananya Iyer", "ananya@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-005", "Kabir Mehta", "kabir@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-006", "Ishita Roy", "ishita@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-007", "Vikram Sen", "vikram@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-008", "Tanvi Nair", "tanvi@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            # Pod Beta (8)
            ("EMP-009", "Pooja Hegde", "pooja@datastraw.io", "Pod Beta - Beauty & Personal Care", True),
            ("EMP-010", "Siddharth Rao", "siddharth@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            ("EMP-011", "Meera Joshi", "meera@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            ("EMP-012", "Aditya Deshmukh", "aditya@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            ("EMP-013", "Kavya Menon", "kavya@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            ("EMP-014", "Nikhil Pillai", "nikhil@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            ("EMP-015", "Sneha Kulkarni", "sneha@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            ("EMP-016", "Arjun Nambiar", "arjun@datastraw.io", "Pod Beta - Beauty & Personal Care", False),
            # Pod Gamma (8)
            ("EMP-017", "Gaurav Malhotra", "gaurav@datastraw.io", "Pod Gamma - Health & Nutrition", True),
            ("EMP-018", "Neha Reddy", "neha@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-019", "Rahul Bose", "rahul@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-020", "Priya Dasgupta", "priya@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-021", "Manish Choudhury", "manish@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-022", "Rhea Sengupta", "rhea@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-023", "Varun Bhatia", "varun@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-024", "Simran Gill", "simran@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            # Pod Delta (8)
            ("EMP-025", "Devansh Kapoor", "devansh@datastraw.io", "Pod Delta - Electronics & Home", True),
            ("EMP-026", "Tara Sundaram", "tara@datastraw.io", "Pod Delta - Electronics & Home", False),
            ("EMP-027", "Yash Singhal", "yash@datastraw.io", "Pod Delta - Electronics & Home", False),
            ("EMP-028", "Bhavna Chawla", "bhavna@datastraw.io", "Pod Delta - Electronics & Home", False),
            ("EMP-029", "Karan Bansal", "karan@datastraw.io", "Pod Delta - Electronics & Home", False),
            ("EMP-030", "Swati Saxena", "swati@datastraw.io", "Pod Delta - Electronics & Home", False),
            ("EMP-031", "Harsh Agarwal", "harsh@datastraw.io", "Pod Delta - Electronics & Home", False),
            ("EMP-032", "Zoya Mirza", "zoya@datastraw.io", "Pod Delta - Electronics & Home", False),
            # Additional Capacity (4 specialized employees to guarantee full 590+ shift host capacity)
            ("EMP-033", "Karan Malhotra", "karan.m@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-034", "Meera Kapoor", "meera.k@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
            ("EMP-035", "Nikhil Joshi", "nikhil.j@datastraw.io", "Pod Gamma - Health & Nutrition", False),
            ("EMP-036", "Sneha Reddy", "sneha.r@datastraw.io", "Pod Alpha - Fast Fashion & Apparel", False),
        ]

        emp_map: dict[str, Employee] = {}
        for code, name, email, pod_name, is_lead in employees_spec:
            emp = db.scalar(select(Employee).where(Employee.employee_code == code))
            if not emp:
                pod = pod_map[pod_name]
                emp = Employee(
                    employee_code=code,
                    name=name,
                    email=email,
                    pod_id=pod.id,
                    daily_capacity_minutes=540,
                    standard_start_time=time(9, 0),
                    standard_end_time=time(18, 0),
                    status=EmployeeStatus.ACTIVE,
                )
                db.add(emp)
                db.flush()

                # Set Pod Lead if applicable
                if is_lead and not pod.lead:
                    pod_lead = PodLead(pod_id=pod.id, employee_id=emp.id)
                    db.add(pod_lead)
                    db.flush()

                # Add process skills (All employees have CS; many have ACC and NDR)
                db.add(EmployeeProcessSkill(employee_id=emp.id, process_id=proc_map["CS"].id, proficiency=SkillProficiency.ADVANCED))
                db.add(EmployeeProcessSkill(employee_id=emp.id, process_id=proc_map["ACC"].id, proficiency=SkillProficiency.INTERMEDIATE))
                if code in ("EMP-001", "EMP-005", "EMP-009", "EMP-013", "EMP-017", "EMP-021", "EMP-025", "EMP-029", "EMP-033", "EMP-035", "EMP-036"):
                    db.add(EmployeeProcessSkill(employee_id=emp.id, process_id=proc_map["NDR"].id, proficiency=SkillProficiency.ADVANCED))
                    db.add(EmployeeProcessSkill(employee_id=emp.id, process_id=proc_map["RETENTION"].id, proficiency=SkillProficiency.INTERMEDIATE))

                # Default Preferences: Sunday off (6), Saturday off (5)
                db.add(EmployeePreference(employee_id=emp.id, preferred_weekly_off_days="5,6"))

            emp_map[code] = emp
        db.flush()

        # 6. Brands: 15 Brands (~80% single-resource: 12 brands; ~20% multi-resource: 3 brands)
        brands_data = [
            # 12 Single-Resource Brands (Sole dedicated employee handles all assigned processes)
            ("KAVYA", "Kavya Organic Skincare", "EMP-002", ["CS", "ACC"]),
            ("URBAN", "Urban Loom Casuals", "EMP-003", ["CS"]),
            ("CHAI", "BlueTokai Chai & Roast", "EMP-004", ["CS", "ACC"]),
            ("SNACK", "YogaBar Snacks", "EMP-006", ["CS"]),
            ("GLOW", "Earth Rhythm Cosmetics", "EMP-010", ["CS", "ACC"]),
            ("SLEEP", "SleepyCat Mattresses", "EMP-011", ["CS"]),
            ("BEAT", "Noise Audio Gears", "EMP-012", ["CS", "ACC"]),
            ("FIT", "Oziva Clean Nutrition", "EMP-014", ["CS"]),
            ("BREW", "Sleepy Owl Coffee", "EMP-018", ["CS", "ACC"]),
            ("HERB", "Kapiva Ayurveda", "EMP-019", ["CS"]),
            ("CHEW", "Supertails Pet Supplies", "EMP-026", ["CS", "ACC"]),
            ("TECH", "Portronics Tech Gadgets", "EMP-027", ["CS"]),
            # 3 Multi-Resource Brands (2-3 employees distributed by process)
            ("BOMBAY", "Bombay Shaving Company", None, ["CS", "ACC", "NDR"]),
            ("BOAT", "boAt Lifestyle Audio", None, ["CS", "ACC", "RETENTION"]),
            ("MAMA", "Mamaearth Natural Care", None, ["CS", "ACC", "NDR"]),
        ]

        bp_map: dict[tuple[str, str], BrandProcess] = {}

        for b_code, b_name, sole_emp_code, proc_codes in brands_data:
            brand = db.scalar(select(Brand).where(Brand.code == b_code))
            if not brand:
                brand = Brand(code=b_code, name=b_name, status=RecordStatus.ACTIVE)
                db.add(brand)
                db.flush()

            for p_code in proc_codes:
                proc = proc_map[p_code]
                bp = db.scalar(
                    select(BrandProcess).where(
                        BrandProcess.brand_id == brand.id,
                        BrandProcess.process_id == proc.id,
                    )
                )
                if not bp:
                    # Operating Rule Variety
                    if b_code in ("BOAT", "BOMBAY") and p_code == "CS":
                        # 365 Days including Sundays
                        h_behav = HolidayBehavior.NORMAL
                        op_days = "0,1,2,3,4,5,6"
                        min_weekday, min_weekend = 2, 2
                    elif p_code == "ACC":
                        # Mon-Sat, Sunday off
                        h_behav = HolidayBehavior.REDUCED
                        op_days = "0,1,2,3,4,5"
                        min_weekday, min_weekend = 1, 1
                    else:
                        # Mon-Fri, weekends off, holidays closed
                        h_behav = HolidayBehavior.CLOSED
                        op_days = "0,1,2,3,4"
                        min_weekday, min_weekend = 1, 0

                    bp = BrandProcess(
                        brand_id=brand.id,
                        process_id=proc.id,
                        holiday_calendar_id=cal.id,
                        holiday_behavior=h_behav,
                        holiday_min_employees=1 if h_behav == HolidayBehavior.REDUCED else None,
                        is_active=True,
                    )
                    db.add(bp)
                    db.flush()

                    # Create Operating Pattern
                    op_pattern = OperatingPattern(
                        brand_process_id=bp.id,
                        operating_days=op_days,
                        start_time=time(9, 0),
                        end_time=time(18, 0),
                        min_staffing_weekday=min_weekday,
                        min_staffing_weekend=min_weekend,
                        holiday_behavior=h_behav,
                        min_staffing_holiday=1 if h_behav == HolidayBehavior.REDUCED else 0,
                    )
                    db.add(op_pattern)

                bp_map[(b_code, p_code)] = bp

                # Primary Assignments
                if sole_emp_code:
                    emp = emp_map[sole_emp_code]
                    if not db.scalar(select(PrimaryAssignment).where(PrimaryAssignment.employee_id == emp.id, PrimaryAssignment.brand_process_id == bp.id)):
                        db.add(PrimaryAssignment(employee_id=emp.id, brand_process_id=bp.id, effective_from=date(2026, 1, 1), priority=1))

        # Multi-resource primary assignments
        multi_assignments = [
            # Bombay Shaving Company
            ("BOMBAY", "CS", "EMP-001"),
            ("BOMBAY", "CS", "EMP-005"),
            ("BOMBAY", "ACC", "EMP-007"),
            ("BOMBAY", "NDR", "EMP-008"),
            # boAt Lifestyle
            ("BOAT", "CS", "EMP-017"),
            ("BOAT", "CS", "EMP-020"),
            ("BOAT", "ACC", "EMP-021"),
            ("BOAT", "RETENTION", "EMP-022"),
            ("BOAT", "RETENTION", "EMP-035"),
            # Bombay NDR reinforcement
            ("BOMBAY", "NDR", "EMP-033"),
            # YogaBar reinforcement
            ("SNACK", "CS", "EMP-034"),
            # Mamaearth
            ("MAMA", "CS", "EMP-025"),
            ("MAMA", "ACC", "EMP-028"),
            ("MAMA", "NDR", "EMP-029"),
        ]
        for b_code, p_code, e_code in multi_assignments:
            bp = bp_map.get((b_code, p_code))
            emp = emp_map.get(e_code)
            if bp and emp:
                if not db.scalar(select(PrimaryAssignment).where(PrimaryAssignment.employee_id == emp.id, PrimaryAssignment.brand_process_id == bp.id)):
                    db.add(PrimaryAssignment(employee_id=emp.id, brand_process_id=bp.id, effective_from=date(2026, 1, 1), priority=1))

        # 7. Date-Specific Override Scenario
        # Flash Sale Surge on Kavya Organics (Nov 15 Sunday: usually closed, but override demands 2 staff)
        kavya_cs_bp = bp_map.get(("KAVYA", "CS"))
        if kavya_cs_bp:
            override_date = date(2026, 11, 15)
            if not db.scalar(select(OperatingOverride).where(OperatingOverride.brand_process_id == kavya_cs_bp.id, OperatingOverride.date == override_date)):
                db.add(
                    OperatingOverride(
                        brand_process_id=kavya_cs_bp.id,
                        date=override_date,
                        is_closed=False,
                        override_start_time=time(10, 0),
                        override_end_time=time(16, 0),
                        override_min_staffing=2,
                        reason="Kavya Diwali Super Sale Surge",
                    )
                )

        # 8. Realistic Approved Leaves (Demonstrating Section 4.F Assessment Scenario)
        # Diya Patel (EMP-002, sole employee of Kavya Organics) takes approved medical leave Nov 4 to Nov 6
        sole_emp = emp_map.get("EMP-002")
        if sole_emp:
            for l_day in (4, 5, 6):
                l_date = date(2026, 11, l_day)
                if not db.scalar(select(EmployeeUnavailability).where(EmployeeUnavailability.employee_id == sole_emp.id, EmployeeUnavailability.date == l_date)):
                    db.add(
                        EmployeeUnavailability(
                            employee_id=sole_emp.id,
                            date=l_date,
                            reason_type=AbsenceReasonType.SICK_LEAVE,
                            is_approved=True,
                            notes="Medical leave (fracture recovery)",
                        )
                    )

        # Another employee (EMP-007) takes planned comp-off on Nov 12
        comp_off_emp = emp_map.get("EMP-007")
        if comp_off_emp:
            co_date = date(2026, 11, 12)
            if not db.scalar(select(EmployeeUnavailability).where(EmployeeUnavailability.employee_id == comp_off_emp.id, EmployeeUnavailability.date == co_date)):
                db.add(
                    EmployeeUnavailability(
                        employee_id=comp_off_emp.id,
                        date=co_date,
                        reason_type=AbsenceReasonType.COMP_OFF,
                        is_approved=True,
                        notes="Comp-off for weekend deployment",
                    )
                )

        db.commit()
        print("✅ Seed data generation complete: 32 employees, 4 pods, 15 brands (12 single-resource, 3 multi-resource), operating patterns, overrides, and leaves initialized.")


if __name__ == "__main__":
    seed_data()

