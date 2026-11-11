from __future__ import annotations

from datetime import date, time
import uuid

from app.modules.roster.engine.demand import DemandResolver
from app.modules.roster.engine.domain import (
    AllocationType,
    ConflictSeverity,
    ConflictType,
    DemandSlot,
    EmployeeSpec,
    OperatingOverrideSpec,
    OperatingPatternSpec,
    ScheduledAllocation,
    ScheduledShift,
    TimeInterval,
    UnavailabilitySpec,
    ValidationConflict,
)


class IndependentValidator:
    """
    Independent Roster Validation Engine.
    
    Audits:
    1. Shifts:
       - At most one shift per employee per date.
       - No overnight shifts (start_time < end_time).
       - Total working duration <= daily capacity minutes.
    2. Allocations:
       - Every allocation strictly enclosed inside employee's shift.
       - Zero overlapping allocations for same employee on same date (DOUBLE_BOOKING).
       - Zero allocations on approved unavailability dates (UNAVAILABLE_ALLOCATION).
       - Employee possesses required process skill (SKILL_MISMATCH).
       - Cross-pod allocation requires explicit authorization (CROSS_POD_UNAPPROVED).
    3. Demand coverage:
       - Distinct eligible employee count over complete required interval.
       - Partial interval coverage does NOT count towards headcount and is flagged.
    """

    @classmethod
    def validate_roster(
        cls,
        all_dates: list[date],
        brand_processes: list[tuple[uuid.UUID, uuid.UUID, uuid.UUID]],  # (bp_id, brand_id, process_id)
        patterns: dict[uuid.UUID, OperatingPatternSpec],
        overrides: dict[tuple[uuid.UUID, date], OperatingOverrideSpec],
        company_holidays: set[date],
        employees: dict[uuid.UUID, EmployeeSpec],
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        shifts: list[ScheduledShift],
        allocations: list[ScheduledAllocation],
    ) -> list[ValidationConflict]:
        conflicts: list[ValidationConflict] = []

        # -------------------------------------------------------------
        # 1. Audit Shifts: At most 1 shift per (employee, date), valid bounds, capacity
        # -------------------------------------------------------------
        emp_date_shifts: dict[tuple[uuid.UUID, date], list[ScheduledShift]] = {}
        for shift in shifts:
            key = (shift.employee_id, shift.date)
            emp_date_shifts.setdefault(key, []).append(shift)
            
            # Check overnight or invalid interval
            if shift.interval.start_time >= shift.interval.end_time:
                conflicts.append(
                    ValidationConflict(
                        conflict_type=ConflictType.INVALID_SHIFT,
                        severity=ConflictSeverity.HARD_VIOLATION,
                        date=shift.date,
                        employee_id=shift.employee_id,
                        interval=shift.interval,
                        description=(
                            f"Invalid shift interval {shift.interval.start_time}-{shift.interval.end_time}: "
                            f"overnight shifts or non-advancing times are forbidden."
                        ),
                    )
                )

        for (emp_id, target_date), emp_shifts in emp_date_shifts.items():
            if len(emp_shifts) > 1:
                conflicts.append(
                    ValidationConflict(
                        conflict_type=ConflictType.INVALID_SHIFT,
                        severity=ConflictSeverity.HARD_VIOLATION,
                        date=target_date,
                        employee_id=emp_id,
                        description=f"Multiple shifts ({len(emp_shifts)}) assigned to employee on {target_date}.",
                    )
                )

        # -------------------------------------------------------------
        # 2. Audit Allocations: Shift boundaries, double-booking, unavailability, skills, cross-pod auth
        # -------------------------------------------------------------
        emp_date_allocs: dict[tuple[uuid.UUID, date], list[ScheduledAllocation]] = {}
        bp_map = {bp_id: (brand_id, proc_id) for bp_id, brand_id, proc_id in brand_processes}

        for alloc in allocations:
            emp_date_allocs.setdefault((alloc.employee_id, alloc.date), []).append(alloc)
            emp = employees.get(alloc.employee_id)
            bp_info = bp_map.get(alloc.brand_process_id)
            process_id = bp_info[1] if bp_info else None

            # A. Check employee skill match
            if emp and process_id and process_id not in emp.skill_process_ids:
                conflicts.append(
                    ValidationConflict(
                        conflict_type=ConflictType.SKILL_MISMATCH,
                        severity=ConflictSeverity.HARD_VIOLATION,
                        date=alloc.date,
                        employee_id=alloc.employee_id,
                        brand_process_id=alloc.brand_process_id,
                        interval=alloc.interval,
                        description=f"Employee {emp.name} lacks skill required for process {process_id}.",
                    )
                )

            # B. Check approved unavailability
            unavail = unavailabilities.get((alloc.employee_id, alloc.date))
            if unavail and unavail.is_approved:
                conflicts.append(
                    ValidationConflict(
                        conflict_type=ConflictType.UNAVAILABLE_ALLOCATION,
                        severity=ConflictSeverity.HARD_VIOLATION,
                        date=alloc.date,
                        employee_id=alloc.employee_id,
                        brand_process_id=alloc.brand_process_id,
                        interval=alloc.interval,
                        description=f"Employee {alloc.employee_id} allocated while on approved {unavail.reason_type}.",
                    )
                )

            # C. Check cross-pod authorization
            if (
                alloc.allocation_type == AllocationType.CROSS_POD_REASSIGNMENT
                and not alloc.is_cross_pod_approved
            ):
                conflicts.append(
                    ValidationConflict(
                        conflict_type=ConflictType.CROSS_POD_UNAPPROVED,
                        severity=ConflictSeverity.HARD_VIOLATION,
                        date=alloc.date,
                        employee_id=alloc.employee_id,
                        brand_process_id=alloc.brand_process_id,
                        interval=alloc.interval,
                        description=(
                            f"Cross-pod allocation for employee {alloc.employee_id} on {alloc.date} "
                            f"requires Operations Manager authorization."
                        ),
                    )
                )

            # D. Check shift enclosure
            matching_shifts = emp_date_shifts.get((alloc.employee_id, alloc.date), [])
            if not matching_shifts:
                conflicts.append(
                    ValidationConflict(
                        conflict_type=ConflictType.SHIFT_BOUND_EXCEEDED,
                        severity=ConflictSeverity.HARD_VIOLATION,
                        date=alloc.date,
                        employee_id=alloc.employee_id,
                        brand_process_id=alloc.brand_process_id,
                        interval=alloc.interval,
                        description=f"Allocation has no corresponding employee shift on {alloc.date}.",
                    )
                )
            else:
                shift = matching_shifts[0]
                if not shift.interval.contains(alloc.interval):
                    conflicts.append(
                        ValidationConflict(
                            conflict_type=ConflictType.SHIFT_BOUND_EXCEEDED,
                            severity=ConflictSeverity.HARD_VIOLATION,
                            date=alloc.date,
                            employee_id=alloc.employee_id,
                            brand_process_id=alloc.brand_process_id,
                            interval=alloc.interval,
                            description=(
                                f"Allocation interval {alloc.interval.start_time}-{alloc.interval.end_time} "
                                f"exceeds shift boundaries {shift.interval.start_time}-{shift.interval.end_time}."
                            ),
                        )
                    )

        # E. Check daily capacity and double-booking per employee date
        for (emp_id, target_date), allocs in emp_date_allocs.items():
            emp = employees.get(emp_id)
            if emp:
                total_duration = sum(a.interval.duration_minutes for a in allocs)
                if total_duration > emp.daily_capacity_minutes:
                    conflicts.append(
                        ValidationConflict(
                            conflict_type=ConflictType.DAILY_CAPACITY_EXCEEDED,
                            severity=ConflictSeverity.HARD_VIOLATION,
                            date=target_date,
                            employee_id=emp_id,
                            description=(
                                f"Employee {emp.name} allocated {total_duration}m on {target_date}, "
                                f"exceeding daily capacity {emp.daily_capacity_minutes}m."
                            ),
                        )
                    )

            sorted_allocs = sorted(allocs, key=lambda a: a.interval.start_time)
            for i in range(len(sorted_allocs)):
                for j in range(i + 1, len(sorted_allocs)):
                    a1 = sorted_allocs[i]
                    a2 = sorted_allocs[j]
                    if a1.interval.overlaps(a2.interval):
                        conflicts.append(
                            ValidationConflict(
                                conflict_type=ConflictType.DOUBLE_BOOKING,
                                severity=ConflictSeverity.HARD_VIOLATION,
                                date=target_date,
                                employee_id=emp_id,
                                brand_process_id=a2.brand_process_id,
                                interval=TimeInterval(
                                    max(a1.interval.start_time, a2.interval.start_time),
                                    min(a1.interval.end_time, a2.interval.end_time),
                                ),
                                description=(
                                    f"Double booking: Employee allocated to overlapping intervals "
                                    f"({a1.interval.start_time}-{a1.interval.end_time}) and "
                                    f"({a2.interval.start_time}-{a2.interval.end_time})."
                                ),
                            )
                        )

        # -------------------------------------------------------------
        # 3. Independent Demand Verification: Complete Interval Coverage
        # -------------------------------------------------------------
        bp_date_allocs: dict[tuple[uuid.UUID, date], list[ScheduledAllocation]] = {}
        for a in allocations:
            bp_date_allocs.setdefault((a.brand_process_id, a.date), []).append(a)

        for target_date in all_dates:
            is_holiday = target_date in company_holidays
            for bp_id, brand_id, process_id in brand_processes:
                pattern = patterns.get(bp_id)
                if not pattern:
                    continue
                override = overrides.get((bp_id, target_date))
                
                demand = DemandResolver.resolve_slot(
                    brand_process_id=bp_id,
                    brand_id=brand_id,
                    process_id=process_id,
                    target_date=target_date,
                    pattern=pattern,
                    override=override,
                    is_company_holiday=is_holiday,
                )

                if not demand.is_operating or demand.required_staff <= 0:
                    continue

                slot_allocs = bp_date_allocs.get((bp_id, target_date), [])
                
                full_coverage_employees: set[uuid.UUID] = set()
                for a in slot_allocs:
                    if a.interval.contains(demand.interval):
                        full_coverage_employees.add(a.employee_id)
                    elif a.interval.overlaps(demand.interval):
                        conflicts.append(
                            ValidationConflict(
                                conflict_type=ConflictType.PARTIAL_COVERAGE,
                                severity=ConflictSeverity.HARD_VIOLATION,
                                date=target_date,
                                brand_process_id=bp_id,
                                employee_id=a.employee_id,
                                interval=a.interval,
                                description=(
                                    f"Partial coverage: Allocation ({a.interval.start_time}-{a.interval.end_time}) "
                                    f"does not fully cover required interval ({demand.interval.start_time}-{demand.interval.end_time})."
                                ),
                            )
                        )

                covered_count = len(full_coverage_employees)
                if covered_count < demand.required_staff:
                    conflicts.append(
                        ValidationConflict(
                            conflict_type=ConflictType.UNCOVERED_SLOT,
                            severity=ConflictSeverity.HARD_VIOLATION,
                            date=target_date,
                            brand_process_id=bp_id,
                            interval=demand.interval,
                            description=(
                                f"Insufficient staffing on {target_date} for interval "
                                f"{demand.interval.start_time}-{demand.interval.end_time}: "
                                f"required {demand.required_staff}, fully covered by {covered_count}."
                            ),
                        )
                    )

        return conflicts
