from __future__ import annotations

from datetime import date
import uuid

from app.modules.roster.engine.domain import (
    EmployeeSpec,
    ScheduledAllocation,
    TimeInterval,
    UnavailabilitySpec,
)


class EligibilityChecker:
    """
    Deterministic employee eligibility checks for process staffing.
    
    An employee is eligible to cover a DemandSlot on a target date if:
    1. Employee is active.
    2. Employee possesses the required skill/process capability.
    3. Employee has NO approved full-shift unavailability on that date.
    4. Employee's shift window contains the required slot interval.
    5. Employee has NO overlapping allocations on that date.
    6. Adding this allocation does not exceed daily capacity minutes.
    """

    @staticmethod
    def is_eligible_for_slot(
        employee: EmployeeSpec,
        process_id: uuid.UUID,
        slot_interval: TimeInterval,
        target_date: date,
        unavailabilities: dict[tuple[uuid.UUID, date], UnavailabilitySpec],
        current_allocations: list[ScheduledAllocation],
    ) -> tuple[bool, str]:
        # 1. Active employee status
        if not employee.is_active:
            return False, f"Employee {employee.name} is inactive."

        # 2. Process skill match
        if process_id not in employee.skill_process_ids:
            return False, f"Employee {employee.name} lacks required skill for process {process_id}."

        # 3. Approved full-shift unavailability
        unavail = unavailabilities.get((employee.id, target_date))
        if unavail is not None and unavail.is_approved:
            return False, f"Employee {employee.name} is on approved {unavail.reason_type}."

        # 4. Standard shift boundary check
        emp_shift_interval = TimeInterval(employee.standard_start_time, employee.standard_end_time)
        if not emp_shift_interval.contains(slot_interval):
            return (
                False,
                f"Slot interval {slot_interval.start_time}-{slot_interval.end_time} falls outside "
                f"employee shift window {emp_shift_interval.start_time}-{emp_shift_interval.end_time}.",
            )

        # 5. Overlapping allocation check (Strict non-overlapping intervals within same date)
        emp_allocs_today = [
            a for a in current_allocations if a.employee_id == employee.id and a.date == target_date
        ]
        for existing in emp_allocs_today:
            if existing.interval.overlaps(slot_interval):
                return (
                    False,
                    f"Overlaps with existing allocation ({existing.interval.start_time}-{existing.interval.end_time}) "
                    f"for brand-process {existing.brand_process_id}.",
                )

        # 6. Daily capacity check
        total_allocated_minutes = sum(a.interval.duration_minutes for a in emp_allocs_today)
        if total_allocated_minutes + slot_interval.duration_minutes > employee.daily_capacity_minutes:
            return (
                False,
                f"Exceeds daily capacity: {total_allocated_minutes + slot_interval.duration_minutes}m > "
                f"{employee.daily_capacity_minutes}m allowed.",
            )

        return True, "Eligible"

