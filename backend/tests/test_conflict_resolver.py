from __future__ import annotations

from datetime import date, time
import uuid

import pytest

from app.modules.roster.engine import (
    ActionType,
    AllocationType,
    AutomatedConflictResolver,
    ConflictSeverity,
    ConflictType,
    DemandSlot,
    EmployeeSpec,
    HolidayBehavior,
    IndependentValidator,
    OperatingPatternSpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    ResolverStatus,
    ScheduledAllocation,
    ScheduledShift,
    TimeInterval,
    UnavailabilitySpec,
)


@pytest.fixture
def base_setup():
    d1 = date(2026, 11, 2)  # Monday (weekday=0)
    pod_a = uuid.uuid4()
    pod_b = uuid.uuid4()

    proc_support = uuid.uuid4()
    proc_ndr = uuid.uuid4()
    proc_retention = uuid.uuid4()

    bp_support = uuid.uuid4()
    bp_ndr = uuid.uuid4()
    bp_retention = uuid.uuid4()

    bp_pod_map = {
        bp_support: pod_a,
        bp_ndr: pod_a,
        bp_retention: pod_b,
    }

    brand_processes = [
        (bp_support, uuid.uuid4(), proc_support),
        (bp_ndr, uuid.uuid4(), proc_ndr),
        (bp_retention, uuid.uuid4(), proc_retention),
    ]

    patterns = {
        bp_support: OperatingPatternSpec(
            brand_process_id=bp_support,
            operating_days=(0, 1, 2, 3, 4),
            start_time=time(9, 0),
            end_time=time(18, 0),
            min_staffing_weekday=1,
            min_staffing_weekend=0,
            holiday_behavior=HolidayBehavior.NORMAL,
        ),
        bp_ndr: OperatingPatternSpec(
            brand_process_id=bp_ndr,
            operating_days=(0, 1, 2, 3, 4),
            start_time=time(9, 0),
            end_time=time(18, 0),
            min_staffing_weekday=1,
            min_staffing_weekend=0,
            holiday_behavior=HolidayBehavior.NORMAL,
        ),
        bp_retention: OperatingPatternSpec(
            brand_process_id=bp_retention,
            operating_days=(0, 1, 2, 3, 4),
            start_time=time(9, 0),
            end_time=time(18, 0),
            min_staffing_weekday=1,
            min_staffing_weekend=0,
            holiday_behavior=HolidayBehavior.NORMAL,
        ),
    }

    return {
        "d1": d1,
        "pod_a": pod_a,
        "pod_b": pod_b,
        "proc_support": proc_support,
        "proc_ndr": proc_ndr,
        "proc_retention": proc_retention,
        "bp_support": bp_support,
        "bp_ndr": bp_ndr,
        "bp_retention": bp_retention,
        "bp_pod_map": bp_pod_map,
        "brand_processes": brand_processes,
        "patterns": patterns,
    }


def test_multi_process_allocations_inside_one_shift(base_setup):
    """
    Validates that an employee can be allocated to multiple non-overlapping processes
    within their shift, resulting in exactly one enclosing shift.
    """
    d1 = base_setup["d1"]
    emp_id = uuid.uuid4()
    bp1 = uuid.uuid4()
    bp2 = uuid.uuid4()
    proc1 = uuid.uuid4()
    proc2 = uuid.uuid4()
    pod = base_setup["pod_a"]

    emp = EmployeeSpec(
        id=emp_id,
        name="Multi Skill Agent",
        email="multi@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc1, proc2]),
        is_active=True,
    )

    slot1 = DemandSlot(
        brand_process_id=bp1,
        brand_id=uuid.uuid4(),
        process_id=proc1,
        date=d1,
        interval=TimeInterval(time(9, 0), time(13, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )
    slot2 = DemandSlot(
        brand_process_id=bp2,
        brand_id=uuid.uuid4(),
        process_id=proc2,
        date=d1,
        interval=TimeInterval(time(14, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp1: pod, bp2: pod}
    brand_processes = [(bp1, slot1.brand_id, proc1), (bp2, slot2.brand_id, proc2)]
    patterns = {
        bp1: OperatingPatternSpec(bp1, (0, 1, 2, 3, 4), time(9, 0), time(13, 0), 1, 0),
        bp2: OperatingPatternSpec(bp2, (0, 1, 2, 3, 4), time(14, 0), time(18, 0), 1, 0),
    }

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot1, slot2],
        employees={emp_id: emp},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.overall_status in (ResolverStatus.OPTIMAL, ResolverStatus.FEASIBLE)
    assert result.final_covered_positions == 2
    assert len(result.proposed_shifts) == 1
    shift = result.proposed_shifts[0]
    assert shift.employee_id == emp_id
    assert shift.interval.start_time <= time(9, 0)
    assert shift.interval.end_time >= time(18, 0)
    assert len(result.proposed_allocations) == 2
    assert len(result.validation_conflicts) == 0


def test_overlapping_intervals_cannot_be_double_booked(base_setup):
    """
    Validates that pairwise overlapping demand intervals cannot both be assigned to the same employee.
    """
    d1 = base_setup["d1"]
    emp_id = uuid.uuid4()
    bp1 = uuid.uuid4()
    bp2 = uuid.uuid4()
    proc1 = uuid.uuid4()
    proc2 = uuid.uuid4()
    pod = base_setup["pod_a"]

    emp = EmployeeSpec(
        id=emp_id,
        name="Solo Agent",
        email="solo@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc1, proc2]),
        is_active=True,
    )

    slot1 = DemandSlot(
        brand_process_id=bp1,
        brand_id=uuid.uuid4(),
        process_id=proc1,
        date=d1,
        interval=TimeInterval(time(9, 0), time(14, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )
    slot2 = DemandSlot(
        brand_process_id=bp2,
        brand_id=uuid.uuid4(),
        process_id=proc2,
        date=d1,
        interval=TimeInterval(time(12, 0), time(17, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp1: pod, bp2: pod}
    brand_processes = [(bp1, slot1.brand_id, proc1), (bp2, slot2.brand_id, proc2)]
    patterns = {
        bp1: OperatingPatternSpec(bp1, (0, 1, 2, 3, 4), time(9, 0), time(14, 0), 1, 0),
        bp2: OperatingPatternSpec(bp2, (0, 1, 2, 3, 4), time(12, 0), time(17, 0), 1, 0),
    }

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot1, slot2],
        employees={emp_id: emp},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 1
    assert result.final_uncovered_positions == 1
    assert len(result.proposed_allocations) == 1
    assert not any(c.conflict_type == ConflictType.DOUBLE_BOOKING for c in result.validation_conflicts)
    assert any(c.conflict_type == ConflictType.UNCOVERED_SLOT for c in result.validation_conflicts)


def test_no_phantom_shifts_when_employee_unassigned(base_setup):
    """
    Validates that employees with zero allocations have no active shift synthesized.
    """
    d1 = base_setup["d1"]
    emp1_id = uuid.uuid4()
    emp2_id = uuid.uuid4()
    bp1 = uuid.uuid4()
    proc1 = uuid.uuid4()
    pod = base_setup["pod_a"]

    emp1 = EmployeeSpec(
        id=emp1_id,
        name="Working Agent",
        email="emp1@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc1]),
        is_active=True,
    )
    emp2 = EmployeeSpec(
        id=emp2_id,
        name="Idle Agent",
        email="emp2@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc1]),
        is_active=True,
    )

    slot1 = DemandSlot(
        brand_process_id=bp1,
        brand_id=uuid.uuid4(),
        process_id=proc1,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp1: pod}
    brand_processes = [(bp1, slot1.brand_id, proc1)]
    patterns = {bp1: OperatingPatternSpec(bp1, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0)}

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot1],
        employees={emp1_id: emp1, emp2_id: emp2},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert len(result.proposed_shifts) == 1
    assert result.proposed_shifts[0].employee_id in (emp1_id, emp2_id)


def test_same_pod_cascading_swap(base_setup):
    """
    Validates a multi-employee cascading swap:
    - Slot 1 (BSC CS) requires CS skill.
    - Slot 2 (BSC NDR) requires NDR skill.
    - Employee A has both CS and NDR skills, but is baseline assigned to Slot 1.
    - Employee B has only CS skill, and is unassigned.
    - Resolver moves Employee B into Slot 1, releasing Employee A for Slot 2.
    """
    d1 = base_setup["d1"]
    pod = base_setup["pod_a"]
    proc_cs = base_setup["proc_support"]
    proc_ndr = base_setup["proc_ndr"]
    bp_cs = base_setup["bp_support"]
    bp_ndr = base_setup["bp_ndr"]

    emp_a_id = uuid.uuid4()
    emp_b_id = uuid.uuid4()

    emp_a = EmployeeSpec(
        id=emp_a_id,
        name="Specialist A (CS + NDR)",
        email="a@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs, proc_ndr]),
        is_active=True,
    )
    emp_b = EmployeeSpec(
        id=emp_b_id,
        name="Generalist B (CS only)",
        email="b@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs]),
        is_active=True,
    )

    slot_cs = DemandSlot(
        brand_process_id=bp_cs,
        brand_id=uuid.uuid4(),
        process_id=proc_cs,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )
    slot_ndr = DemandSlot(
        brand_process_id=bp_ndr,
        brand_id=uuid.uuid4(),
        process_id=proc_ndr,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    baseline_alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp_a_id,
        brand_process_id=bp_cs,
        date=d1,
        interval=slot_cs.interval,
        allocation_type=AllocationType.PRIMARY,
    )

    bp_pod_map = {bp_cs: pod, bp_ndr: pod}
    brand_processes = [
        (bp_cs, slot_cs.brand_id, proc_cs),
        (bp_ndr, slot_ndr.brand_id, proc_ndr),
    ]
    patterns = {
        bp_cs: OperatingPatternSpec(bp_cs, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0),
        bp_ndr: OperatingPatternSpec(bp_ndr, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0),
    }

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot_cs, slot_ndr],
        employees={emp_a_id: emp_a, emp_b_id: emp_b},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[baseline_alloc],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 2
    assert result.final_uncovered_positions == 0

    alloc_map = {a.brand_process_id: a.employee_id for a in result.proposed_allocations}
    assert alloc_map[bp_ndr] == emp_a_id
    assert alloc_map[bp_cs] == emp_b_id

    assert len(result.resolution_bundles) == 1
    bundle = result.resolution_bundles[0]
    assert not bundle.is_cross_pod
    assert not bundle.requires_manager_approval
    # In connected-component grouping, all 3 actions (1 removal + 2 additions) are in 1 atomic bundle!
    assert len(bundle.changes) == 3
    actions = {c.action_type for c in bundle.changes}
    assert ActionType.REMOVE_ALLOCATION in actions
    assert ActionType.NEW_ALLOCATION in actions
    assert len(result.validation_conflicts) == 0


def test_cross_pod_resolution_pass_b(base_setup):
    """
    Validates that when same-pod capacity is exhausted, Pass B discovers the cross-pod
    candidate and tags the bundle with requires_manager_approval = True.
    """
    d1 = base_setup["d1"]
    pod_a = base_setup["pod_a"]
    pod_b = base_setup["pod_b"]
    proc_ret = base_setup["proc_retention"]
    bp_ret = base_setup["bp_retention"]

    emp_b_id = uuid.uuid4()
    emp_b = EmployeeSpec(
        id=emp_b_id,
        name="Cross-Pod Candidate",
        email="cp@test.com",
        pod_id=pod_b,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_ret]),
        is_active=True,
    )

    slot_ret = DemandSlot(
        brand_process_id=bp_ret,
        brand_id=uuid.uuid4(),
        process_id=proc_ret,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp_ret: pod_a}
    brand_processes = [(bp_ret, slot_ret.brand_id, proc_ret)]
    patterns = {bp_ret: OperatingPatternSpec(bp_ret, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0)}

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot_ret],
        employees={emp_b_id: emp_b},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        allow_cross_pod=True,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 1
    assert len(result.resolution_bundles) == 1
    bundle = result.resolution_bundles[0]
    assert bundle.is_cross_pod is True
    assert bundle.requires_manager_approval is True
    assert len(result.proposed_allocations) == 1
    assert result.proposed_allocations[0].allocation_type == AllocationType.CROSS_POD_REASSIGNMENT


def test_evidence_based_shortage_reporting(base_setup):
    """
    Validates that when a skill is genuinely missing, the resolver produces ShortageEvidence
    with an exact reason.
    """
    d1 = base_setup["d1"]
    pod_a = base_setup["pod_a"]
    proc_ret = base_setup["proc_retention"]
    bp_ret = base_setup["bp_retention"]

    emp_id = uuid.uuid4()
    emp = EmployeeSpec(
        id=emp_id,
        name="CS Only Agent",
        email="csonly@test.com",
        pod_id=pod_a,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([base_setup["proc_support"]]),
        is_active=True,
    )

    slot_ret = DemandSlot(
        brand_process_id=bp_ret,
        brand_id=uuid.uuid4(),
        process_id=proc_ret,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp_ret: pod_a}
    brand_processes = [(bp_ret, slot_ret.brand_id, proc_ret)]
    patterns = {bp_ret: OperatingPatternSpec(bp_ret, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0)}

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot_ret],
        employees={emp_id: emp},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        allow_cross_pod=True,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 0
    assert result.final_uncovered_positions == 1
    assert len(result.shortage_evidences) == 1
    evidence = result.shortage_evidences[0]
    assert evidence.shortfall == 1
    assert evidence.total_company_certified == 0
    assert any("0 active employees certified" in r for r in evidence.reasons)


def test_snapshot_hash_determinism_and_invalidation(base_setup):
    """
    Validates that identical solver inputs produce the identical SHA-256 fingerprint,
    and altering any preference, availability, or assignment changes the hash.
    """
    d1 = base_setup["d1"]
    emp_id = uuid.uuid4()
    bp1 = uuid.uuid4()
    proc1 = uuid.uuid4()

    emp = EmployeeSpec(
        id=emp_id,
        name="Agent 1",
        email="a1@test.com",
        pod_id=base_setup["pod_a"],
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc1]),
    )
    slot1 = DemandSlot(
        brand_process_id=bp1,
        brand_id=uuid.uuid4(),
        process_id=proc1,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    hash1 = AutomatedConflictResolver.compute_snapshot_hash(
        target_dates=[d1],
        demand_slots=[slot1],
        employees={emp_id: emp},
        primary_assignments=[],
        unavailabilities={},
        preferences={emp_id: PreferenceSpec(employee_id=emp_id, preferred_weekly_off_days=(5, 6))},
        existing_allocations=[],
    )
    hash2 = AutomatedConflictResolver.compute_snapshot_hash(
        target_dates=[d1],
        demand_slots=[slot1],
        employees={emp_id: emp},
        primary_assignments=[],
        unavailabilities={},
        preferences={emp_id: PreferenceSpec(employee_id=emp_id, preferred_weekly_off_days=(5, 6))},
        existing_allocations=[],
    )
    assert hash1 == hash2
    assert len(hash1) == 64

    # 1. Alter preferences: hash must change!
    hash_pref_changed = AutomatedConflictResolver.compute_snapshot_hash(
        target_dates=[d1],
        demand_slots=[slot1],
        employees={emp_id: emp},
        primary_assignments=[],
        unavailabilities={},
        preferences={emp_id: PreferenceSpec(employee_id=emp_id, preferred_weekly_off_days=(0, 6))},
        existing_allocations=[],
    )
    assert hash1 != hash_pref_changed

    # 2. Alter unavailability: hash must change!
    hash_unavail_changed = AutomatedConflictResolver.compute_snapshot_hash(
        target_dates=[d1],
        demand_slots=[slot1],
        employees={emp_id: emp},
        primary_assignments=[],
        unavailabilities={(emp_id, d1): UnavailabilitySpec(emp_id, d1, "SICK_LEAVE", True)},
        preferences={emp_id: PreferenceSpec(employee_id=emp_id, preferred_weekly_off_days=(5, 6))},
        existing_allocations=[],
    )
    assert hash1 != hash_unavail_changed


def test_daily_capacity_duration_enforced(base_setup):
    """
    Validates that allocations cannot exceed daily working capacity (540 minutes).
    Two non-overlapping 5-hour slots = 600 minutes > 540 allowed.
    """
    d1 = base_setup["d1"]
    emp_id = uuid.uuid4()
    bp1 = uuid.uuid4()
    bp2 = uuid.uuid4()
    proc1 = uuid.uuid4()
    proc2 = uuid.uuid4()
    pod = base_setup["pod_a"]

    emp = EmployeeSpec(
        id=emp_id,
        name="Standard Agent",
        email="std@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(8, 0),
        standard_end_time=time(19, 0),
        skill_process_ids=frozenset([proc1, proc2]),
        is_active=True,
    )

    slot1 = DemandSlot(
        brand_process_id=bp1,
        brand_id=uuid.uuid4(),
        process_id=proc1,
        date=d1,
        interval=TimeInterval(time(8, 0), time(13, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )
    slot2 = DemandSlot(
        brand_process_id=bp2,
        brand_id=uuid.uuid4(),
        process_id=proc2,
        date=d1,
        interval=TimeInterval(time(13, 30), time(18, 30)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp1: pod, bp2: pod}
    brand_processes = [(bp1, slot1.brand_id, proc1), (bp2, slot2.brand_id, proc2)]
    patterns = {
        bp1: OperatingPatternSpec(bp1, (0, 1, 2, 3, 4), time(8, 0), time(13, 0), 1, 0),
        bp2: OperatingPatternSpec(bp2, (0, 1, 2, 3, 4), time(13, 30), time(18, 30), 1, 0),
    }

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot1, slot2],
        employees={emp_id: emp},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 1
    assert result.final_uncovered_positions == 1
    total_minutes = sum(a.interval.duration_minutes for a in result.proposed_allocations)
    assert total_minutes <= 540
    assert not any(c.conflict_type == ConflictType.DAILY_CAPACITY_EXCEEDED for c in result.validation_conflicts)


def test_approved_leave_exclusion(base_setup):
    """
    Validates that an employee on approved leave cannot be allocated.
    """
    d1 = base_setup["d1"]
    emp_id = uuid.uuid4()
    bp1 = uuid.uuid4()
    proc1 = uuid.uuid4()
    pod = base_setup["pod_a"]

    emp = EmployeeSpec(
        id=emp_id,
        name="Sick Agent",
        email="sick@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc1]),
        is_active=True,
    )

    slot1 = DemandSlot(
        brand_process_id=bp1,
        brand_id=uuid.uuid4(),
        process_id=proc1,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    unavails = {
        (emp_id, d1): UnavailabilitySpec(
            employee_id=emp_id,
            date=d1,
            reason_type="SICK_LEAVE",
            is_approved=True,
        )
    }

    bp_pod_map = {bp1: pod}
    brand_processes = [(bp1, slot1.brand_id, proc1)]
    patterns = {bp1: OperatingPatternSpec(bp1, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0)}

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot1],
        employees={emp_id: emp},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities=unavails,
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 0
    assert result.final_uncovered_positions == 1
    assert len(result.proposed_allocations) == 0
    assert len(result.proposed_shifts) == 0
    assert len(result.shortage_evidences) == 1
    assert any("approved leave" in r for r in result.shortage_evidences[0].reasons)


def test_pass_b_preserves_pass_a_fully_satisfied_slots(base_setup):
    """
    Regression Test: Pass B must preserve both filled positions AND fully satisfied demand intervals
    achieved in Pass A.
    - Slot 1 (Same-Pod) requires 2 staff. Two same-pod employees A & B are available.
    - Slot 2 (Cross-Pod) requires 1 staff. Employee B is also certified for Slot 2.
    - Pass B must NOT steal Employee B to cover Slot 2 if it breaks Slot 1's full satisfaction!
    """
    d1 = base_setup["d1"]
    pod_a = base_setup["pod_a"]
    pod_b = base_setup["pod_b"]
    proc_cs = base_setup["proc_support"]
    proc_ret = base_setup["proc_retention"]
    bp_cs = base_setup["bp_support"]
    bp_ret = base_setup["bp_retention"]

    emp_a_id = uuid.uuid4()
    emp_b_id = uuid.uuid4()

    # Both in Pod A
    emp_a = EmployeeSpec(
        id=emp_a_id,
        name="Pod A Agent 1",
        email="a1@test.com",
        pod_id=pod_a,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs]),
        is_active=True,
    )
    emp_b = EmployeeSpec(
        id=emp_b_id,
        name="Pod A Agent 2 (Cross-Skilled in Retention)",
        email="a2@test.com",
        pod_id=pod_a,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs, proc_ret]),
        is_active=True,
    )

    # Slot CS requires 2 employees (Pod A)
    slot_cs = DemandSlot(
        brand_process_id=bp_cs,
        brand_id=uuid.uuid4(),
        process_id=proc_cs,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=2,
        is_operating=True,
        resolution_source="TEST",
    )
    # Slot Retention requires 1 employee (Pod B)
    slot_ret = DemandSlot(
        brand_process_id=bp_ret,
        brand_id=uuid.uuid4(),
        process_id=proc_ret,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp_cs: pod_a, bp_ret: pod_b}
    brand_processes = [
        (bp_cs, slot_cs.brand_id, proc_cs),
        (bp_ret, slot_ret.brand_id, proc_ret),
    ]
    patterns = {
        bp_cs: OperatingPatternSpec(bp_cs, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 2, 0),
        bp_ret: OperatingPatternSpec(bp_ret, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0),
    }

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot_cs, slot_ret],
        employees={emp_a_id: emp_a, emp_b_id: emp_b},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        allow_cross_pod=True,
        time_limit_seconds=3.0,
    )

    # Slot CS has both emp_a and emp_b and is FULLY SATISFIED (v=1, 2 positions)
    # Pass B must preserve fully_satisfied_slots >= 1
    assert result.fully_satisfied_demand_slots == 1
    assert result.final_covered_positions == 2
    # Verify allocations: both emp_a and emp_b stayed on bp_cs!
    cs_allocs = [a for a in result.proposed_allocations if a.brand_process_id == bp_cs]
    assert len(cs_allocs) == 2
    assert set(a.employee_id for a in cs_allocs) == {emp_a_id, emp_b_id}


def test_multi_staff_partial_coverage_metrics(base_setup):
    """
    Validates exact metrics when a demand slot is partially covered:
    - Slot requires 2 staff.
    - Only 1 qualified employee is available.
    - Result: covered_positions = 1, fully_satisfied_demand_slots = 0, partially_satisfied_demand_slots = 1.
    """
    d1 = base_setup["d1"]
    pod_a = base_setup["pod_a"]
    proc_cs = base_setup["proc_support"]
    bp_cs = base_setup["bp_support"]

    emp_id = uuid.uuid4()
    emp = EmployeeSpec(
        id=emp_id,
        name="Solo Agent",
        email="solo@test.com",
        pod_id=pod_a,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs]),
        is_active=True,
    )

    slot_cs = DemandSlot(
        brand_process_id=bp_cs,
        brand_id=uuid.uuid4(),
        process_id=proc_cs,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=2,  # requires 2
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp_cs: pod_a}
    brand_processes = [(bp_cs, slot_cs.brand_id, proc_cs)]
    patterns = {bp_cs: OperatingPatternSpec(bp_cs, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 2, 0)}

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot_cs],
        employees={emp_id: emp},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.total_required_staff_positions == 2
    assert result.final_covered_positions == 1
    assert result.final_uncovered_positions == 1
    assert result.fully_satisfied_demand_slots == 0
    assert result.partially_satisfied_demand_slots == 1
    assert result.uncovered_demand_slots == 0
    assert len(result.shortage_evidences) == 1
    assert result.shortage_evidences[0].shortfall == 1


def test_soft_weekly_off_preference_influence(base_setup):
    """
    Validates soft preference handling:
    - On Monday (weekday=0), Slot requires 1 agent.
    - Agent 1 prefers Monday off (preferred_weekly_off_days = (0, 6)).
    - Agent 2 has standard weekend off (preferred_weekly_off_days = (5, 6)).
    - The resolver prefers assigning Agent 2 over Agent 1.
    - But if Agent 2 is unavailable, Agent 1 is assigned (soft preference sacrificed for coverage).
    """
    d1 = base_setup["d1"]  # 2026-11-02 is Monday (0)
    pod = base_setup["pod_a"]
    proc_cs = base_setup["proc_support"]
    bp_cs = base_setup["bp_support"]

    emp1_id = uuid.uuid4()
    emp2_id = uuid.uuid4()

    emp1 = EmployeeSpec(
        id=emp1_id,
        name="Prefers Mon Off",
        email="emp1@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs]),
    )
    emp2 = EmployeeSpec(
        id=emp2_id,
        name="Standard Off",
        email="emp2@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_cs]),
    )

    slot = DemandSlot(
        brand_process_id=bp_cs,
        brand_id=uuid.uuid4(),
        process_id=proc_cs,
        date=d1,
        interval=TimeInterval(time(9, 0), time(18, 0)),
        required_staff=1,
        is_operating=True,
        resolution_source="TEST",
    )

    bp_pod_map = {bp_cs: pod}
    brand_processes = [(bp_cs, slot.brand_id, proc_cs)]
    patterns = {bp_cs: OperatingPatternSpec(bp_cs, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0)}

    prefs = {
        emp1_id: PreferenceSpec(employee_id=emp1_id, preferred_weekly_off_days=(0, 6)),  # Monday off
        emp2_id: PreferenceSpec(employee_id=emp2_id, preferred_weekly_off_days=(5, 6)),  # Sat/Sun off
    }

    # Case A: Both available -> Solver chooses emp2 (respecting emp1's soft preference)
    result_a = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot],
        employees={emp1_id: emp1, emp2_id: emp2},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences=prefs,
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )
    assert result_a.final_covered_positions == 1
    assert result_a.proposed_allocations[0].employee_id == emp2_id

    # Case B: Only emp1 available -> Solver assigns emp1 (coverage overrides soft preference)
    result_b = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot],
        employees={emp1_id: emp1},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences=prefs,
        existing_allocations=[],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )
    assert result_b.final_covered_positions == 1
    assert result_b.proposed_allocations[0].employee_id == emp1_id


def test_atomic_cascading_bundle_connected_graph(base_setup):
    """
    Validates that on date d:
    - Cascading changes involving Employee 1 moving from Brand X to Brand Y, and Employee 2
      filling Brand X, share exactly ONE atomic ResolutionBundle.
    - An independent change on Brand Z gets a distinct ResolutionBundle.
    """
    d1 = base_setup["d1"]
    pod = base_setup["pod_a"]

    proc_x = uuid.uuid4()
    proc_y = uuid.uuid4()
    proc_z = uuid.uuid4()

    bp_x = uuid.uuid4()
    bp_y = uuid.uuid4()
    bp_z = uuid.uuid4()

    emp1_id = uuid.uuid4()
    emp2_id = uuid.uuid4()
    emp3_id = uuid.uuid4()

    emp1 = EmployeeSpec(
        id=emp1_id,
        name="Emp 1 (X & Y)",
        email="e1@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_x, proc_y]),
    )
    emp2 = EmployeeSpec(
        id=emp2_id,
        name="Emp 2 (X only)",
        email="e2@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_x]),
    )
    emp3 = EmployeeSpec(
        id=emp3_id,
        name="Emp 3 (Z only)",
        email="e3@test.com",
        pod_id=pod,
        daily_capacity_minutes=540,
        standard_start_time=time(9, 0),
        standard_end_time=time(18, 0),
        skill_process_ids=frozenset([proc_z]),
    )

    slot_x = DemandSlot(bp_x, uuid.uuid4(), proc_x, d1, TimeInterval(time(9, 0), time(18, 0)), 1, True, "TEST")
    slot_y = DemandSlot(bp_y, uuid.uuid4(), proc_y, d1, TimeInterval(time(9, 0), time(18, 0)), 1, True, "TEST")
    slot_z = DemandSlot(bp_z, uuid.uuid4(), proc_z, d1, TimeInterval(time(9, 0), time(18, 0)), 1, True, "TEST")

    # Baseline: emp1 on bp_x; bp_y and bp_z are uncovered
    baseline_alloc = ScheduledAllocation(
        id=uuid.uuid4(),
        employee_id=emp1_id,
        brand_process_id=bp_x,
        date=d1,
        interval=slot_x.interval,
        allocation_type=AllocationType.PRIMARY,
    )

    bp_pod_map = {bp_x: pod, bp_y: pod, bp_z: pod}
    brand_processes = [
        (bp_x, slot_x.brand_id, proc_x),
        (bp_y, slot_y.brand_id, proc_y),
        (bp_z, slot_z.brand_id, proc_z),
    ]
    patterns = {
        bp_x: OperatingPatternSpec(bp_x, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0),
        bp_y: OperatingPatternSpec(bp_y, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0),
        bp_z: OperatingPatternSpec(bp_z, (0, 1, 2, 3, 4), time(9, 0), time(18, 0), 1, 0),
    }

    result = AutomatedConflictResolver.solve(
        target_dates=[d1],
        demand_slots=[slot_x, slot_y, slot_z],
        employees={emp1_id: emp1, emp2_id: emp2, emp3_id: emp3},
        patterns=patterns,
        overrides={},
        company_holidays=set(),
        primary_assignments=[],
        unavailabilities={},
        preferences={},
        existing_allocations=[baseline_alloc],
        existing_shifts=[],
        brand_processes=brand_processes,
        bp_pod_map=bp_pod_map,
        time_limit_seconds=3.0,
    )

    assert result.final_covered_positions == 3
    # Two disjoint connected components:
    # Component 1: {emp1, emp2, bp_x, bp_y} (cascading swap between X and Y)
    # Component 2: {emp3, bp_z} (independent addition on Z)
    assert len(result.resolution_bundles) == 2

    bundles_by_brand_count = sorted(result.resolution_bundles, key=lambda b: len(b.brand_process_ids), reverse=True)
    cascading_bundle = bundles_by_brand_count[0]
    independent_bundle = bundles_by_brand_count[1]

    # Cascading bundle spans bp_x and bp_y
    assert set(cascading_bundle.brand_process_ids) == {bp_x, bp_y}
    # Contains all changes (emp1 moved, emp2 added)
    assert len(cascading_bundle.changes) >= 2

    # Independent bundle only spans bp_z
    assert independent_bundle.brand_process_ids == [bp_z]
    assert len(independent_bundle.changes) == 1
    assert independent_bundle.changes[0].employee_id == emp3_id
