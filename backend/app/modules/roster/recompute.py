from __future__ import annotations

import calendar
import uuid
from datetime import date
from typing import Any
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from app.modules.operations.models import (
    BrandProcess,
    Holiday,
    PrimaryAssignment,
)
from app.modules.operations.pattern_models import (
    OperatingOverride,
    OperatingPattern,
)
from app.modules.roster.engine import (
    ConflictSeverity as EngineConflictSeverity,
    EmployeeSpec,
    HolidayBehavior as EngineHolidayBehavior,
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
from app.modules.roster.models import (
    ConflictSeverity,
    ConflictType,
    EmployeeShift,
    Roster,
    RosterAllocation,
    RosterConflict,
    RosterStatus,
)
from app.modules.workforce.availability_models import (
    EmployeePreference,
    EmployeeUnavailability,
)
from app.modules.workforce.models import (
    Employee,
    EmployeeProcessSkill,
    EmployeeStatus,
)


def recompute_roster_conflicts_sync(db: Session, roster_id: uuid.UUID) -> int:
    """
    Runs the IndependentValidator against the specified roster using current database constraints
    (including newly approved leaves and brand overrides), updates the roster_conflicts table,
    and updates the roster's status (DRAFT if hard conflicts exist, else VALIDATED).
    Returns the count of hard violations.
    """
    roster = db.get(Roster, roster_id)
    if not roster:
        return 0

    num_days = calendar.monthrange(roster.year, roster.month)[1]
    all_dates = [date(roster.year, roster.month, d) for d in range(1, num_days + 1)]

    bps = db.scalars(select(BrandProcess).where(BrandProcess.is_active == True)).all()
    bp_list = [(bp.id, bp.brand_id, bp.process_id) for bp in bps]

    patterns = db.scalars(select(OperatingPattern)).all()
    patterns_map = {
        p.brand_process_id: OperatingPatternSpec(
            brand_process_id=p.brand_process_id,
            operating_days=[int(d.strip()) for d in p.operating_days.split(",") if d.strip()],
            start_time=p.start_time,
            end_time=p.end_time,
            min_staffing_weekday=p.min_staffing_weekday,
            min_staffing_weekend=p.min_staffing_weekend,
            holiday_behavior=EngineHolidayBehavior(
                p.holiday_behavior.value if hasattr(p.holiday_behavior, "value") else str(p.holiday_behavior)
            ),
            min_staffing_holiday=p.min_staffing_holiday,
        )
        for p in patterns
    }

    overrides = db.scalars(select(OperatingOverride)).all()
    overrides_map = {
        (o.brand_process_id, o.date): OperatingOverrideSpec(
            brand_process_id=o.brand_process_id,
            date=o.date,
            is_closed=o.is_closed,
            override_start_time=o.override_start_time,
            override_end_time=o.override_end_time,
            override_min_staffing=o.override_min_staffing,
        )
        for o in overrides
    }

    holidays = {h.date for h in db.scalars(select(Holiday)).all()}

    active_emps = db.scalars(select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)).all()
    skills = db.scalars(select(EmployeeProcessSkill)).all()
    skills_map: dict[uuid.UUID, set[uuid.UUID]] = {}
    for s in skills:
        skills_map.setdefault(s.employee_id, set()).add(s.process_id)

    emp_map = {
        e.id: EmployeeSpec(
            id=e.id,
            name=e.name,
            email=e.email,
            pod_id=e.pod_id,
            daily_capacity_minutes=e.daily_capacity_minutes,
            standard_start_time=e.standard_start_time,
            standard_end_time=e.standard_end_time,
            skill_process_ids=skills_map.get(e.id, set()),
            is_active=True,
        )
        for e in active_emps
    }

    m_start = date(roster.year, roster.month, 1)
    m_end = date(roster.year, roster.month, num_days)
    unavails_db = db.scalars(
        select(EmployeeUnavailability).where(
            EmployeeUnavailability.date >= m_start, EmployeeUnavailability.date <= m_end
        )
    ).all()
    unavails_map = {
        (u.employee_id, u.date): UnavailabilitySpec(
            employee_id=u.employee_id,
            date=u.date,
            reason_type=u.reason_type.value if hasattr(u.reason_type, "value") else str(u.reason_type),
            is_approved=u.is_approved,
        )
        for u in unavails_db
    }

    shifts = db.scalars(select(EmployeeShift).where(EmployeeShift.roster_id == roster.id)).all()
    engine_shifts = [
        ScheduledShift(
            id=s.id,
            employee_id=s.employee_id,
            date=s.date,
            interval=TimeInterval(s.start_time, s.end_time),
            is_working_day=s.is_working_day,
        )
        for s in shifts
    ]

    allocs = db.scalars(select(RosterAllocation).where(RosterAllocation.roster_id == roster.id)).all()
    engine_allocs = [
        ScheduledAllocation(
            id=a.id,
            employee_id=a.employee_id,
            brand_process_id=a.brand_process_id,
            date=a.date,
            interval=TimeInterval(a.start_time, a.end_time),
            is_cross_pod_approved=a.is_cross_pod_approved,
        )
        for a in allocs
    ]

    validation_conflicts = IndependentValidator.validate_roster(
        all_dates=all_dates,
        brand_processes=bp_list,
        patterns=patterns_map,
        overrides=overrides_map,
        company_holidays=holidays,
        employees=emp_map,
        unavailabilities=unavails_map,
        shifts=engine_shifts,
        allocations=engine_allocs,
    )

    # Replace existing conflicts in database
    db.execute(delete(RosterConflict).where(RosterConflict.roster_id == roster.id))
    for c in validation_conflicts:
        conf_entity = RosterConflict(
            id=uuid.uuid4(),
            roster_id=roster.id,
            date=c.date,
            brand_process_id=c.brand_process_id,
            employee_id=c.employee_id,
            start_time=c.interval.start_time if c.interval else None,
            end_time=c.interval.end_time if c.interval else None,
            severity=ConflictSeverity(c.severity.value),
            conflict_type=ConflictType(c.conflict_type.value),
            description=c.description,
            is_resolved=False,
        )
        db.add(conf_entity)

    hard_count = sum(1 for c in validation_conflicts if c.severity == EngineConflictSeverity.HARD_VIOLATION)
    if roster.status != RosterStatus.PUBLISHED:
        roster.status = RosterStatus.DRAFT if hard_count > 0 else RosterStatus.VALIDATED

    db.flush()
    return hard_count


def recompute_all_active_rosters_conflicts(db: Session) -> dict[str, Any]:
    """
    On-demand recomputation across active rosters (DRAFT, VALIDATED, PUBLISHED, STALE).
    Updates roster_conflicts, updates roster status, and returns a consolidated summary.
    """
    rosters = db.scalars(
        select(Roster).where(
            Roster.status.in_([RosterStatus.DRAFT, RosterStatus.VALIDATED, RosterStatus.PUBLISHED, RosterStatus.STALE])
        ).order_by(Roster.created_at.desc())
    ).all()

    total_conflicts = 0
    total_hard = 0
    summaries = []

    for r in rosters:
        hard_count = recompute_roster_conflicts_sync(db, r.id)
        count = db.scalar(
            select(func.count(RosterConflict.id)).where(RosterConflict.roster_id == r.id)
        ) or 0
        total_conflicts += count
        total_hard += hard_count
        summaries.append({
            "roster_id": str(r.id),
            "roster_name": r.name,
            "status": r.status.value,
            "total_conflicts": count,
            "hard_conflicts": hard_count,
        })

    db.flush()
    return {
        "checked": True,
        "rosters_checked": len(rosters),
        "total_conflicts": total_conflicts,
        "hard_conflicts": total_hard,
        "rosters": summaries,
        "message": (
            f"Conflict check completed across {len(rosters)} roster(s): "
            f"{total_hard} hard violation(s), {total_conflicts} total conflict(s) identified."
            if len(rosters) > 0 else "No active rosters to check."
        ),
    }


