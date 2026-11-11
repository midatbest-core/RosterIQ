from __future__ import annotations

import uuid
from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole
from app.modules.operations.models import (
    Brand,
    BrandProcess,
    HolidayBehavior,
    PrimaryAssignment,
    Process,
    RecordStatus,
)
from app.modules.operations.pattern_models import (
    OperatingOverride,
    OperatingPattern,
)
from app.modules.roster.models import (
    AllocationType,
    ConflictSeverity,
    ConflictType,
    EmployeeShift,
    Roster,
    RosterAllocation,
    RosterConflict,
    RosterStatus,
)
from app.modules.workforce.availability_models import (
    AbsenceReasonType,
    EmployeePreference,
    EmployeeUnavailability,
)
from app.modules.workforce.models import (
    Employee,
    EmployeeStatus,
    Pod,
)


def test_reconciled_models_create_and_relations(db_session: Session) -> None:
    session = db_session

    # 1. Pod & Employee
    pod = Pod(name="Pod Apollo")
    session.add(pod)
    session.flush()

    emp1 = Employee(
        employee_code="EMP-101",
        name="Vikram Seth",
        email="vikram@example.com",
        pod_id=pod.id,
        daily_capacity_minutes=480,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    emp2 = Employee(
        employee_code="EMP-102",
        name="Pooja Hegde",
        email="pooja@example.com",
        pod_id=pod.id,
        daily_capacity_minutes=480,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    session.add_all([emp1, emp2])
    session.flush()

    # 2. Brand & Process
    brand = Brand(code="NOVA", name="Nova Wellness")
    proc_cs = Process(code="CS", name="Customer Support")
    session.add_all([brand, proc_cs])
    session.flush()

    bp_cs = BrandProcess(
        brand_id=brand.id,
        process_id=proc_cs.id,
        holiday_behavior=HolidayBehavior.REDUCED,
        holiday_min_employees=1,
    )
    session.add(bp_cs)
    session.flush()

    # 3. Operating Pattern (Recurring) & Override (Precedence)
    pattern = OperatingPattern(
        brand_process_id=bp_cs.id,
        operating_days="0,1,2,3,4",
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=2,
        min_staffing_weekend=0,
        holiday_behavior=HolidayBehavior.REDUCED,
        min_staffing_holiday=1,
    )
    override = OperatingOverride(
        brand_process_id=bp_cs.id,
        date=date(2026, 11, 15),
        is_closed=True,
        reason="System Maintenance",
    )
    session.add_all([pattern, override])
    session.flush()

    # 4. Availability & Preference
    unavail = EmployeeUnavailability(
        employee_id=emp1.id,
        date=date(2026, 11, 20),
        reason_type=AbsenceReasonType.PLANNED_LEAVE,
        is_approved=True,
        notes="Medical checkup",
    )
    pref = EmployeePreference(
        employee_id=emp1.id,
        preferred_weekly_off_days="0,6",
    )
    session.add_all([unavail, pref])
    session.flush()

    # 5. Primary Assignment
    primary = PrimaryAssignment(
        employee_id=emp1.id,
        brand_process_id=bp_cs.id,
        effective_from=date(2026, 11, 1),
        priority=1,
    )
    session.add(primary)
    session.flush()

    # 6. Roster Tree, Shifts & Non-Overlapping Allocations
    roster_v1 = Roster(
        name="Nov 2026 Roster",
        month=11,
        year=2026,
        version=1,
        status=RosterStatus.DRAFT,
        created_by="Ops Lead",
    )
    session.add(roster_v1)
    session.flush()

    shift1 = EmployeeShift(
        roster_id=roster_v1.id,
        employee_id=emp1.id,
        date=date(2026, 11, 10),
        start_time=time(9, 0),
        end_time=time(18, 0),
        is_working_day=True,
    )
    session.add(shift1)
    session.flush()

    # Allocation within shift
    alloc1 = RosterAllocation(
        roster_id=roster_v1.id,
        shift_id=shift1.id,
        employee_id=emp1.id,
        brand_process_id=bp_cs.id,
        date=date(2026, 11, 10),
        start_time=time(9, 0),
        end_time=time(13, 30),
        allocation_type=AllocationType.PRIMARY,
    )
    session.add(alloc1)

    # Conflict Record
    conflict = RosterConflict(
        roster_id=roster_v1.id,
        date=date(2026, 11, 20),
        brand_process_id=bp_cs.id,
        employee_id=emp1.id,
        severity=ConflictSeverity.HARD_VIOLATION,
        conflict_type=ConflictType.UNAVAILABLE_ALLOCATION,
        description="Employee on approved leave",
    )
    session.add(conflict)
    session.commit()

    # Verify relationships & queries
    saved_roster = session.get(Roster, roster_v1.id)
    assert saved_roster is not None
    assert len(saved_roster.shifts) == 1
    assert len(saved_roster.allocations) == 1
    assert len(saved_roster.conflicts) == 1
    assert saved_roster.shifts[0].employee_id == emp1.id


def test_one_shift_per_employee_per_date_constraint(db_session: Session) -> None:
    session = db_session

    pod = Pod(name="Pod Beta")
    session.add(pod)
    session.flush()

    emp = Employee(
        employee_code="EMP-201",
        name="Sunil Gavaskar",
        email="sunil@example.com",
        pod_id=pod.id,
        daily_capacity_minutes=480,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    session.add(emp)
    session.flush()

    roster = Roster(name="Dec 2026", month=12, year=2026, version=1)
    session.add(roster)
    session.flush()

    shift1 = EmployeeShift(
        roster_id=roster.id,
        employee_id=emp.id,
        date=date(2026, 12, 1),
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    session.add(shift1)
    session.flush()

    # Attempting to add a 2nd shift on the same date for the same employee in this roster
    shift2 = EmployeeShift(
        roster_id=roster.id,
        employee_id=emp.id,
        date=date(2026, 12, 1),
        start_time=time(18, 0),
        end_time=time(22, 0),
    )
    session.add(shift2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_unique_availability_per_employee_date(db_session: Session) -> None:
    session = db_session

    pod = Pod(name="Pod Gamma")
    session.add(pod)
    session.flush()

    emp = Employee(
        employee_code="EMP-301",
        name="Anil Kumble",
        email="anil@example.com",
        pod_id=pod.id,
        daily_capacity_minutes=480,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
    )
    session.add(emp)
    session.flush()

    unavail1 = EmployeeUnavailability(
        employee_id=emp.id,
        date=date(2026, 12, 25),
        reason_type=AbsenceReasonType.PLANNED_LEAVE,
    )
    session.add(unavail1)
    session.flush()

    # Duplicate unavailability on the same date
    unavail2 = EmployeeUnavailability(
        employee_id=emp.id,
        date=date(2026, 12, 25),
        reason_type=AbsenceReasonType.COMP_OFF,
    )
    session.add(unavail2)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

