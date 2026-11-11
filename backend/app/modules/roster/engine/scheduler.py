from __future__ import annotations

import calendar
from datetime import date
import uuid

from app.modules.roster.engine.demand import DemandResolver
from app.modules.roster.engine.domain import (
    AllocationType,
    ConflictSeverity,
    ConflictType,
    CrossPodCandidate,
    DemandSlot,
    EmployeeSpec,
    OperatingOverrideSpec,
    OperatingPatternSpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    RosterScheduleResult,
    ScheduledAllocation,
    ScheduledShift,
    TimeInterval,
    UnavailabilitySpec,
    ValidationConflict,
)
from app.modules.roster.engine.eligibility import EligibilityChecker


class DeterministicScheduler:
    """
    Deterministic monthly roster scheduling engine.
    
    Principles:
    1. Consumes structured input without direct DB queries or side effects.
    2. Resolves demand for each brand-process per date via DemandResolver.
    3. Allocates eligible primary employees first (by assignment priority).
    4. If primary employees are unavailable or insufficient, searches eligible SAME-POD backup candidates.
    5. Cross-pod employees are NEVER allocated automatically without Operations Manager authorization.
       Instead, eligible cross-pod candidates are recorded in result.cross_pod_candidates, and the slot
       remains flagged as UNCOVERED_SLOT until authorized by a manager.
    6. Synthesizes at most one shift per working employee per date, enclosing all allocations without
       exceeding daily capacity.
    7. Guarantees non-overlapping process allocations within the shift.
    """

    @classmethod
    def generate_monthly_roster(
        cls,
        year: int,
        month: int,
        brand_processes: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]],  # (bp_id, brand_id, process_id)
        patterns: dict[uuid.UUID, OperatingPatternSpec],
        overrides: dict[tuple[uuid.UUID, date], OperatingOverrideSpec],
        company_holidays: set[date],
        employees: dict[uuid.UUID, EmployeeSpec],
        primary_assignments: list[PrimaryAssignmentSpec],
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        preferences: dict[uuid.UUID, PreferenceSpec],
    ) -> RosterScheduleResult:
        result = RosterScheduleResult()
        num_days = calendar.monthrange(year, month)[1]
        all_dates = [date(year, month, d) for d in range(1, num_days + 1)]

        # Map primary assignments by brand_process_id sorted by priority (1 is highest priority)
        bp_primary_map: dict[uuid.UUID, list[PrimaryAssignmentSpec]] = {}
        for pa in sorted(primary_assignments, key=lambda a: a.priority):
            bp_primary_map.setdefault(pa.brand_process_id, []).append(pa)

        # Iterate over each date of the month
        for target_date in all_dates:
            is_holiday = target_date in company_holidays

            # 1. Resolve demand slots for all brand-processes on target_date
            demand_slots: list[DemandSlot] = []
            for bp_id, brand_id, process_id in brand_processes:
                pattern = patterns.get(bp_id)
                if not pattern:
                    continue
                override = overrides.get((bp_id, target_date))
                slot = DemandResolver.resolve_slot(
                    brand_process_id=bp_id,
                    brand_id=brand_id,
                    process_id=process_id,
                    target_date=target_date,
                    pattern=pattern,
                    override=override,
                    is_company_holiday=is_holiday,
                )
                if slot.is_operating and slot.required_staff > 0:
                    demand_slots.append(slot)

            # 2. Allocate employees to demand slots on target_date
            # Sort demand slots deterministically by (start_time, brand_id, process_id)
            demand_slots.sort(key=lambda s: (s.interval.start_time, s.brand_id, s.process_id))

            for slot in demand_slots:
                needed = slot.required_staff
                allocated_for_slot = 0

                # Determine the primary pod(s) responsible for this brand-process
                primary_candidates = bp_primary_map.get(slot.brand_process_id, [])
                primary_emp_ids = [pa.employee_id for pa in primary_candidates]
                primary_pods = {
                    employees[eid].pod_id for eid in primary_emp_ids if eid in employees and employees[eid].pod_id
                }

                # A. Try Primary Assigned Employees first
                for pa in primary_candidates:
                    if allocated_for_slot >= needed:
                        break
                    # Check active date range for assignment
                    if pa.effective_from <= target_date and (
                        pa.effective_to is None or pa.effective_to >= target_date
                    ):
                        emp = employees.get(pa.employee_id)
                        if not emp:
                            continue
                        
                        eligible, _reason = EligibilityChecker.is_eligible_for_slot(
                            employee=emp,
                            process_id=slot.process_id,
                            slot_interval=slot.interval,
                            target_date=target_date,
                            unavailabilities=unavailabilities,
                            current_allocations=result.allocations,
                        )
                        if eligible:
                            alloc = ScheduledAllocation(
                                id=uuid.uuid4(),
                                employee_id=emp.id,
                                brand_process_id=slot.brand_process_id,
                                date=target_date,
                                interval=slot.interval,
                                allocation_type=AllocationType.PRIMARY,
                            )
                            result.allocations.append(alloc)
                            allocated_for_slot += 1

                # B. If understaffed, search eligible SAME-POD backup candidates only
                if allocated_for_slot < needed:
                    same_pod_candidates: list[tuple[int, EmployeeSpec]] = []
                    cross_pod_candidates: list[CrossPodCandidate] = []

                    already_allocated_emp_ids = {
                        a.employee_id
                        for a in result.allocations
                        if a.date == target_date and a.brand_process_id == slot.brand_process_id
                    }

                    for emp in employees.values():
                        if emp.id in already_allocated_emp_ids:
                            continue

                        eligible, _ = EligibilityChecker.is_eligible_for_slot(
                            employee=emp,
                            process_id=slot.process_id,
                            slot_interval=slot.interval,
                            target_date=target_date,
                            unavailabilities=unavailabilities,
                            current_allocations=result.allocations,
                        )
                        if eligible:
                            is_same_pod = emp.pod_id in primary_pods if primary_pods else False
                            pref = preferences.get(emp.id)
                            prefers_off = bool(pref and target_date.weekday() in pref.preferred_weekly_off_days)

                            if is_same_pod:
                                # Rank: prefers_off (asc) -> name
                                same_pod_candidates.append((1 if prefers_off else 0, emp))
                            else:
                                # Record cross-pod candidate for manager discovery (DO NOT auto-allocate)
                                cross_pod_candidates.append(
                                    CrossPodCandidate(
                                        employee_id=emp.id,
                                        employee_name=emp.name,
                                        pod_id=emp.pod_id,
                                        brand_process_id=slot.brand_process_id,
                                        date=target_date,
                                        interval=slot.interval,
                                        prefers_off_on_day=prefers_off,
                                    )
                                )

                    # Sort same-pod candidates: employees not preferring off on this day first
                    same_pod_candidates.sort(key=lambda item: (item[0], item[1].name))

                    for _, emp in same_pod_candidates:
                        if allocated_for_slot >= needed:
                            break
                        alloc = ScheduledAllocation(
                            id=uuid.uuid4(),
                            employee_id=emp.id,
                            brand_process_id=slot.brand_process_id,
                            date=target_date,
                            interval=slot.interval,
                            allocation_type=AllocationType.SAME_POD_REASSIGNMENT,
                            notes="Auto same-pod backup allocation",
                        )
                        result.allocations.append(alloc)
                        allocated_for_slot += 1

                    # Record cross-pod candidates in schedule result for future manager discovery
                    result.cross_pod_candidates.extend(cross_pod_candidates)

                # C. If STILL understaffed, record uncovered demand and conflict
                if allocated_for_slot < needed:
                    shortfall = needed - allocated_for_slot
                    result.uncovered_demand.append(slot)
                    result.conflicts.append(
                        ValidationConflict(
                            conflict_type=ConflictType.UNCOVERED_SLOT,
                            severity=ConflictSeverity.HARD_VIOLATION,
                            date=target_date,
                            brand_process_id=slot.brand_process_id,
                            interval=slot.interval,
                            description=(
                                f"Uncovered demand on {target_date}: required {needed} employees, "
                                f"assigned {allocated_for_slot}. Shortfall: {shortfall}."
                            ),
                        )
                    )

        # 3. Build Employee Shifts enclosing their allocations (Max 1 shift per employee per working date)
        emp_date_allocs: dict[tuple[uuid.UUID, date], list[ScheduledAllocation]] = {}
        for a in result.allocations:
            emp_date_allocs.setdefault((a.employee_id, a.date), []).append(a)

        for (emp_id, target_date), allocs in emp_date_allocs.items():
            emp = employees[emp_id]
            # Shift window: spans exactly from earliest allocation start to latest allocation end
            shift_start = min(a.interval.start_time for a in allocs)
            shift_end = max(a.interval.end_time for a in allocs)

            shift = ScheduledShift(
                id=uuid.uuid4(),
                employee_id=emp_id,
                date=target_date,
                interval=TimeInterval(shift_start, shift_end),
                is_working_day=True,
            )
            result.shifts.append(shift)

        return result
