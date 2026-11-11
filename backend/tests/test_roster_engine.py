from __future__ import annotations

from datetime import date, time
import uuid

import pytest

from app.modules.roster.engine import (
    AllocationType,
    ConflictSeverity,
    ConflictType,
    DemandResolver,
    DeterministicScheduler,
    EmployeeSpec,
    HolidayBehavior,
    IndependentValidator,
    OperatingOverrideSpec,
    OperatingPatternSpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    ScheduledAllocation,
    ScheduledShift,
    TimeInterval,
    UnavailabilitySpec,
)


@pytest.fixture
def ids():
    return {
        "brand_a": uuid.uuid4(),
        "brand_b": uuid.uuid4(),
        "proc_cs": uuid.uuid4(),
        "proc_acc": uuid.uuid4(),
        "bp_a_cs": uuid.uuid4(),
        "bp_b_cs": uuid.uuid4(),
        "bp_a_acc": uuid.uuid4(),
        "pod_1": uuid.uuid4(),
        "pod_2": uuid.uuid4(),
        "emp1": uuid.uuid4(),
        "emp2": uuid.uuid4(),
        "emp3": uuid.uuid4(),
    }


# =====================================================================
# 1-6: Demand Resolution & Precedence Tests
# =====================================================================

def test_1_normal_weekday_scheduling(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),  # Mon-Fri
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=2,
        min_staffing_weekend=1,
    )
    target = date(2026, 11, 4)
    slot = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], target, pattern, None, False
    )
    assert slot.is_operating is True
    assert slot.required_staff == 2
    assert slot.interval == TimeInterval(time(9, 0), time(18, 0))
    assert slot.resolution_source == "WEEKDAY_OPERATING_RULE"


def test_2_weekend_scheduling(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4, 5, 6),
        start_time=time(10, 0),
        end_time=time(16, 0),
        min_staffing_weekday=3,
        min_staffing_weekend=1,
    )
    target = date(2026, 11, 7)
    slot = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], target, pattern, None, False
    )
    assert slot.is_operating is True
    assert slot.required_staff == 1
    assert slot.interval == TimeInterval(time(10, 0), time(16, 0))


def test_3_closed_holiday(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=2,
        min_staffing_weekend=0,
        holiday_behavior=HolidayBehavior.CLOSED,
    )
    target = date(2026, 11, 2)
    slot = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], target, pattern, None, True
    )
    assert slot.is_operating is False
    assert slot.required_staff == 0
    assert slot.resolution_source == "HOLIDAY_BEHAVIOR_CLOSED"


def test_4_normal_holiday(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=2,
        min_staffing_weekend=0,
        holiday_behavior=HolidayBehavior.NORMAL,
    )
    target = date(2026, 11, 2)
    slot = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], target, pattern, None, True
    )
    assert slot.is_operating is True
    assert slot.required_staff == 2
    assert slot.resolution_source == "HOLIDAY_BEHAVIOR_NORMAL"


def test_5_reduced_holiday(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=3,
        min_staffing_weekend=0,
        holiday_behavior=HolidayBehavior.REDUCED,
        min_staffing_holiday=1,
    )
    target = date(2026, 11, 2)
    slot = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], target, pattern, None, True
    )
    assert slot.is_operating is True
    assert slot.required_staff == 1
    assert slot.interval == TimeInterval(time(9, 0), time(18, 0))
    assert slot.resolution_source == "HOLIDAY_BEHAVIOR_REDUCED"


def test_6_date_override_precedence(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=3,
        min_staffing_weekend=0,
        holiday_behavior=HolidayBehavior.NORMAL,
    )
    target = date(2026, 11, 8)  # Sunday
    override = OperatingOverrideSpec(
        brand_process_id=ids["bp_a_cs"],
        date=target,
        is_closed=False,
        override_start_time=time(10, 0),
        override_end_time=time(14, 0),
        override_min_staffing=4,
        reason="Flash Sale Surge",
    )
    slot = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], target, pattern, override, False
    )
    assert slot.is_operating is True
    assert slot.required_staff == 4
    assert slot.interval == TimeInterval(time(10, 0), time(14, 0))
    assert slot.resolution_source == "DATE_OVERRIDE_OPEN"


# =====================================================================
# 7: Different Operating Calendars for 2 Processes Under 1 Brand
# =====================================================================

def test_7_different_calendars_two_processes_same_brand(ids):
    pattern_cs = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4, 5, 6),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=1,
    )
    pattern_acc = OperatingPatternSpec(
        brand_process_id=ids["bp_a_acc"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    sunday = date(2026, 11, 8)

    slot_cs = DemandResolver.resolve_slot(
        ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"], sunday, pattern_cs, None, False
    )
    slot_acc = DemandResolver.resolve_slot(
        ids["bp_a_acc"], ids["brand_a"], ids["proc_acc"], sunday, pattern_acc, None, False
    )

    assert slot_cs.is_operating is True
    assert slot_cs.required_staff == 1

    assert slot_acc.is_operating is False
    assert slot_acc.required_staff == 0


# =====================================================================
# 8: One Employee Working Multiple Non-Overlapping Processes
# =====================================================================

def test_8_one_employee_working_multiple_non_overlapping_processes(ids):
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Aarav Sharma",
        email="aarav@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"], ids["proc_acc"]]),
    )
    pattern_cs = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(13, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    pattern_acc = OperatingPatternSpec(
        brand_process_id=ids["bp_a_acc"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(13, 30),
        end_time=time(17, 30),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    primary_assignments = [
        PrimaryAssignmentSpec(employee_id=emp.id, brand_process_id=ids["bp_a_cs"], priority=1),
        PrimaryAssignmentSpec(employee_id=emp.id, brand_process_id=ids["bp_a_acc"], priority=1),
    ]

    res = DeterministicScheduler.generate_monthly_roster(
        year=2026,
        month=11,
        brand_processes=[
            (ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"]),
            (ids["bp_a_acc"], ids["brand_a"], ids["proc_acc"]),
        ],
        patterns={ids["bp_a_cs"]: pattern_cs, ids["bp_a_acc"]: pattern_acc},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        primary_assignments=primary_assignments,
        unavailabilities={},
        preferences={},
    )

    nov2_shifts = [s for s in res.shifts if s.date == date(2026, 11, 2)]
    assert len(nov2_shifts) == 1
    # Shift spans exactly from earliest allocation (09:00) to latest (17:30)
    assert nov2_shifts[0].interval == TimeInterval(time(9, 0), time(17, 30))

    nov2_allocs = [a for a in res.allocations if a.date == date(2026, 11, 2)]
    assert len(nov2_allocs) == 2
    assert not nov2_allocs[0].interval.overlaps(nov2_allocs[1].interval)


# =====================================================================
# 9: Employee Working Across Multiple Brands (NEW TEST)
# =====================================================================

def test_9_employee_working_across_multiple_brands(ids):
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Cross Brand Specialist",
        email="specialist@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    # Brand A CS in the morning
    pattern_a = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(13, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    # Brand B CS in the afternoon
    pattern_b = OperatingPatternSpec(
        brand_process_id=ids["bp_b_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(14, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    primary_assignments = [
        PrimaryAssignmentSpec(employee_id=emp.id, brand_process_id=ids["bp_a_cs"], priority=1),
        PrimaryAssignmentSpec(employee_id=emp.id, brand_process_id=ids["bp_b_cs"], priority=1),
    ]

    res = DeterministicScheduler.generate_monthly_roster(
        year=2026,
        month=11,
        brand_processes=[
            (ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"]),
            (ids["bp_b_cs"], ids["brand_b"], ids["proc_cs"]),
        ],
        patterns={ids["bp_a_cs"]: pattern_a, ids["bp_b_cs"]: pattern_b},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        primary_assignments=primary_assignments,
        unavailabilities={},
        preferences={},
    )

    nov2_allocs = [a for a in res.allocations if a.date == date(2026, 11, 2)]
    assert len(nov2_allocs) == 2
    brand_process_ids = {a.brand_process_id for a in nov2_allocs}
    assert brand_process_ids == {ids["bp_a_cs"], ids["bp_b_cs"]}

    # Shift spans 09:00 to 18:00
    nov2_shifts = [s for s in res.shifts if s.date == date(2026, 11, 2)]
    assert len(nov2_shifts) == 1
    assert nov2_shifts[0].interval == TimeInterval(time(9, 0), time(18, 0))


# =====================================================================
# 10: Approved Leave (Hard Constraint)
# =====================================================================

def test_10_approved_leave_surfaces_conflict(ids):
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Rohan Verma",
        email="rohan@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    pattern_cs = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0, 1, 2, 3, 4),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    primary = PrimaryAssignmentSpec(employee_id=emp.id, brand_process_id=ids["bp_a_cs"])
    leave_date = date(2026, 11, 4)
    leave = UnavailabilitySpec(
        employee_id=emp.id,
        date=leave_date,
        reason_type="PLANNED_LEAVE",
        is_approved=True,
    )

    res = DeterministicScheduler.generate_monthly_roster(
        year=2026,
        month=11,
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={ids["bp_a_cs"]: pattern_cs},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        primary_assignments=[primary],
        unavailabilities={(emp.id, leave_date): leave},
        preferences={},
    )

    nov4_allocs = [a for a in res.allocations if a.date == leave_date]
    assert len(nov4_allocs) == 0

    nov4_conflicts = [c for c in res.conflicts if c.date == leave_date]
    assert len(nov4_conflicts) == 1
    assert nov4_conflicts[0].conflict_type == ConflictType.UNCOVERED_SLOT


# =====================================================================
# 11: Preferences Soft Constraint vs Approved Unavailability Hard Constraint (NEW TEST)
# =====================================================================

def test_11_preferences_soft_vs_unavailability_hard(ids):
    # Two employees in same pod:
    # Emp 1 prefers off on Mondays (soft preference).
    # Emp 2 has approved medical leave on Monday (hard constraint).
    # Brand requires coverage on Monday.
    emp1 = EmployeeSpec(
        id=ids["emp1"],
        name="Soft Preference Emp",
        email="soft@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    emp2 = EmployeeSpec(
        id=ids["emp2"],
        name="Hard Leave Emp",
        email="hard@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0,),  # Monday only
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    primary2 = PrimaryAssignmentSpec(employee_id=emp2.id, brand_process_id=ids["bp_a_cs"], priority=1)
    target = date(2026, 11, 2)  # Monday

    # Emp 2 has approved leave on target
    leave2 = UnavailabilitySpec(
        employee_id=emp2.id, date=target, reason_type="PLANNED_LEAVE", is_approved=True
    )
    # Emp 1 has soft preference: prefers Monday off (weekday 0)
    pref1 = PreferenceSpec(employee_id=emp1.id, preferred_weekly_off_days=(0,))

    res = DeterministicScheduler.generate_monthly_roster(
        year=2026,
        month=11,
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={ids["bp_a_cs"]: pattern},
        overrides={},
        company_holidays=set(),
        employees={emp1.id: emp1, emp2.id: emp2},
        primary_assignments=[primary2],
        unavailabilities={(emp2.id, target): leave2},
        preferences={emp1.id: pref1},
    )

    # Emp 2 is strictly NEVER allocated (hard constraint)
    # Emp 1 is allocated as same-pod backup (soft preference is overridden to satisfy required demand)
    allocs = [a for a in res.allocations if a.date == target]
    assert len(allocs) == 1
    assert allocs[0].employee_id == emp1.id
    assert allocs[0].allocation_type == AllocationType.SAME_POD_REASSIGNMENT


# =====================================================================
# Correction 1 Verification: Cross-Pod Authorization Tests
# =====================================================================

def test_cross_pod_candidate_discovered_but_not_auto_allocated(ids):
    # Primary employee in Pod 1 takes leave.
    # No other employees exist in Pod 1.
    # An eligible employee exists in Pod 2.
    # Scheduler MUST NOT auto-allocate Pod 2 employee. It must record uncovered demand AND expose candidate.
    emp_pod1 = EmployeeSpec(
        id=ids["emp1"],
        name="Pod 1 Primary",
        email="p1@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    emp_pod2 = EmployeeSpec(
        id=ids["emp2"],
        name="Pod 2 Backup",
        email="p2@example.com",
        pod_id=ids["pod_2"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0,),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    target = date(2026, 11, 2)
    leave1 = UnavailabilitySpec(
        employee_id=emp_pod1.id, date=target, reason_type="SICK_LEAVE", is_approved=True
    )
    primary = PrimaryAssignmentSpec(employee_id=emp_pod1.id, brand_process_id=ids["bp_a_cs"])

    res = DeterministicScheduler.generate_monthly_roster(
        year=2026,
        month=11,
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={ids["bp_a_cs"]: pattern},
        overrides={},
        company_holidays=set(),
        employees={emp_pod1.id: emp_pod1, emp_pod2.id: emp_pod2},
        primary_assignments=[primary],
        unavailabilities={(emp_pod1.id, target): leave1},
        preferences={},
    )

    # 1. Zero allocations automatically made for Pod 2 employee
    allocs = [a for a in res.allocations if a.date == target]
    assert len(allocs) == 0

    # 2. Slot is flagged as UNCOVERED_SLOT
    conflicts = [c for c in res.conflicts if c.date == target and c.conflict_type == ConflictType.UNCOVERED_SLOT]
    assert len(conflicts) == 1

    # 3. Cross-pod candidate is discovered and recorded for future manager authorization
    candidates = [c for c in res.cross_pod_candidates if c.date == target]
    assert len(candidates) == 1
    assert candidates[0].employee_id == emp_pod2.id
    assert candidates[0].pod_id == ids["pod_2"]


def test_validator_enforces_cross_pod_authorization(ids):
    target = date(2026, 11, 2)
    emp = EmployeeSpec(
        id=ids["emp2"],
        name="Pod 2 Backup",
        email="p2@example.com",
        pod_id=ids["pod_2"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    shift = ScheduledShift(
        id=uuid.uuid4(), employee_id=emp.id, date=target, interval=TimeInterval(time(9, 0), time(18, 0))
    )
    # Allocation with is_cross_pod_approved = False
    unapproved_alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_cs"],
        date=target,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        allocation_type=AllocationType.CROSS_POD_REASSIGNMENT,
        is_cross_pod_approved=False,
    )

    conflicts = IndependentValidator.validate_roster(
        all_dates=[target],
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        unavailabilities={},
        shifts=[shift],
        allocations=[unapproved_alloc],
    )

    unapproved = [c for c in conflicts if c.conflict_type == ConflictType.CROSS_POD_UNAPPROVED]
    assert len(unapproved) == 1
    assert "requires Operations Manager authorization" in unapproved[0].description


# =====================================================================
# 12-16: Independent Validator Integrity Checks
# =====================================================================

def test_12_validator_detects_insufficient_staffing(ids):
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0,),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=2,
        min_staffing_weekend=0,
    )
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Asha",
        email="asha@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    target = date(2026, 11, 2)
    shift = ScheduledShift(
        id=uuid.uuid4(), employee_id=emp.id, date=target, interval=TimeInterval(time(9, 0), time(18, 0))
    )
    alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_cs"],
        date=target,
        interval=TimeInterval(time(9, 0), time(18, 0)),
    )
    conflicts = IndependentValidator.validate_roster(
        all_dates=[target],
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={ids["bp_a_cs"]: pattern},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        unavailabilities={},
        shifts=[shift],
        allocations=[alloc],
    )
    uncovered = [c for c in conflicts if c.conflict_type == ConflictType.UNCOVERED_SLOT]
    assert len(uncovered) == 1
    assert "required 2, fully covered by 1" in uncovered[0].description


def test_13_validator_detects_double_booking(ids):
    target = date(2026, 11, 2)
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Asha",
        email="asha@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"], ids["proc_acc"]]),
    )
    shift = ScheduledShift(
        id=uuid.uuid4(), employee_id=emp.id, date=target, interval=TimeInterval(time(9, 0), time(18, 0))
    )
    a1 = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_cs"],
        date=target,
        interval=TimeInterval(time(9, 0), time(14, 0)),
    )
    a2 = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_acc"],
        date=target,
        interval=TimeInterval(time(13, 0), time(18, 0)),
    )
    conflicts = IndependentValidator.validate_roster(
        all_dates=[target],
        brand_processes=[
            (ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"]),
            (ids["bp_a_acc"], ids["brand_a"], ids["proc_acc"]),
        ],
        patterns={},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        unavailabilities={},
        shifts=[shift],
        allocations=[a1, a2],
    )
    db_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.DOUBLE_BOOKING]
    assert len(db_conflicts) == 1


def test_14_validator_detects_partial_interval_coverage(ids):
    target = date(2026, 11, 2)
    pattern = OperatingPatternSpec(
        brand_process_id=ids["bp_a_cs"],
        operating_days=(0,),
        start_time=time(9, 0),
        end_time=time(18, 0),
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Asha",
        email="asha@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    shift = ScheduledShift(
        id=uuid.uuid4(), employee_id=emp.id, date=target, interval=TimeInterval(time(9, 0), time(18, 0))
    )
    partial_alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_cs"],
        date=target,
        interval=TimeInterval(time(9, 0), time(14, 0)),
    )
    conflicts = IndependentValidator.validate_roster(
        all_dates=[target],
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={ids["bp_a_cs"]: pattern},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        unavailabilities={},
        shifts=[shift],
        allocations=[partial_alloc],
    )
    partial_flags = [c for c in conflicts if c.conflict_type == ConflictType.PARTIAL_COVERAGE]
    assert len(partial_flags) == 1
    uncovered_flags = [c for c in conflicts if c.conflict_type == ConflictType.UNCOVERED_SLOT]
    assert len(uncovered_flags) == 1


def test_15_validator_detects_shift_boundaries_exceeded(ids):
    target = date(2026, 11, 2)
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Asha",
        email="asha@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(10, 0),
        standard_end_time=time(17, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    shift = ScheduledShift(
        id=uuid.uuid4(), employee_id=emp.id, date=target, interval=TimeInterval(time(10, 0), time(17, 0))
    )
    alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_cs"],
        date=target,
        interval=TimeInterval(time(9, 0), time(15, 0)),
    )
    conflicts = IndependentValidator.validate_roster(
        all_dates=[target],
        brand_processes=[(ids["bp_a_cs"], ids["brand_a"], ids["proc_cs"])],
        patterns={},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        unavailabilities={},
        shifts=[shift],
        allocations=[alloc],
    )
    bound_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.SHIFT_BOUND_EXCEEDED]
    assert len(bound_conflicts) == 1


def test_16_validator_detects_skill_mismatch(ids):
    target = date(2026, 11, 2)
    emp = EmployeeSpec(
        id=ids["emp1"],
        name="Asha",
        email="asha@example.com",
        pod_id=ids["pod_1"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([ids["proc_cs"]]),
    )
    shift = ScheduledShift(
        id=uuid.uuid4(), employee_id=emp.id, date=target, interval=TimeInterval(time(9, 0), time(18, 0))
    )
    alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp.id,
        brand_process_id=ids["bp_a_acc"],
        date=target,
        interval=TimeInterval(time(9, 0), time(18, 0)),
    )
    conflicts = IndependentValidator.validate_roster(
        all_dates=[target],
        brand_processes=[(ids["bp_a_acc"], ids["brand_a"], ids["proc_acc"])],
        patterns={},
        overrides={},
        company_holidays=set(),
        employees={emp.id: emp},
        unavailabilities={},
        shifts=[shift],
        allocations=[alloc],
    )
    skill_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.SKILL_MISMATCH]
    assert len(skill_conflicts) == 1
