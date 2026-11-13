from __future__ import annotations

from typing import Any

import calendar
import csv
from datetime import date, datetime, time, timezone
import hashlib
import io
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, require_manager, require_lead_or_manager
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import (
    Brand,
    BrandProcess,
    Holiday,
    HolidayBehavior,
    PrimaryAssignment,
    Process,
    RecordStatus,
)
from app.modules.operations.pattern_models import (
    OperatingOverride,
    OperatingPattern,
)
from app.modules.roster.engine import (
    ActionType,
    AllocationType as EngineAllocationType,
    AutomatedConflictResolver,
    ConflictSeverity as EngineConflictSeverity,
    ConflictType as EngineConflictType,
    DemandResolver,
    DeterministicScheduler,
    EligibilityChecker,
    EmployeeSpec,
    HolidayBehavior as EngineHolidayBehavior,
    IndependentValidator,
    OperatingOverrideSpec,
    OperatingPatternSpec,
    PreferenceSpec,
    PrimaryAssignmentSpec,
    ResolutionBundle,
    ResolverResult,
    ResolverStatus,
    ScheduledAllocation,
    ScheduledShift,
    ShortageEvidence,
    TimeInterval,
    UnavailabilitySpec,
    ValidationConflict,
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
from app.modules.roster.schemas import (
    AllocationCell,
    AllocationLogItem,
    BackupCandidateResponse,
    DayCell,
    GridRow,
    ReassignApplyRequest,
    ReassignPreviewRequest,
    ReassignPreviewResponse,
    RosterConflictResponse,
    RosterGenerateRequest,
    RosterGridViewResponse,
    RosterSummaryResponse,
    PodAnalytics,
    WorkforceAnalyticsResponse,
    ResolverBundleResponse,
    ResolverShortageResponse,
    ResolverPreviewResponse,
    ResolverApplyRequest,
    ResolverApplyResponse,
)
from app.modules.workforce.availability_models import (
    EmployeePreference,
    EmployeeUnavailability,
)
from app.modules.workforce.models import (
    Employee,
    EmployeeProcessSkill,
    EmployeeStatus,
    Pod,
    PodLead,
)

router = APIRouter(prefix="/rosters", tags=["Rosters"])


def compute_config_hash(db: Session) -> str:
    """Computes a SHA-256 hash of active rules, assignments, and availability."""
    patterns = db.scalars(select(OperatingPattern)).all()
    assignments = db.scalars(select(PrimaryAssignment).where(PrimaryAssignment.is_active == True)).all()
    unavails = db.scalars(select(EmployeeUnavailability)).all()
    
    parts: list[str] = []
    for p in sorted(patterns, key=lambda x: str(x.brand_process_id)):
        parts.append(f"{p.brand_process_id}:{p.operating_days}:{p.min_staffing_weekday}:{p.min_staffing_weekend}")
    for a in sorted(assignments, key=lambda x: (str(x.employee_id), str(x.brand_process_id))):
        parts.append(f"{a.employee_id}:{a.brand_process_id}:{a.effective_from}")
    for u in sorted(unavails, key=lambda x: (str(x.employee_id), str(x.date))):
        parts.append(f"{u.employee_id}:{u.date}:{u.reason_type}:{u.is_approved}")
    
    return hashlib.sha256(";".join(parts).encode("utf-8")).hexdigest()


def check_and_mark_stale_rosters(db: Session, current_hash: str) -> None:
    """Marks any unpublished roster whose config_hash doesn't match current_hash as STALE."""
    unpub = db.scalars(
        select(Roster).where(Roster.status.in_([RosterStatus.DRAFT, RosterStatus.VALIDATED]))
    ).all()
    for r in unpub:
        if r.config_hash and r.config_hash != current_hash:
            r.status = RosterStatus.STALE


@router.post("/generate", response_model=RosterSummaryResponse, status_code=status.HTTP_201_CREATED)
def generate_roster(
    payload: RosterGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> RosterSummaryResponse:
    # 1. Fetch DB records into pure domain specs
    employees = db.scalars(
        select(Employee)
        .options(selectinload(Employee.process_skills))
        .where(Employee.status == EmployeeStatus.ACTIVE)
    ).all()
    emp_map: dict[uuid.UUID, EmployeeSpec] = {}
    for e in employees:
        skills = frozenset([s.process_id for s in e.process_skills if s.is_active])
        emp_map[e.id] = EmployeeSpec(
            id=e.id,
            name=e.name,
            email=e.email,
            pod_id=e.pod_id,
            daily_capacity_minutes=e.daily_capacity_minutes,
            standard_start_time=e.standard_start_time,
            standard_end_time=e.standard_end_time,
            skill_process_ids=skills,
            is_active=True,
        )

    bps = db.scalars(
        select(BrandProcess)
        .where(BrandProcess.is_active == True)
    ).all()
    bp_list = [(bp.id, bp.brand_id, bp.process_id) for bp in bps]

    patterns_db = db.scalars(select(OperatingPattern)).all()
    patterns_map: dict[uuid.UUID, OperatingPatternSpec] = {}
    for p in patterns_db:
        op_days = tuple(int(d.strip()) for d in p.operating_days.split(",") if d.strip())
        h_behav = EngineHolidayBehavior(p.holiday_behavior.value)
        patterns_map[p.brand_process_id] = OperatingPatternSpec(
            brand_process_id=p.brand_process_id,
            operating_days=op_days,
            start_time=p.start_time,
            end_time=p.end_time,
            min_staffing_weekday=p.min_staffing_weekday,
            min_staffing_weekend=p.min_staffing_weekend,
            holiday_behavior=h_behav,
            min_staffing_holiday=p.min_staffing_holiday,
        )

    # Overrides in target month
    num_days = calendar.monthrange(payload.year, payload.month)[1]
    m_start = date(payload.year, payload.month, 1)
    m_end = date(payload.year, payload.month, num_days)

    overrides_db = db.scalars(
        select(OperatingOverride).where(
            OperatingOverride.date >= m_start, OperatingOverride.date <= m_end
        )
    ).all()
    overrides_map: dict[tuple[uuid.UUID, date], OperatingOverrideSpec] = {
        (o.brand_process_id, o.date): OperatingOverrideSpec(
            brand_process_id=o.brand_process_id,
            date=o.date,
            is_closed=o.is_closed,
            override_start_time=o.override_start_time,
            override_end_time=o.override_end_time,
            override_min_staffing=o.override_min_staffing,
            reason=o.reason,
        )
        for o in overrides_db
    }

    holidays_db = db.scalars(
        select(Holiday).where(Holiday.date >= m_start, Holiday.date <= m_end)
    ).all()
    holidays_set = {h.date for h in holidays_db}

    assignments_db = db.scalars(
        select(PrimaryAssignment).where(PrimaryAssignment.is_active == True)
    ).all()
    primaries: list[PrimaryAssignmentSpec] = [
        PrimaryAssignmentSpec(
            employee_id=a.employee_id,
            brand_process_id=a.brand_process_id,
            priority=a.priority,
            effective_from=a.effective_from,
            effective_to=a.effective_to,
        )
        for a in assignments_db
    ]

    unavails_db = db.scalars(
        select(EmployeeUnavailability).where(
            EmployeeUnavailability.date >= m_start, EmployeeUnavailability.date <= m_end
        )
    ).all()
    unavails_map: dict[tuple[uuid.UUID, date], UnavailabilitySpec] = {
        (u.employee_id, u.date): UnavailabilitySpec(
            employee_id=u.employee_id,
            date=u.date,
            reason_type=u.reason_type.value,
            is_approved=u.is_approved,
        )
        for u in unavails_db
    }

    prefs_db = db.scalars(select(EmployeePreference)).all()
    prefs_map: dict[uuid.UUID, PreferenceSpec] = {
        p.employee_id: PreferenceSpec(
            employee_id=p.employee_id,
            preferred_weekly_off_days=tuple(
                int(d.strip()) for d in p.preferred_weekly_off_days.split(",") if d.strip()
            ),
        )
        for p in prefs_db
    }

    # 2. Run deterministic scheduling
    result = DeterministicScheduler.generate_monthly_roster(
        year=payload.year,
        month=payload.month,
        brand_processes=bp_list,
        patterns=patterns_map,
        overrides=overrides_map,
        company_holidays=holidays_set,
        employees=emp_map,
        primary_assignments=primaries,
        unavailabilities=unavails_map,
        preferences=prefs_map,
    )

    # 3. Run independent validator
    all_dates = [date(payload.year, payload.month, d) for d in range(1, num_days + 1)]
    validation_conflicts = IndependentValidator.validate_roster(
        all_dates=all_dates,
        brand_processes=bp_list,
        patterns=patterns_map,
        overrides=overrides_map,
        company_holidays=holidays_set,
        employees=emp_map,
        unavailabilities=unavails_map,
        shifts=result.shifts,
        allocations=result.allocations,
    )

    # Combine conflicts (deduplicated by type, date, bp_id, emp_id)
    all_conflicts = list(result.conflicts)
    for vc in validation_conflicts:
        exists = any(
            c.conflict_type == vc.conflict_type
            and c.date == vc.date
            and c.brand_process_id == vc.brand_process_id
            and c.employee_id == vc.employee_id
            for c in all_conflicts
        )
        if not exists:
            all_conflicts.append(vc)

    # Determine status: VALIDATED if 0 hard violations, else DRAFT
    has_hard_violations = any(c.severity == EngineConflictSeverity.HARD_VIOLATION for c in all_conflicts)
    initial_status = RosterStatus.DRAFT if has_hard_violations else RosterStatus.VALIDATED

    # Calculate version: check existing rosters for this month/year
    existing_count = db.scalar(
        select(func.count()).select_from(Roster).where(Roster.month == payload.month, Roster.year == payload.year)
    ) or 0
    version = existing_count + 1

    current_hash = compute_config_hash(db)

    # Auto-sync roster name with selected month to prevent stale "November" label for December
    roster_name = payload.name
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
    }
    target_month_name = month_names.get(payload.month, "")
    for m_idx, m_name in month_names.items():
        if m_idx != payload.month and m_name in roster_name:
            roster_name = roster_name.replace(m_name, target_month_name)

    roster = Roster(
        id=uuid.uuid4(),
        name=roster_name,
        month=payload.month,
        year=payload.year,
        version=version,
        status=initial_status,
        config_hash=current_hash,
        created_by=current_user.email,
    )
    db.add(roster)
    db.flush()

    # Persist Shifts
    shift_entity_map: dict[tuple[uuid.UUID, date], uuid.UUID] = {}
    for s in result.shifts:
        shift_entity = EmployeeShift(
            id=s.id,
            roster_id=roster.id,
            employee_id=s.employee_id,
            date=s.date,
            start_time=s.interval.start_time,
            end_time=s.interval.end_time,
            is_working_day=s.is_working_day,
        )
        db.add(shift_entity)
        shift_entity_map[(s.employee_id, s.date)] = s.id

    db.flush()

    # Persist Allocations
    for a in result.allocations:
        shift_id = shift_entity_map.get((a.employee_id, a.date))
        if not shift_id:
            continue
        alloc_entity = RosterAllocation(
            id=a.id,
            roster_id=roster.id,
            shift_id=shift_id,
            employee_id=a.employee_id,
            brand_process_id=a.brand_process_id,
            date=a.date,
            start_time=a.interval.start_time,
            end_time=a.interval.end_time,
            allocation_type=AllocationType(a.allocation_type.value),
            reassigned_from_employee_id=a.reassigned_from_employee_id,
            is_cross_pod_approved=a.is_cross_pod_approved,
            reassignment_reason=a.notes,
        )
        db.add(alloc_entity)

    # Persist Conflicts
    for c in all_conflicts:
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

    db.commit()

    return RosterSummaryResponse(
        id=roster.id,
        name=roster.name,
        month=roster.month,
        year=roster.year,
        version=roster.version,
        parent_roster_id=roster.parent_roster_id,
        status=roster.status,
        config_hash=roster.config_hash,
        created_by=roster.created_by,
        created_at=roster.created_at,
        published_at=roster.published_at,
        total_shifts=len(result.shifts),
        total_allocations=len(result.allocations),
        total_conflicts=len(all_conflicts),
        hard_violations_count=sum(1 for c in all_conflicts if c.severity == EngineConflictSeverity.HARD_VIOLATION),
        soft_warnings_count=sum(1 for c in all_conflicts if c.severity == EngineConflictSeverity.SOFT_WARNING),
    )


@router.get("", response_model=list[RosterSummaryResponse])
def list_rosters(
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> list[RosterSummaryResponse]:
    current_hash = compute_config_hash(db)
    check_and_mark_stale_rosters(db, current_hash)
    db.commit()

    query = select(Roster).order_by(Roster.created_at.desc(), Roster.version.desc())
    if month is not None:
        query = query.where(Roster.month == month)
    if year is not None:
        query = query.where(Roster.year == year)

    pod_emp_ids: set[uuid.UUID] = set()
    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        pod_emp_ids = set(db.scalars(select(Employee.id).where(Employee.pod_id == _user.pod_id)).all())

    rosters = db.scalars(query).all()
    results = []
    for r in rosters:
        if _user.role == UserRole.POD_LEAD and pod_emp_ids:
            shifts_count = db.scalar(select(func.count()).select_from(EmployeeShift).where(EmployeeShift.roster_id == r.id, EmployeeShift.employee_id.in_(pod_emp_ids))) or 0
            allocs_count = db.scalar(select(func.count()).select_from(RosterAllocation).where(RosterAllocation.roster_id == r.id, RosterAllocation.employee_id.in_(pod_emp_ids))) or 0
            conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == r.id, RosterConflict.employee_id.in_(pod_emp_ids))).all()
        else:
            shifts_count = db.scalar(select(func.count()).select_from(EmployeeShift).where(EmployeeShift.roster_id == r.id)) or 0
            allocs_count = db.scalar(select(func.count()).select_from(RosterAllocation).where(RosterAllocation.roster_id == r.id)) or 0
            conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == r.id)).all()
        results.append(
            RosterSummaryResponse(
                id=r.id,
                name=r.name,
                month=r.month,
                year=r.year,
                version=r.version,
                parent_roster_id=r.parent_roster_id,
                status=r.status,
                config_hash=r.config_hash,
                created_by=r.created_by,
                created_at=r.created_at,
                published_at=r.published_at,
                total_shifts=shifts_count,
                total_allocations=allocs_count,
                total_conflicts=len(conflicts),
                hard_violations_count=sum(1 for c in conflicts if c.severity == ConflictSeverity.HARD_VIOLATION),
                soft_warnings_count=sum(1 for c in conflicts if c.severity == ConflictSeverity.SOFT_WARNING),
            )
        )
    return results


@router.get("/{roster_id}", response_model=RosterSummaryResponse)
def get_roster(
    roster_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> RosterSummaryResponse:
    r = db.get(Roster, roster_id)
    if not r:
        raise HTTPException(status_code=404, detail="Roster not found")

    pod_emp_ids: set[uuid.UUID] = set()
    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        pod_emp_ids = set(db.scalars(select(Employee.id).where(Employee.pod_id == _user.pod_id)).all())

    if _user.role == UserRole.POD_LEAD and pod_emp_ids:
        shifts_count = db.scalar(select(func.count()).select_from(EmployeeShift).where(EmployeeShift.roster_id == r.id, EmployeeShift.employee_id.in_(pod_emp_ids))) or 0
        allocs_count = db.scalar(select(func.count()).select_from(RosterAllocation).where(RosterAllocation.roster_id == r.id, RosterAllocation.employee_id.in_(pod_emp_ids))) or 0
        conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == r.id, RosterConflict.employee_id.in_(pod_emp_ids))).all()
    else:
        shifts_count = db.scalar(select(func.count()).select_from(EmployeeShift).where(EmployeeShift.roster_id == r.id)) or 0
        allocs_count = db.scalar(select(func.count()).select_from(RosterAllocation).where(RosterAllocation.roster_id == r.id)) or 0
        conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == r.id)).all()
    return RosterSummaryResponse(
        id=r.id,
        name=r.name,
        month=r.month,
        year=r.year,
        version=r.version,
        parent_roster_id=r.parent_roster_id,
        status=r.status,
        config_hash=r.config_hash,
        created_by=r.created_by,
        created_at=r.created_at,
        published_at=r.published_at,
        shift_count=shifts_count,
        allocation_count=allocs_count,
        total_conflicts=len(conflicts),
        hard_violations_count=sum(1 for c in conflicts if c.severity == ConflictSeverity.HARD_VIOLATION),
        soft_warnings_count=sum(1 for c in conflicts if c.severity == ConflictSeverity.SOFT_WARNING),
    )


@router.post("/{roster_id}/publish", response_model=RosterSummaryResponse)
def publish_roster(
    roster_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
) -> RosterSummaryResponse:
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    if roster.status == RosterStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Roster is already published and immutable")

    # Verify not STALE
    current_hash = compute_config_hash(db)
    if roster.config_hash != current_hash:
        roster.status = RosterStatus.STALE
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="Roster configuration is STALE. Please regenerate/refresh before publishing.",
        )

    # Verify zero hard violations
    hard_conflicts = db.scalars(
        select(RosterConflict).where(
            RosterConflict.roster_id == roster.id,
            RosterConflict.severity == ConflictSeverity.HARD_VIOLATION,
            RosterConflict.is_resolved == False,
        )
    ).all()
    if hard_conflicts:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot publish roster with {len(hard_conflicts)} unresolved hard constraint violations.",
        )

    roster.status = RosterStatus.PUBLISHED
    roster.published_at = datetime.now()
    db.commit()

    return RosterSummaryResponse(
        id=roster.id,
        name=roster.name,
        month=roster.month,
        year=roster.year,
        version=roster.version,
        parent_roster_id=roster.parent_roster_id,
        status=roster.status,
        config_hash=roster.config_hash,
        created_by=roster.created_by,
        created_at=roster.created_at,
        published_at=roster.published_at,
    )


@router.post("/{roster_id}/create-child-version", response_model=RosterSummaryResponse)
def create_child_version(
    roster_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> RosterSummaryResponse:
    parent = db.get(Roster, roster_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Roster not found")

    new_version = parent.version + 1
    child_roster = Roster(
        id=uuid.uuid4(),
        name=f"{parent.name} (v{new_version})",
        month=parent.month,
        year=parent.year,
        version=new_version,
        parent_roster_id=parent.id,
        status=RosterStatus.DRAFT,
        config_hash=compute_config_hash(db),
        created_by=current_user.email,
    )
    db.add(child_roster)
    db.flush()

    # Clone shifts & allocations
    parent_shifts = db.scalars(select(EmployeeShift).where(EmployeeShift.roster_id == parent.id)).all()
    shift_map: dict[uuid.UUID, uuid.UUID] = {}
    for s in parent_shifts:
        new_shift = EmployeeShift(
            id=uuid.uuid4(),
            roster_id=child_roster.id,
            employee_id=s.employee_id,
            date=s.date,
            start_time=s.start_time,
            end_time=s.end_time,
            is_working_day=s.is_working_day,
        )
        db.add(new_shift)
        shift_map[s.id] = new_shift.id

    db.flush()

    parent_allocs = db.scalars(select(RosterAllocation).where(RosterAllocation.roster_id == parent.id)).all()
    for a in parent_allocs:
        new_shift_id = shift_map.get(a.shift_id)
        if not new_shift_id:
            continue
        new_alloc = RosterAllocation(
            id=uuid.uuid4(),
            roster_id=child_roster.id,
            shift_id=new_shift_id,
            employee_id=a.employee_id,
            brand_process_id=a.brand_process_id,
            date=a.date,
            start_time=a.start_time,
            end_time=a.end_time,
            allocation_type=a.allocation_type,
            reassigned_from_employee_id=a.reassigned_from_employee_id,
            is_cross_pod_approved=a.is_cross_pod_approved,
            reassignment_reason=a.reassignment_reason,
        )
        db.add(new_alloc)

    db.commit()

    return RosterSummaryResponse(
        id=child_roster.id,
        name=child_roster.name,
        month=child_roster.month,
        year=child_roster.year,
        version=child_roster.version,
        parent_roster_id=child_roster.parent_roster_id,
        status=child_roster.status,
        config_hash=child_roster.config_hash,
        created_by=child_roster.created_by,
        created_at=child_roster.created_at,
        published_at=child_roster.published_at,
    )


# ---------------------------------------------------------------------
# Unified Grid View Endpoint (Serves all 5 views)
# ---------------------------------------------------------------------

@router.get("/{roster_id}/grid", response_model=RosterGridViewResponse)
def get_roster_grid(
    roster_id: uuid.UUID,
    view_type: str = Query("company", pattern="^(company|pod|brand|process|employee)$"),
    filter_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> RosterGridViewResponse:
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    num_days = calendar.monthrange(roster.year, roster.month)[1]
    dates = [f"{roster.year:04d}-{roster.month:02d}-{d:02d}" for d in range(1, num_days + 1)]

    # Fetch all shifts, allocations, conflicts, brands, processes, employees, pods
    shifts = db.scalars(select(EmployeeShift).where(EmployeeShift.roster_id == roster.id)).all()
    allocs = db.scalars(
        select(RosterAllocation)
        .options(
            selectinload(RosterAllocation.shift),
        )
        .where(RosterAllocation.roster_id == roster.id)
    ).all()
    conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == roster.id)).all()

    employees = {e.id: e for e in db.scalars(select(Employee)).all()}
    pods = {p.id: p for p in db.scalars(select(Pod)).all()}
    bps = {bp.id: bp for bp in db.scalars(select(BrandProcess)).all()}
    brands = {b.id: b for b in db.scalars(select(Brand)).all()}
    processes = {pr.id: pr for pr in db.scalars(select(Process)).all()}

    # Build DayCells map: (row_id, date_str) -> DayCell
    # Pivot rows depending on view_type:
    # 1. 'company' or 'employee': Rows are Employees grouped by Pod
    # 2. 'pod': Rows are Employees belonging to specified Pod
    # 3. 'brand': Rows are BrandProcesses grouped by Brand
    # 4. 'process': Rows are BrandProcesses grouped by Process
    rows: list[GridRow] = []

    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        # Pod Lead is strictly restricted to viewing employees and conflicts within their own pod
        pod_emp_ids = {e.id for e in employees.values() if e.pod_id == _user.pod_id}
        conflicts = [c for c in conflicts if c.employee_id in pod_emp_ids]
        shifts = [s for s in shifts if s.employee_id in pod_emp_ids]
        allocs = [a for a in allocs if a.employee_id in pod_emp_ids]
        if view_type == "employee":
            if filter_id and filter_id in pod_emp_ids:
                pass
            elif _user.employee_id and _user.employee_id in pod_emp_ids:
                filter_id = _user.employee_id
            else:
                filter_id = None
        else:
            filter_id = _user.pod_id

    if view_type in ("company", "employee", "pod"):
        target_employees = list(employees.values())
        if _user.role == UserRole.POD_LEAD and _user.pod_id:
            target_employees = [e for e in target_employees if e.pod_id == _user.pod_id]
            if view_type == "employee" and filter_id:
                target_employees = [e for e in target_employees if e.id == filter_id]
        elif view_type == "pod" and filter_id:
            target_employees = [e for e in target_employees if e.pod_id == filter_id]
        elif view_type == "employee" and filter_id:
            target_employees = [e for e in target_employees if e.id == filter_id]

        target_employees.sort(key=lambda e: (str(e.pod_id or ""), e.name))

        for emp in target_employees:
            pod_name = pods[emp.pod_id].name if emp.pod_id and emp.pod_id in pods else "Unassigned Pod"
            emp_shifts = {s.date.isoformat(): s for s in shifts if s.employee_id == emp.id}
            emp_allocs: dict[str, list[AllocationCell]] = {}
            for a in allocs:
                if a.employee_id == emp.id:
                    d_str = a.date.isoformat()
                    bp = bps.get(a.brand_process_id)
                    b_name = brands[bp.brand_id].name if bp and bp.brand_id in brands else "Unknown Brand"
                    p_name = processes[bp.process_id].name if bp and bp.process_id in processes else "Unknown Process"
                    cell = AllocationCell(
                        allocation_id=a.id,
                        brand_process_id=a.brand_process_id,
                        brand_id=bp.brand_id if bp else uuid.uuid4(),
                        brand_name=b_name,
                        process_id=bp.process_id if bp else uuid.uuid4(),
                        process_name=p_name,
                        employee_id=emp.id,
                        employee_name=emp.name,
                        start_time=a.start_time.strftime("%H:%M"),
                        end_time=a.end_time.strftime("%H:%M"),
                        allocation_type=a.allocation_type,
                        reassigned_from_employee_id=a.reassigned_from_employee_id,
                        is_cross_pod_approved=a.is_cross_pod_approved,
                    )
                    emp_allocs.setdefault(d_str, []).append(cell)

            days_dict: dict[str, DayCell] = {}
            for d_str in dates:
                d_obj = date.fromisoformat(d_str)
                shift = emp_shifts.get(d_str)
                d_allocs = emp_allocs.get(d_str, [])
                days_dict[d_str] = DayCell(
                    date=d_str,
                    day_of_week=d_obj.weekday(),
                    is_working=shift is not None and shift.is_working_day,
                    shift_start=shift.start_time.strftime("%H:%M") if shift else None,
                    shift_end=shift.end_time.strftime("%H:%M") if shift else None,
                    allocations=d_allocs,
                )

            rows.append(
                GridRow(
                    row_id=str(emp.id),
                    row_type="EMPLOYEE",
                    title=emp.name,
                    subtitle=emp.email,
                    group_id=str(emp.pod_id) if emp.pod_id else None,
                    group_name=pod_name,
                    days=days_dict,
                )
            )

    elif view_type == "brand":
        target_bps = list(bps.values())
        if filter_id:
            target_bps = [bp for bp in target_bps if bp.brand_id == filter_id]

        target_bps.sort(key=lambda bp: (str(bp.brand_id), str(bp.process_id)))

        for bp in target_bps:
            b_name = brands[bp.brand_id].name if bp.brand_id in brands else "Unknown Brand"
            p_name = processes[bp.process_id].name if bp.process_id in processes else "Unknown Process"
            bp_allocs: dict[str, list[AllocationCell]] = {}
            for a in allocs:
                if a.brand_process_id == bp.id:
                    d_str = a.date.isoformat()
                    emp = employees.get(a.employee_id)
                    cell = AllocationCell(
                        allocation_id=a.id,
                        brand_process_id=bp.id,
                        brand_id=bp.brand_id,
                        brand_name=b_name,
                        process_id=bp.process_id,
                        process_name=p_name,
                        employee_id=a.employee_id,
                        employee_name=emp.name if emp else "Unknown",
                        start_time=a.start_time.strftime("%H:%M"),
                        end_time=a.end_time.strftime("%H:%M"),
                        allocation_type=a.allocation_type,
                        reassigned_from_employee_id=a.reassigned_from_employee_id,
                        is_cross_pod_approved=a.is_cross_pod_approved,
                    )
                    bp_allocs.setdefault(d_str, []).append(cell)

            days_dict = {}
            for d_str in dates:
                d_obj = date.fromisoformat(d_str)
                d_allocs = bp_allocs.get(d_str, [])
                days_dict[d_str] = DayCell(
                    date=d_str,
                    day_of_week=d_obj.weekday(),
                    is_working=len(d_allocs) > 0,
                    allocations=d_allocs,
                )

            rows.append(
                GridRow(
                    row_id=str(bp.id),
                    row_type="BRAND_PROCESS",
                    title=f"{b_name} — {p_name}",
                    subtitle=f"Brand: {b_name}",
                    group_id=str(bp.brand_id),
                    group_name=b_name,
                    days=days_dict,
                )
            )

    elif view_type == "process":
        target_bps = list(bps.values())
        if filter_id:
            target_bps = [bp for bp in target_bps if bp.process_id == filter_id]

        target_bps.sort(key=lambda bp: (str(bp.process_id), str(bp.brand_id)))

        for bp in target_bps:
            b_name = brands[bp.brand_id].name if bp.brand_id in brands else "Unknown Brand"
            p_name = processes[bp.process_id].name if bp.process_id in processes else "Unknown Process"
            bp_allocs = {}
            for a in allocs:
                if a.brand_process_id == bp.id:
                    d_str = a.date.isoformat()
                    emp = employees.get(a.employee_id)
                    cell = AllocationCell(
                        allocation_id=a.id,
                        brand_process_id=bp.id,
                        brand_id=bp.brand_id,
                        brand_name=b_name,
                        process_id=bp.process_id,
                        process_name=p_name,
                        employee_id=a.employee_id,
                        employee_name=emp.name if emp else "Unknown",
                        start_time=a.start_time.strftime("%H:%M"),
                        end_time=a.end_time.strftime("%H:%M"),
                        allocation_type=a.allocation_type,
                        reassigned_from_employee_id=a.reassigned_from_employee_id,
                        is_cross_pod_approved=a.is_cross_pod_approved,
                    )
                    bp_allocs.setdefault(d_str, []).append(cell)

            days_dict = {}
            for d_str in dates:
                d_obj = date.fromisoformat(d_str)
                d_allocs = bp_allocs.get(d_str, [])
                days_dict[d_str] = DayCell(
                    date=d_str,
                    day_of_week=d_obj.weekday(),
                    is_working=len(d_allocs) > 0,
                    allocations=d_allocs,
                )

            rows.append(
                GridRow(
                    row_id=str(bp.id),
                    row_type="PROCESS_BRAND",
                    title=f"{p_name} ({b_name})",
                    subtitle=f"Process: {p_name}",
                    group_id=str(bp.process_id),
                    group_name=p_name,
                    days=days_dict,
                )
            )

    # Map primary pods for brand processes
    primaries_active = db.scalars(select(PrimaryAssignment).where(PrimaryAssignment.is_active == True)).all()
    bp_pod_map: dict[uuid.UUID, uuid.UUID | None] = {}
    for pa in primaries_active:
        if pa.brand_process_id not in bp_pod_map:
            emp = employees.get(pa.employee_id)
            if emp and emp.pod_id:
                bp_pod_map[pa.brand_process_id] = emp.pod_id

    # Fallback to skills
    emp_skills = db.scalars(select(EmployeeProcessSkill)).all()
    bp_process_to_pod: dict[uuid.UUID, uuid.UUID] = {}
    for s in emp_skills:
        emp = employees.get(s.employee_id)
        if emp and emp.pod_id and s.process_id not in bp_process_to_pod:
            bp_process_to_pod[s.process_id] = emp.pod_id

    for bp in bps.values():
        if bp.id not in bp_pod_map and bp.process_id in bp_process_to_pod:
            bp_pod_map[bp.id] = bp_process_to_pod[bp.process_id]

    conflict_responses: list[RosterConflictResponse] = []
    for c in conflicts:
        b_name = None
        p_name = None
        c_pod_id = None
        c_pod_name = None

        if c.brand_process_id and c.brand_process_id in bps:
            bp = bps[c.brand_process_id]
            b_name = brands[bp.brand_id].name if bp.brand_id in brands else None
            p_name = processes[bp.process_id].name if bp.process_id in processes else None
            c_pod_id = bp_pod_map.get(bp.id)
            if c_pod_id and c_pod_id in pods:
                c_pod_name = pods[c_pod_id].name
            elif bp.process_id in bp_process_to_pod and bp_process_to_pod[bp.process_id] in pods:
                c_pod_id = bp_process_to_pod[bp.process_id]
                c_pod_name = pods[c_pod_id].name

        if not c_pod_id and c.employee_id and c.employee_id in employees:
            emp = employees[c.employee_id]
            if emp.pod_id and emp.pod_id in pods:
                c_pod_id = emp.pod_id
                c_pod_name = pods[c_pod_id].name

        # Fallback for pod assignment if not resolved
        if not c_pod_name and pods:
            first_pod = next(iter(pods.values()))
            c_pod_name = first_pod.name
            c_pod_id = first_pod.id

        # Enrich description with operational context if not already present
        desc = c.description
        if p_name and f"Process:" not in desc and f"Skill:" not in desc:
            desc = f"{desc} (Process / Skill: {p_name}{f', Brand: {b_name}' if b_name else ''}{f', Pod: {c_pod_name}' if c_pod_name else ''})"

        conflict_responses.append(
            RosterConflictResponse(
                id=c.id,
                date=c.date,
                brand_process_id=c.brand_process_id,
                employee_id=c.employee_id,
                start_time=c.start_time,
                end_time=c.end_time,
                severity=c.severity,
                conflict_type=c.conflict_type,
                description=desc,
                is_resolved=c.is_resolved,
                brand_name=b_name or "General Brand",
                process_name=p_name or "Core Process",
                required_skill=p_name or "Operating Skill",
                pod_name=c_pod_name,
                pod_id=c_pod_id,
            )
        )

    return RosterGridViewResponse(
        roster_id=roster.id,
        month=roster.month,
        year=roster.year,
        version=roster.version,
        status=roster.status,
        view_type=view_type,
        dates=dates,
        rows=rows,
        summary_conflicts=conflict_responses,
    )


class GoogleSheetsExportRequest(BaseModel):
    view_type: str = Field(default="company", pattern="^(company|pod|brand|process|employee)$")
    filter_id: uuid.UUID | None = None
    google_access_token: str | None = None


class GoogleSheetsExportResponse(BaseModel):
    spreadsheet_id: str
    spreadsheet_url: str
    title: str
    rows_exported: int


def extract_roster_export_dataset(
    roster_id: uuid.UUID,
    view_type: str,
    filter_id: uuid.UUID | None,
    db: Session,
    _user: User,
) -> tuple[Roster, list[str], list[dict[str, str]]]:
    """Extracts and formats roster data rows while strictly enforcing RBAC and tenant scoping."""
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    num_days = calendar.monthrange(roster.year, roster.month)[1]
    dates = [f"{roster.year:04d}-{roster.month:02d}-{d:02d}" for d in range(1, num_days + 1)]

    shifts = db.scalars(select(EmployeeShift).where(EmployeeShift.roster_id == roster.id)).all()
    allocs = db.scalars(
        select(RosterAllocation)
        .options(selectinload(RosterAllocation.shift))
        .where(RosterAllocation.roster_id == roster.id)
    ).all()

    employees = {e.id: e for e in db.scalars(select(Employee)).all()}
    pods = {p.id: p for p in db.scalars(select(Pod)).all()}
    bps = {bp.id: bp for bp in db.scalars(select(BrandProcess)).all()}
    brands = {b.id: b for b in db.scalars(select(Brand)).all()}
    processes = {pr.id: pr for pr in db.scalars(select(Process)).all()}

    # RBAC & Tenant Scoping
    if _user.role == UserRole.POD_LEAD:
        if not _user.pod_id:
            raise AppError("FORBIDDEN", "Pod Lead has no assigned pod.", 403)
        if view_type in ("company", "brand", "process"):
            raise AppError("FORBIDDEN", "Pod Leads can only export their authorized pod.", 403)
        if view_type == "pod":
            if filter_id and filter_id != _user.pod_id:
                raise AppError("FORBIDDEN", "Pod Leads can only export their authorized pod.", 403)
            filter_id = _user.pod_id
        elif view_type == "employee":
            if filter_id:
                target_emp = employees.get(filter_id)
                if not target_emp or target_emp.pod_id != _user.pod_id:
                    raise AppError("FORBIDDEN", "Pod Leads can only export employees in their authorized pod.", 403)
            else:
                view_type = "pod"
                filter_id = _user.pod_id

    elif _user.role == UserRole.BRAND_USER:
        if not _user.brand_id:
            raise AppError("FORBIDDEN", "Brand User has no assigned brand.", 403)
        if view_type != "brand":
            raise AppError("FORBIDDEN", "Brand users can only export their own brand.", 403)
        if filter_id and filter_id != _user.brand_id:
            raise AppError("FORBIDDEN", "Brand users can only export their own brand.", 403)
        filter_id = _user.brand_id

    elif _user.role == UserRole.EMPLOYEE:
        if not _user.employee_id:
            raise AppError("FORBIDDEN", "Employee user has no linked employee record.", 403)
        if view_type != "employee":
            raise AppError("FORBIDDEN", "Employees can only export their own assignments.", 403)
        if filter_id and filter_id != _user.employee_id:
            raise AppError("FORBIDDEN", "Employees can only export their own assignments.", 403)
        filter_id = _user.employee_id

    elif _user.role in (UserRole.ADMIN, UserRole.OPERATIONS_MANAGER):
        pass
    else:
        raise AppError("FORBIDDEN", "You do not have permission to export rosters.", 403)

    fieldnames = [
        "Date",
        "Day of Week",
        "Pod",
        "Employee Code",
        "Employee Name",
        "Brand",
        "Process",
        "Shift Start",
        "Shift End",
        "Allocation Start",
        "Allocation End",
        "Allocation Status",
        "Cross-Pod Approved",
        "Reassigned From",
    ]

    rows_data: list[dict[str, str]] = []

    if view_type in ("company", "pod", "employee"):
        target_employees = list(employees.values())
        if view_type == "pod" and filter_id:
            target_employees = [e for e in target_employees if e.pod_id == filter_id]
        elif view_type == "employee" and filter_id:
            target_employees = [e for e in target_employees if e.id == filter_id]

        target_employees.sort(key=lambda e: (str(e.pod_id or ""), e.name))

        emp_shifts_map = {(s.employee_id, s.date.isoformat()): s for s in shifts}
        emp_allocs_map: dict[tuple[uuid.UUID, str], list[RosterAllocation]] = {}
        for a in allocs:
            emp_allocs_map.setdefault((a.employee_id, a.date.isoformat()), []).append(a)

        for emp in target_employees:
            pod = pods.get(emp.pod_id)
            pod_name = pod.name if pod else "Unassigned Pod"

            for d_str in dates:
                d_obj = date.fromisoformat(d_str)
                day_name = d_obj.strftime("%A")
                shift = emp_shifts_map.get((emp.id, d_str))
                d_allocs = emp_allocs_map.get((emp.id, d_str), [])

                shift_start = shift.start_time.strftime("%H:%M") if shift and shift.start_time else "-"
                shift_end = shift.end_time.strftime("%H:%M") if shift and shift.end_time else "-"

                if d_allocs:
                    for a in d_allocs:
                        bp = bps.get(a.brand_process_id)
                        b_name = brands[bp.brand_id].name if bp and bp.brand_id in brands else "Unknown Brand"
                        p_name = processes[bp.process_id].name if bp and bp.process_id in processes else "Unknown Process"
                        reassigned_from_name = (
                            employees[a.reassigned_from_employee_id].name
                            if a.reassigned_from_employee_id and a.reassigned_from_employee_id in employees
                            else "-"
                        )
                        rows_data.append({
                            "Date": d_str,
                            "Day of Week": day_name,
                            "Pod": pod_name,
                            "Employee Code": emp.employee_code,
                            "Employee Name": emp.name,
                            "Brand": b_name,
                            "Process": p_name,
                            "Shift Start": shift_start,
                            "Shift End": shift_end,
                            "Allocation Start": a.start_time.strftime("%H:%M"),
                            "Allocation End": a.end_time.strftime("%H:%M"),
                            "Allocation Status": a.allocation_type.value if hasattr(a.allocation_type, "value") else str(a.allocation_type),
                            "Cross-Pod Approved": "Yes" if a.is_cross_pod_approved else "No",
                            "Reassigned From": reassigned_from_name,
                        })
                else:
                    alloc_status = "WEEKLY_OFF"
                    if shift and shift.is_working_day:
                        alloc_status = "UNALLOCATED_WORKING_DAY"
                    rows_data.append({
                        "Date": d_str,
                        "Day of Week": day_name,
                        "Pod": pod_name,
                        "Employee Code": emp.employee_code,
                        "Employee Name": emp.name,
                        "Brand": "-",
                        "Process": "-",
                        "Shift Start": shift_start if shift and shift.is_working_day else "-",
                        "Shift End": shift_end if shift and shift.is_working_day else "-",
                        "Allocation Start": "-",
                        "Allocation End": "-",
                        "Allocation Status": alloc_status,
                        "Cross-Pod Approved": "No",
                        "Reassigned From": "-",
                    })

    elif view_type == "brand":
        target_bps = list(bps.values())
        if filter_id:
            target_bps = [bp for bp in target_bps if bp.brand_id == filter_id]

        target_bps.sort(key=lambda bp: (str(bp.brand_id), str(bp.process_id)))

        bp_allocs_map: dict[tuple[uuid.UUID, str], list[RosterAllocation]] = {}
        for a in allocs:
            bp_allocs_map.setdefault((a.brand_process_id, a.date.isoformat()), []).append(a)

        for bp in target_bps:
            b_name = brands[bp.brand_id].name if bp.brand_id in brands else "Unknown Brand"
            p_name = processes[bp.process_id].name if bp.process_id in processes else "Unknown Process"

            for d_str in dates:
                d_obj = date.fromisoformat(d_str)
                day_name = d_obj.strftime("%A")
                d_allocs = bp_allocs_map.get((bp.id, d_str), [])

                if d_allocs:
                    for a in d_allocs:
                        emp = employees.get(a.employee_id)
                        pod = pods.get(emp.pod_id) if emp and emp.pod_id else None
                        pod_name = pod.name if pod else "-"
                        emp_code = emp.employee_code if emp else "-"
                        emp_name = emp.name if emp else "Unassigned"
                        reassigned_from_name = (
                            employees[a.reassigned_from_employee_id].name
                            if a.reassigned_from_employee_id and a.reassigned_from_employee_id in employees
                            else "-"
                        )
                        rows_data.append({
                            "Date": d_str,
                            "Day of Week": day_name,
                            "Pod": pod_name,
                            "Employee Code": emp_code,
                            "Employee Name": emp_name,
                            "Brand": b_name,
                            "Process": p_name,
                            "Shift Start": a.start_time.strftime("%H:%M"),
                            "Shift End": a.end_time.strftime("%H:%M"),
                            "Allocation Start": a.start_time.strftime("%H:%M"),
                            "Allocation End": a.end_time.strftime("%H:%M"),
                            "Allocation Status": a.allocation_type.value if hasattr(a.allocation_type, "value") else str(a.allocation_type),
                            "Cross-Pod Approved": "Yes" if a.is_cross_pod_approved else "No",
                            "Reassigned From": reassigned_from_name,
                        })
                else:
                    rows_data.append({
                        "Date": d_str,
                        "Day of Week": day_name,
                        "Pod": "-",
                        "Employee Code": "-",
                        "Employee Name": "-",
                        "Brand": b_name,
                        "Process": p_name,
                        "Shift Start": "-",
                        "Shift End": "-",
                        "Allocation Start": "-",
                        "Allocation End": "-",
                        "Allocation Status": "CLOSED_OR_UNALLOCATED",
                        "Cross-Pod Approved": "No",
                        "Reassigned From": "-",
                    })

    elif view_type == "process":
        target_bps = list(bps.values())
        if filter_id:
            target_bps = [bp for bp in target_bps if bp.process_id == filter_id]

        target_bps.sort(key=lambda bp: (str(bp.process_id), str(bp.brand_id)))

        bp_allocs_map = {}
        for a in allocs:
            bp_allocs_map.setdefault((a.brand_process_id, a.date.isoformat()), []).append(a)

        for bp in target_bps:
            b_name = brands[bp.brand_id].name if bp.brand_id in brands else "Unknown Brand"
            p_name = processes[bp.process_id].name if bp.process_id in processes else "Unknown Process"

            for d_str in dates:
                d_obj = date.fromisoformat(d_str)
                day_name = d_obj.strftime("%A")
                d_allocs = bp_allocs_map.get((bp.id, d_str), [])

                if d_allocs:
                    for a in d_allocs:
                        emp = employees.get(a.employee_id)
                        pod = pods.get(emp.pod_id) if emp and emp.pod_id else None
                        pod_name = pod.name if pod else "-"
                        emp_code = emp.employee_code if emp else "-"
                        emp_name = emp.name if emp else "Unassigned"
                        reassigned_from_name = (
                            employees[a.reassigned_from_employee_id].name
                            if a.reassigned_from_employee_id and a.reassigned_from_employee_id in employees
                            else "-"
                        )
                        rows_data.append({
                            "Date": d_str,
                            "Day of Week": day_name,
                            "Pod": pod_name,
                            "Employee Code": emp_code,
                            "Employee Name": emp_name,
                            "Brand": b_name,
                            "Process": p_name,
                            "Shift Start": a.start_time.strftime("%H:%M"),
                            "Shift End": a.end_time.strftime("%H:%M"),
                            "Allocation Start": a.start_time.strftime("%H:%M"),
                            "Allocation End": a.end_time.strftime("%H:%M"),
                            "Allocation Status": a.allocation_type.value if hasattr(a.allocation_type, "value") else str(a.allocation_type),
                            "Cross-Pod Approved": "Yes" if a.is_cross_pod_approved else "No",
                            "Reassigned From": reassigned_from_name,
                        })
                else:
                    rows_data.append({
                        "Date": d_str,
                        "Day of Week": day_name,
                        "Pod": "-",
                        "Employee Code": "-",
                        "Employee Name": "-",
                        "Brand": b_name,
                        "Process": p_name,
                        "Shift Start": "-",
                        "Shift End": "-",
                        "Allocation Start": "-",
                        "Allocation End": "-",
                        "Allocation Status": "CLOSED_OR_UNALLOCATED",
                        "Cross-Pod Approved": "No",
                        "Reassigned From": "-",
                    })

    return roster, fieldnames, rows_data


@router.get("/export/google-sheets/status")
def google_sheets_status(
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Returns whether Google Sheets export is currently configured and operational."""
    from app.modules.roster.sheets_service import get_google_sheets_status
    return get_google_sheets_status()


@router.post("/{roster_id}/export/google-sheets", response_model=GoogleSheetsExportResponse)
def export_roster_google_sheets(
    roster_id: uuid.UUID,
    payload: GoogleSheetsExportRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> GoogleSheetsExportResponse:
    """Exports a specific roster and version to a new Google Spreadsheet using official Sheets API."""
    from app.modules.roster.sheets_service import (
        resolve_google_credentials,
        create_and_format_roster_sheet,
    )

    roster, fieldnames, rows_data = extract_roster_export_dataset(
        roster_id=roster_id,
        view_type=payload.view_type,
        filter_id=payload.filter_id,
        db=db,
        _user=_user,
    )

    credentials = resolve_google_credentials(payload.google_access_token)
    spreadsheet_title = f"{roster.name} - {payload.view_type.capitalize()} View (v{roster.version})"

    result = create_and_format_roster_sheet(
        credentials=credentials,
        spreadsheet_title=spreadsheet_title,
        fieldnames=fieldnames,
        rows_data=rows_data,
    )

    return GoogleSheetsExportResponse(**result)


def sanitize_csv_cell(value: Any) -> str:
    """Sanitizes cell values to prevent CSV formula injection (OWASP CSV Injection defense).

    If the string begins with '=', '+', '-', '@', tab (0x09), or carriage return (0x0D),
    prepends a single quote (') so spreadsheet applications interpret it strictly as plain text.
    Preserves valid CSV escaping, Unicode characters, and converts non-string types.
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val_str}"
    return val_str


def serialize_dataset_to_csv(fieldnames: list[str], rows_data: list[dict[str, Any]]) -> bytes:
    """Serializes dataset rows to RFC 4180 CSV with UTF-8 BOM and formula injection protection."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\r\n")
    writer.writeheader()
    for row in rows_data:
        sanitized_row = {k: sanitize_csv_cell(row.get(k, "")) for k in fieldnames}
        writer.writerow(sanitized_row)

    csv_content = output.getvalue()
    return csv_content.encode("utf-8-sig")


@router.get("/{roster_id}/export/csv")
def export_roster_csv(
    roster_id: uuid.UUID,
    view_type: str = Query("company", pattern="^(company|pod|brand|process|employee)$"),
    filter_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Response:
    """Exports a specific roster and version to downloadable CSV, respecting view type and strict role scoping."""
    roster, fieldnames, rows_data = extract_roster_export_dataset(
        roster_id=roster_id,
        view_type=view_type,
        filter_id=filter_id,
        db=db,
        _user=_user,
    )

    csv_bytes = serialize_dataset_to_csv(fieldnames=fieldnames, rows_data=rows_data)

    safe_name = re.sub(r"[^\w\-_]", "_", roster.name)
    filename = f"roster_{safe_name}_{view_type}_v{roster.version}.csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
    }
    return Response(content=csv_bytes, media_type="text/csv", headers=headers)


# ---------------------------------------------------------------------
# Reassignment Preview & Transactional Apply Endpoints
# ---------------------------------------------------------------------

@router.post("/{roster_id}/reassign/preview", response_model=ReassignPreviewResponse)
def preview_reassignment(
    roster_id: uuid.UUID,
    payload: ReassignPreviewRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> ReassignPreviewResponse:
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    if roster.status == RosterStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Cannot reassign on an immutable published roster")

    target_emp = db.get(Employee, payload.target_employee_id)
    if not target_emp or target_emp.status != EmployeeStatus.ACTIVE:
        return ReassignPreviewResponse(
            is_eligible=False,
            rejection_reason="Target employee is not found or inactive",
            allocation_type=AllocationType.PRIMARY,
            requires_ops_manager_approval=False,
            affected_conflicts_count=0,
        )

    # Scoping for Pod Lead: can only reassign to employees within their own pod
    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        if target_emp.pod_id != _user.pod_id:
            return ReassignPreviewResponse(
                is_eligible=False,
                rejection_reason="Pod leads can only reassign to employees within their own pod",
                allocation_type=AllocationType.PRIMARY,
                requires_ops_manager_approval=False,
                affected_conflicts_count=0,
            )

    bp = db.get(BrandProcess, payload.brand_process_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Brand process not found")

    # Skills check
    has_skill = db.scalar(
        select(select(EmployeeProcessSkill).where(
            EmployeeProcessSkill.employee_id == target_emp.id,
            EmployeeProcessSkill.process_id == bp.process_id,
            EmployeeProcessSkill.is_active == True,
        ).exists())
    )
    if not has_skill:
        return ReassignPreviewResponse(
            is_eligible=False,
            rejection_reason=f"Target employee {target_emp.name} lacks required process skill",
            allocation_type=AllocationType.PRIMARY,
            requires_ops_manager_approval=False,
            affected_conflicts_count=0,
        )

    # Approved leave check
    is_on_leave = db.scalar(
        select(select(EmployeeUnavailability).where(
            EmployeeUnavailability.employee_id == target_emp.id,
            EmployeeUnavailability.date == payload.date,
            EmployeeUnavailability.is_approved == True,
        ).exists())
    )
    if is_on_leave:
        return ReassignPreviewResponse(
            is_eligible=False,
            rejection_reason=f"Target employee {target_emp.name} has approved unavailability on {payload.date}",
            allocation_type=AllocationType.PRIMARY,
            requires_ops_manager_approval=False,
            affected_conflicts_count=0,
        )

    # Shift overlap check
    slot_interval = TimeInterval(payload.start_time, payload.end_time)
    existing_allocs = db.scalars(
        select(RosterAllocation).where(
            RosterAllocation.roster_id == roster.id,
            RosterAllocation.employee_id == target_emp.id,
            RosterAllocation.date == payload.date,
        )
    ).all()
    for ea in existing_allocs:
        ea_interval = TimeInterval(ea.start_time, ea.end_time)
        if ea_interval.overlaps(slot_interval):
            return ReassignPreviewResponse(
                is_eligible=False,
                rejection_reason=f"Target employee {target_emp.name} has overlapping allocation on {payload.date}",
                allocation_type=AllocationType.PRIMARY,
                requires_ops_manager_approval=False,
                affected_conflicts_count=0,
            )

    # Determine same-pod vs cross-pod
    primary_emp_pods = {
        e.pod_id
        for e in db.scalars(
            select(Employee).join(PrimaryAssignment, PrimaryAssignment.employee_id == Employee.id).where(
                PrimaryAssignment.brand_process_id == bp.id
            )
        ).all()
        if e.pod_id
    }
    is_same_pod = target_emp.pod_id in primary_emp_pods if primary_emp_pods else True
    alloc_type = AllocationType.SAME_POD_REASSIGNMENT if is_same_pod else AllocationType.CROSS_POD_REASSIGNMENT
    requires_approval = not is_same_pod

    # Count matching unresolved conflicts that will be cleared
    unresolved_conflicts = db.scalars(
        select(RosterConflict).where(
            RosterConflict.roster_id == roster.id,
            RosterConflict.date == payload.date,
            RosterConflict.brand_process_id == bp.id,
            RosterConflict.is_resolved == False,
        )
    ).all()

    return ReassignPreviewResponse(
        is_eligible=True,
        rejection_reason=None,
        allocation_type=alloc_type,
        requires_ops_manager_approval=requires_approval,
        affected_conflicts_count=len(unresolved_conflicts),
    )


@router.post("/{roster_id}/reassign/apply", status_code=status.HTTP_201_CREATED)
def apply_reassignment(
    roster_id: uuid.UUID,
    payload: ReassignApplyRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
):
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    if roster.status == RosterStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Cannot modify an immutable published roster")

    target_emp = db.get(Employee, payload.target_employee_id)
    if not target_emp or target_emp.status != EmployeeStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Target employee not found or inactive")

    # Scoping for Pod Lead: can only reassign to employees within their own pod
    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        if target_emp.pod_id != _user.pod_id:
            raise HTTPException(status_code=403, detail="Pod leads can only reassign to employees within their own pod")

    preview = preview_reassignment(
        roster_id=roster_id,
        payload=ReassignPreviewRequest(
            date=payload.date,
            brand_process_id=payload.brand_process_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            target_employee_id=payload.target_employee_id,
            source_employee_id=payload.source_employee_id,
        ),
        db=db,
        _user=_user,
    )

    if not preview.is_eligible:
        raise HTTPException(status_code=422, detail=preview.rejection_reason)

    if preview.requires_ops_manager_approval and not payload.confirm_cross_pod_approval:
        raise HTTPException(
            status_code=403,
            detail="Cross-pod reassignment requires explicit Operations Manager authorization (confirm_cross_pod_approval=True).",
        )

    # Find or synthesize employee shift for target on date
    shift = db.scalar(
        select(EmployeeShift).where(
            EmployeeShift.roster_id == roster.id,
            EmployeeShift.employee_id == payload.target_employee_id,
            EmployeeShift.date == payload.date,
        )
    )
    if not shift:
        target_emp = db.get(Employee, payload.target_employee_id)
        shift_start = min(target_emp.standard_start_time, payload.start_time)
        shift_end = max(target_emp.standard_end_time, payload.end_time)
        shift = EmployeeShift(
            id=uuid.uuid4(),
            roster_id=roster.id,
            employee_id=payload.target_employee_id,
            date=payload.date,
            start_time=shift_start,
            end_time=shift_end,
            is_working_day=True,
        )
        db.add(shift)
        db.flush()
    else:
        # Expand shift window if needed
        if payload.start_time < shift.start_time:
            shift.start_time = payload.start_time
        if payload.end_time > shift.end_time:
            shift.end_time = payload.end_time

    # Record authenticated manager's authorization details
    is_approved = True if preview.requires_ops_manager_approval else False
    approver_id = _user.id if is_approved else None
    approved_time = datetime.now() if is_approved else None

    # Create allocation
    alloc = RosterAllocation(
        id=uuid.uuid4(),
        roster_id=roster.id,
        shift_id=shift.id,
        employee_id=payload.target_employee_id,
        brand_process_id=payload.brand_process_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        allocation_type=preview.allocation_type,
        reassigned_from_employee_id=payload.source_employee_id,
        is_cross_pod_approved=is_approved,
        approved_by_user_id=approver_id,
        approved_at=approved_time,
        reassignment_reason=payload.reason,
    )
    db.add(alloc)

    # Resolve uncovered conflicts
    conflicts = db.scalars(
        select(RosterConflict).where(
            RosterConflict.roster_id == roster.id,
            RosterConflict.date == payload.date,
            RosterConflict.brand_process_id == payload.brand_process_id,
            RosterConflict.is_resolved == False,
        )
    ).all()
    for c in conflicts:
        c.is_resolved = True

    db.commit()
    return {"status": "reassigned", "allocation_id": alloc.id, "resolved_conflicts": len(conflicts)}


@router.get("/{roster_id}/backup-candidates", response_model=list[BackupCandidateResponse])
def get_backup_candidates(
    roster_id: uuid.UUID,
    brand_process_id: uuid.UUID,
    target_date: date,
    start_time: time,
    end_time: time,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> list[BackupCandidateResponse]:
    bp = db.get(BrandProcess, brand_process_id)
    if not bp:
        raise HTTPException(status_code=404, detail="Brand process not found")

    primary_emp_pods = {
        e.pod_id
        for e in db.scalars(
            select(Employee).join(PrimaryAssignment, PrimaryAssignment.employee_id == Employee.id).where(
                PrimaryAssignment.brand_process_id == bp.id
            )
        ).all()
        if e.pod_id
    }

    candidates = db.scalars(
        select(Employee)
        .join(EmployeeProcessSkill, EmployeeProcessSkill.employee_id == Employee.id)
        .where(
            Employee.status == EmployeeStatus.ACTIVE,
            EmployeeProcessSkill.process_id == bp.process_id,
            EmployeeProcessSkill.is_active == True,
        )
    ).all()

    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        candidates = [c for c in candidates if c.pod_id == _user.pod_id]

    pods = {p.id: p.name for p in db.scalars(select(Pod)).all()}
    prefs = {p.employee_id: p for p in db.scalars(select(EmployeePreference)).all()}

    results = []
    slot_interval = TimeInterval(start_time, end_time)

    for emp in candidates:
        # Check leave
        on_leave = db.scalar(
            select(select(EmployeeUnavailability).where(
                EmployeeUnavailability.employee_id == emp.id,
                EmployeeUnavailability.date == target_date,
                EmployeeUnavailability.is_approved == True,
            ).exists())
        )
        if on_leave:
            continue

        # Check overlapping allocation
        existing_allocs = db.scalars(
            select(RosterAllocation).where(
                RosterAllocation.roster_id == roster_id,
                RosterAllocation.employee_id == emp.id,
                RosterAllocation.date == target_date,
            )
        ).all()
        has_overlap = any(
            TimeInterval(ea.start_time, ea.end_time).overlaps(slot_interval) for ea in existing_allocs
        )
        if has_overlap:
            continue

        is_same_pod = emp.pod_id in primary_emp_pods if primary_emp_pods else True
        pref = prefs.get(emp.id)
        prefers_off = bool(pref and str(target_date.weekday()) in pref.preferred_weekly_off_days.split(","))

        results.append(
            BackupCandidateResponse(
                employee_id=emp.id,
                name=emp.name,
                pod_id=emp.pod_id,
                pod_name=pods.get(emp.pod_id),
                is_same_pod=is_same_pod,
                requires_approval=not is_same_pod,
                prefers_off_on_day=prefers_off,
            )
        )

    # Sort: same-pod first, prefers_off false first, then name
    results.sort(key=lambda c: (not c.is_same_pod, c.prefers_off_on_day, c.name))
    return results


@router.get("/{roster_id}/allocation-log", response_model=list[AllocationLogItem])
def get_allocation_log(
    roster_id: uuid.UUID,
    dynamic_only: bool = Query(default=False, description="Filter for dynamic reassignments only"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> list[AllocationLogItem]:
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    query = select(RosterAllocation).where(RosterAllocation.roster_id == roster_id)
    if dynamic_only:
        query = query.where(
            RosterAllocation.allocation_type.in_([
                AllocationType.SAME_POD_REASSIGNMENT,
                AllocationType.CROSS_POD_REASSIGNMENT,
            ])
        )
    query = query.order_by(RosterAllocation.created_at.desc(), RosterAllocation.date.desc())

    allocations = db.scalars(query).all()

    # Preload entities for lookup
    employees = {e.id: e for e in db.scalars(select(Employee)).all()}
    if _user.role == UserRole.POD_LEAD and _user.pod_id:
        allocations = [
            a for a in allocations
            if employees.get(a.employee_id) and employees[a.employee_id].pod_id == _user.pod_id
        ]
    pods = {p.id: p.name for p in db.scalars(select(Pod)).all()}
    bps = {bp.id: bp for bp in db.scalars(select(BrandProcess)).all()}
    brands = {b.id: b.name for b in db.scalars(select(Brand)).all()}
    processes = {p.id: p.name for p in db.scalars(select(Process)).all()}
    users = {u.id: u.email for u in db.scalars(select(User)).all()}

    log_items: list[AllocationLogItem] = []
    for a in allocations:
        bp = bps.get(a.brand_process_id)
        brand_id = bp.brand_id if bp else uuid.uuid4()
        process_id = bp.process_id if bp else uuid.uuid4()
        brand_name = brands.get(brand_id, "Unknown Brand")
        process_name = processes.get(process_id, "Unknown Process")

        emp = employees.get(a.employee_id)
        emp_name = emp.name if emp else "Unknown Employee"
        emp_pod_name = pods.get(emp.pod_id) if emp and emp.pod_id else None

        source_emp = employees.get(a.reassigned_from_employee_id) if a.reassigned_from_employee_id else None
        source_name = source_emp.name if source_emp else None

        approved_by_email = users.get(a.approved_by_user_id) if a.approved_by_user_id else None

        log_items.append(
            AllocationLogItem(
                id=a.id,
                roster_id=a.roster_id,
                date=a.date,
                start_time=a.start_time.strftime("%H:%M"),
                end_time=a.end_time.strftime("%H:%M"),
                brand_id=brand_id,
                brand_name=brand_name,
                process_id=process_id,
                process_name=process_name,
                employee_id=a.employee_id,
                employee_name=emp_name,
                employee_pod_name=emp_pod_name,
                allocation_type=a.allocation_type,
                reassigned_from_employee_id=a.reassigned_from_employee_id,
                reassigned_from_employee_name=source_name,
                reassignment_reason=a.reassignment_reason,
                is_cross_pod_approved=a.is_cross_pod_approved,
                approved_by_user_id=a.approved_by_user_id,
                approved_by_email=approved_by_email,
                approved_at=a.approved_at,
                created_at=a.created_at,
            )
        )

    return log_items


@router.get("/{roster_id}/analytics", response_model=WorkforceAnalyticsResponse)
def get_roster_analytics(
    roster_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> WorkforceAnalyticsResponse:
    """Calculates workforce utilization, capacity distribution, and staffing deficit/surplus per pod."""
    import math

    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    allocations = db.scalars(
        select(RosterAllocation).where(RosterAllocation.roster_id == roster.id)
    ).all()
    conflicts = db.scalars(
        select(RosterConflict).where(RosterConflict.roster_id == roster.id)
    ).all()

    active_employees = db.scalars(
        select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
    ).all()
    emp_by_id = {e.id: e for e in active_employees}
    pods = list(db.scalars(select(Pod)).all())

    # Scoping for Pod Lead: restrict metrics, employees, allocations, and pods to their pod only
    if current_user.role == UserRole.POD_LEAD and current_user.pod_id:
        pod_emp_ids = {e.id for e in active_employees if e.pod_id == current_user.pod_id}
        allocations = [a for a in allocations if a.employee_id in pod_emp_ids]
        conflicts = [c for c in conflicts if c.employee_id in pod_emp_ids]
        active_employees = [e for e in active_employees if e.pod_id == current_user.pod_id]
        pods = [p for p in pods if p.id == current_user.pod_id]

    uncovered_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.UNCOVERED_SLOT]
    hard_conflicts = [c for c in conflicts if c.severity == ConflictSeverity.HARD_VIOLATION]

    scheduled_allocations = len(allocations)
    total_demand_slots = scheduled_allocations + len(uncovered_conflicts)

    def calc_duration_hours(start: time, end: time) -> float:
        t1 = start.hour + start.minute / 60.0
        t2 = end.hour + end.minute / 60.0
        dur = t2 - t1
        return dur if dur > 0 else 9.0

    scheduled_hours = sum(calc_duration_hours(a.start_time, a.end_time) for a in allocations)
    uncovered_hours = len(uncovered_conflicts) * 9.0
    total_demand_hours = scheduled_hours + uncovered_hours
    demand_coverage_pct = round((scheduled_allocations / total_demand_slots * 100.0), 1) if total_demand_slots > 0 else 100.0
    skills = db.scalars(select(EmployeeProcessSkill)).all()
    processes = {p.id: p.name for p in db.scalars(select(Process)).all()}

    skills_by_emp: dict[uuid.UUID, list[str]] = {}
    for s in skills:
        proc_name = processes.get(s.process_id, "Process")
        skills_by_emp.setdefault(s.employee_id, []).append(proc_name)

    pod_leads = {pl.pod_id: pl.employee_id for pl in db.scalars(select(PodLead)).all()}

    standard_monthly_hours_per_emp = 21 * 9.0  # 189.0 hours
    total_employees = len(active_employees)
    total_capacity_hours = total_employees * standard_monthly_hours_per_emp
    workforce_utilization_pct = round((scheduled_hours / total_capacity_hours * 100.0), 1) if total_capacity_hours > 0 else 0.0

    pod_analytics_list: list[PodAnalytics] = []
    recommendations: list[str] = []

    for pod in pods:
        pod_emps = [e for e in active_employees if e.pod_id == pod.id]
        emp_count = len(pod_emps)
        available_cap = emp_count * standard_monthly_hours_per_emp

        pod_allocs = [a for a in allocations if a.employee_id in emp_by_id and emp_by_id[a.employee_id].pod_id == pod.id]
        pod_sched_hours = sum(calc_duration_hours(a.start_time, a.end_time) for a in pod_allocs)

        pod_util = round((pod_sched_hours / available_cap * 100.0), 1) if available_cap > 0 else 0.0
        gap = round(pod_sched_hours - available_cap, 1)

        pod_skills = set()
        for e in pod_emps:
            for sk in skills_by_emp.get(e.id, []):
                pod_skills.add(sk)

        if pod_sched_hours > available_cap:
            status_str = "DEFICIT"
            needed = max(1, math.ceil((pod_sched_hours - available_cap) / standard_monthly_hours_per_emp))
            free_count = 0
            recommendations.append(
                f"{pod.name} is in DEFICIT at {pod_util}% capacity (+{abs(gap):.0f}h above capacity). Needs {needed} additional staff or cross-pod support."
            )
        elif pod_util < 75.0 and available_cap > 0:
            status_str = "SURPLUS"
            needed = 0
            free_count = max(1, int((available_cap - pod_sched_hours) / standard_monthly_hours_per_emp))
            recommendations.append(
                f"{pod.name} has SURPLUS capacity at {pod_util}% utilization (~{free_count} free employee equivalent). Available for cross-pod lending."
            )
        else:
            status_str = "BALANCED"
            needed = 0
            free_count = 0

        lead_emp_id = pod_leads.get(pod.id)
        lead_name = emp_by_id[lead_emp_id].name if lead_emp_id and lead_emp_id in emp_by_id else "Unassigned Lead"

        pod_analytics_list.append(
            PodAnalytics(
                pod_id=pod.id,
                pod_name=pod.name,
                lead_name=lead_name,
                employee_count=emp_count,
                available_capacity_hours=round(available_cap, 1),
                scheduled_hours=round(pod_sched_hours, 1),
                utilization_pct=pod_util,
                status=status_str,
                net_hours_gap=gap,
                employees_needed=needed,
                free_employees_count=free_count,
                skills_summary=sorted(list(pod_skills)),
            )
        )

    if len(uncovered_conflicts) > 0:
        recommendations.append(
            f"{len(uncovered_conflicts)} demand slots currently uncovered ({uncovered_hours:.0f}h). Utilize cross-pod reassignments or optimizer to fill remaining gaps."
        )
    if not recommendations:
        recommendations.append("All pods are operating within balanced capacity thresholds with 100% demand satisfaction.")

    return WorkforceAnalyticsResponse(
        roster_id=roster.id,
        month=roster.month,
        year=roster.year,
        status=roster.status.value if hasattr(roster.status, "value") else str(roster.status),
        total_demand_slots=total_demand_slots,
        total_demand_hours=round(total_demand_hours, 1),
        scheduled_allocations=scheduled_allocations,
        scheduled_hours=round(scheduled_hours, 1),
        demand_coverage_pct=demand_coverage_pct,
        total_employees=total_employees,
        total_capacity_hours=round(total_capacity_hours, 1),
        workforce_utilization_pct=workforce_utilization_pct,
        hard_conflicts_count=len(hard_conflicts),
        pods=pod_analytics_list,
        recommendations=recommendations,
    )


def _load_solver_inputs(roster: Roster, db: Session):
    num_days = calendar.monthrange(roster.year, roster.month)[1]
    target_dates = [date(roster.year, roster.month, d) for d in range(1, num_days + 1)]

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

    primaries = [
        PrimaryAssignmentSpec(
            employee_id=pa.employee_id,
            brand_process_id=pa.brand_process_id,
            priority=pa.priority,
        )
        for pa in db.scalars(select(PrimaryAssignment).where(PrimaryAssignment.is_active == True)).all()
    ]

    unavails = db.scalars(select(EmployeeUnavailability)).all()
    unavails_map = {
        (u.employee_id, u.date): UnavailabilitySpec(
            employee_id=u.employee_id,
            date=u.date,
            reason_type=u.reason_type.value if hasattr(u.reason_type, "value") else str(u.reason_type),
            is_approved=u.is_approved,
        )
        for u in unavails
    }

    prefs = db.scalars(select(EmployeePreference)).all()
    prefs_map = {
        p.employee_id: PreferenceSpec(
            employee_id=p.employee_id,
            preferred_weekly_off_days=[int(d.strip()) for d in p.preferred_weekly_off_days.split(",") if d.strip()],
        )
        for p in prefs
    }

    allocations = db.scalars(
        select(RosterAllocation).where(RosterAllocation.roster_id == roster.id)
    ).all()
    baseline_allocs = [
        ScheduledAllocation(
            id=a.id,
            employee_id=a.employee_id,
            brand_process_id=a.brand_process_id,
            date=a.date,
            interval=TimeInterval(a.start_time, a.end_time),
            allocation_type=EngineAllocationType(a.allocation_type.value if hasattr(a.allocation_type, "value") else str(a.allocation_type)),
            is_cross_pod_approved=a.is_cross_pod_approved,
        )
        for a in allocations
    ]

    demand_slots = []
    for d in target_dates:
        is_holiday = d in holidays
        for bp_id, brand_id, process_id in bp_list:
            pat = patterns_map.get(bp_id)
            if not pat:
                continue
            ov = overrides_map.get((bp_id, d))
            slot = DemandResolver.resolve_slot(
                brand_process_id=bp_id,
                brand_id=brand_id,
                process_id=process_id,
                target_date=d,
                pattern=pat,
                override=ov,
                is_company_holiday=is_holiday,
            )
            if slot and slot.is_operating and slot.required_staff > 0:
                demand_slots.append(slot)

    shifts_by_emp_date: dict[tuple[uuid.UUID, date], list[TimeInterval]] = {}
    for a in baseline_allocs:
        shifts_by_emp_date.setdefault((a.employee_id, a.date), []).append(a.interval)

    existing_shifts = [
        ScheduledShift(
            id=uuid.uuid4(),
            employee_id=eid,
            date=d,
            interval=TimeInterval(min(i.start_time for i in intervals), max(i.end_time for i in intervals)),
            is_working_day=True,
        )
        for (eid, d), intervals in shifts_by_emp_date.items()
    ]

    bp_pod_map: dict[uuid.UUID, uuid.UUID | None] = {}
    for pa in primaries:
        if pa.brand_process_id not in bp_pod_map:
            e = emp_map.get(pa.employee_id)
            if e:
                bp_pod_map[pa.brand_process_id] = e.pod_id

    # Fallback for brand processes without primary assignments
    for bp_id, brand_id, process_id in bp_list:
        if bp_id not in bp_pod_map:
            for emp in emp_map.values():
                if process_id in emp.skill_process_ids and emp.pod_id:
                    bp_pod_map[bp_id] = emp.pod_id
                    break

    return {
        "target_dates": target_dates,
        "demand_slots": demand_slots,
        "employees": emp_map,
        "patterns": patterns_map,
        "overrides": overrides_map,
        "holidays": holidays,
        "primary_assignments": primaries,
        "unavailabilities": unavails_map,
        "preferences": prefs_map,
        "existing_allocations": baseline_allocs,
        "existing_shifts": existing_shifts,
        "brand_processes": bp_list,
        "bp_pod_map": bp_pod_map,
    }


@router.post("/{roster_id}/resolver/preview", response_model=ResolverPreviewResponse)
def preview_conflict_resolutions(
    roster_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> ResolverPreviewResponse:
    """Runs AutomatedConflictResolver in preview mode without committing changes."""
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    is_published = roster.status == RosterStatus.PUBLISHED
    inputs = _load_solver_inputs(roster, db)

    result: ResolverResult = AutomatedConflictResolver.solve(
        target_dates=inputs["target_dates"],
        demand_slots=inputs["demand_slots"],
        employees=inputs["employees"],
        patterns=inputs["patterns"],
        overrides=inputs["overrides"],
        company_holidays=inputs["holidays"],
        primary_assignments=inputs["primary_assignments"],
        unavailabilities=inputs["unavailabilities"],
        preferences=inputs["preferences"],
        existing_allocations=inputs["existing_allocations"],
        existing_shifts=inputs["existing_shifts"],
        brand_processes=inputs["brand_processes"],
        bp_pod_map=inputs["bp_pod_map"],
        time_limit_seconds=15.0,
    )

    # Entities lookup for rich response
    emp_by_id = {e.id: e for e in db.scalars(select(Employee)).all()}
    pod_by_id = {p.id: p for p in db.scalars(select(Pod)).all()}
    bp_by_id = {bp.id: bp for bp in db.scalars(select(BrandProcess)).all()}
    brand_by_id = {b.id: b for b in db.scalars(select(Brand)).all()}
    proc_by_id = {pr.id: pr for pr in db.scalars(select(Process)).all()}

    def format_bundle(bundle: ResolutionBundle) -> ResolverBundleResponse:
        changes_data = []
        for ch in bundle.changes:
            bp = bp_by_id.get(ch.brand_process_id)
            brand = brand_by_id.get(bp.brand_id) if bp else None
            proc = proc_by_id.get(bp.process_id) if bp else None

            emp = emp_by_id.get(ch.employee_id) if ch.employee_id else None
            pod = pod_by_id.get(emp.pod_id) if emp and emp.pod_id else None

            prev_emp = emp_by_id.get(ch.previous_employee_id) if ch.previous_employee_id else None

            changes_data.append({
                "action_type": ch.action_type.value if hasattr(ch.action_type, "value") else str(ch.action_type),
                "allocation_id": str(ch.allocation_id) if ch.allocation_id else None,
                "date": ch.date.isoformat(),
                "start_time": ch.interval.start_time.strftime("%H:%M"),
                "end_time": ch.interval.end_time.strftime("%H:%M"),
                "brand_name": brand.name if brand else "Brand",
                "process_name": proc.name if proc else "Process",
                "new_employee_id": str(ch.employee_id) if ch.employee_id else None,
                "new_employee_name": emp.name if emp else None,
                "new_employee_pod": pod.name if pod else None,
                "previous_employee_id": str(ch.previous_employee_id) if ch.previous_employee_id else None,
                "previous_employee_name": prev_emp.name if prev_emp else None,
                "is_cross_pod": ch.is_cross_pod,
                "explanation": ch.notes or bundle.description,
            })

        return ResolverBundleResponse(
            bundle_id=bundle.bundle_id,
            requires_cross_pod_approval=bundle.requires_manager_approval,
            explanation=bundle.description,
            affected_dates=[bundle.target_date],
            changes=changes_data,
            affected_conflicts_count=len(bundle.changes),
        )

    auto_bundles: list[ResolverBundleResponse] = []
    approval_bundles: list[ResolverBundleResponse] = []

    for b in result.resolution_bundles:
        formatted = format_bundle(b)
        if b.requires_manager_approval:
            approval_bundles.append(formatted)
        else:
            auto_bundles.append(formatted)

    if current_user.role == UserRole.POD_LEAD and current_user.pod_id:
        pod_emp_ids = set(str(eid) for eid in db.scalars(select(Employee.id).where(Employee.pod_id == current_user.pod_id)).all())
        auto_bundles = [
            b for b in auto_bundles
            if any((ch.get("previous_employee_id") in pod_emp_ids) or (ch.get("new_employee_id") in pod_emp_ids) for ch in b.changes)
        ]
        approval_bundles = [
            b for b in approval_bundles
            if any((ch.get("previous_employee_id") in pod_emp_ids) or (ch.get("new_employee_id") in pod_emp_ids) for ch in b.changes)
        ]

    shortages_data: list[ResolverShortageResponse] = []
    for s in result.shortage_evidences:
        bp = bp_by_id.get(s.brand_process_id)
        brand = brand_by_id.get(s.brand_id)
        proc = proc_by_id.get(s.process_id)

        shortages_data.append(
            ResolverShortageResponse(
                demand_slot_id=uuid.uuid4(),
                date=s.date,
                brand_name=brand.name if brand else "Brand",
                process_name=proc.name if proc else "Process",
                start_time="",
                end_time="",
                primary_employee_names=[],
                root_cause="WORKFORCE_SHORTAGE",
                explanation="; ".join(s.reasons),
            )
        )

    # Initial conflicts count on baseline roster
    init_conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == roster.id)).all()
    uncovered_init = [c for c in init_conflicts if c.conflict_type == ConflictType.UNCOVERED_SLOT]
    total_demand = len(inputs["existing_allocations"]) + len(uncovered_init)

    cov_before = round((len(inputs["existing_allocations"]) / total_demand * 100.0), 1) if total_demand > 0 else 100.0
    cov_after = round((result.final_covered_positions / total_demand * 100.0), 1) if total_demand > 0 else 100.0

    passes_data = [
        {
            "pass_name": p.pass_name,
            "status": p.status.value,
            "solve_time_seconds": round(p.solve_time_seconds, 3),
        }
        for p in result.pass_results
    ]

    val_conflicts_data = [
        {
            "severity": vc.severity.value,
            "conflict_type": vc.conflict_type.value,
            "description": vc.description,
            "date": vc.date.isoformat(),
        }
        for vc in result.validation_conflicts
    ]

    return ResolverPreviewResponse(
        roster_id=roster.id,
        target_roster_id=roster.id,
        is_published=is_published,
        requires_child_revision=is_published,
        status=result.overall_status.value,
        initial_conflicts_count=len(init_conflicts),
        resolvable_conflicts_count=len(result.resolution_bundles),
        unresolvable_conflicts_count=len(result.shortage_evidences),
        coverage_before_pct=cov_before,
        coverage_after_pct=cov_after,
        automatically_resolvable_bundles=auto_bundles,
        pending_approval_bundles=approval_bundles,
        unresolvable_shortages=shortages_data,
        passes=passes_data,
        validation_passed=len([vc for vc in result.validation_conflicts if vc.severity == EngineConflictSeverity.HARD_VIOLATION]) == 0,
        validation_conflicts=val_conflicts_data,
    )


@router.post("/{roster_id}/resolver/apply", response_model=ResolverApplyResponse)
def apply_conflict_resolutions(
    roster_id: uuid.UUID,
    payload: ResolverApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> ResolverApplyResponse:
    """Applies conflict resolutions transactionally, creating a child revision if the roster is published."""
    roster = db.get(Roster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")

    is_new_version = False
    target_roster = roster

    # Safety check: Published roster immutability
    if roster.status == RosterStatus.PUBLISHED:
        if not payload.create_child_if_published:
            raise HTTPException(
                status_code=400,
                detail="Published rosters cannot be modified directly. Must enable create_child_if_published.",
            )
        is_new_version = True
        target_roster = Roster(
            id=uuid.uuid4(),
            name=f"{roster.name} (v{roster.version + 1})",
            month=roster.month,
            year=roster.year,
            version=roster.version + 1,
            status=RosterStatus.DRAFT,
            parent_roster_id=roster.id,
            config_hash=roster.config_hash,
            created_by=current_user.email,
        )
        db.add(target_roster)
        db.flush()

        # Clone shifts first
        parent_shifts = db.scalars(select(EmployeeShift).where(EmployeeShift.roster_id == roster.id)).all()
        shift_map: dict[uuid.UUID, uuid.UUID] = {}
        for s in parent_shifts:
            new_shift = EmployeeShift(
                id=uuid.uuid4(),
                roster_id=target_roster.id,
                employee_id=s.employee_id,
                date=s.date,
                start_time=s.start_time,
                end_time=s.end_time,
                is_working_day=s.is_working_day,
            )
            db.add(new_shift)
            shift_map[s.id] = new_shift.id
        db.flush()

        # Clone baseline allocations to child draft
        for a in db.scalars(select(RosterAllocation).where(RosterAllocation.roster_id == roster.id)).all():
            new_s_id = shift_map.get(a.shift_id)
            if not new_s_id:
                continue
            clone_a = RosterAllocation(
                id=uuid.uuid4(),
                roster_id=target_roster.id,
                shift_id=new_s_id,
                date=a.date,
                employee_id=a.employee_id,
                brand_process_id=a.brand_process_id,
                start_time=a.start_time,
                end_time=a.end_time,
                allocation_type=a.allocation_type,
                reassigned_from_employee_id=a.reassigned_from_employee_id,
                reassignment_reason=a.reassignment_reason,
                is_cross_pod_approved=a.is_cross_pod_approved,
                approved_by_user_id=a.approved_by_user_id,
                approved_at=a.approved_at,
            )
            db.add(clone_a)
        db.flush()

    # Load solver inputs
    inputs = _load_solver_inputs(target_roster, db)
    result = AutomatedConflictResolver.solve(
        target_dates=inputs["target_dates"],
        demand_slots=inputs["demand_slots"],
        employees=inputs["employees"],
        patterns=inputs["patterns"],
        overrides=inputs["overrides"],
        company_holidays=inputs["holidays"],
        primary_assignments=inputs["primary_assignments"],
        unavailabilities=inputs["unavailabilities"],
        preferences=inputs["preferences"],
        existing_allocations=inputs["existing_allocations"],
        existing_shifts=inputs["existing_shifts"],
        brand_processes=inputs["brand_processes"],
        bp_pod_map=inputs["bp_pod_map"],
        time_limit_seconds=15.0,
    )

    # Filter bundles to apply
    approved_set = set(payload.approved_bundle_ids or [])
    bundles_to_apply = []
    for b in result.resolution_bundles:
        if not b.requires_manager_approval:
            bundles_to_apply.append(b)
        elif payload.approve_cross_pod:
            if not approved_set or b.bundle_id in approved_set:
                bundles_to_apply.append(b)

    applied_changes_count = 0
    now = datetime.now(timezone.utc)

    # In-memory caches to eliminate WAN roundtrips on database operations
    existing_shifts_map: dict[tuple[uuid.UUID, date], EmployeeShift] = {
        (s.employee_id, s.date): s
        for s in db.scalars(select(EmployeeShift).where(EmployeeShift.roster_id == target_roster.id)).all()
    }
    emp_records: dict[uuid.UUID, Employee] = {
        e.id: e for e in db.scalars(select(Employee)).all()
    }
    alloc_by_id: dict[uuid.UUID, RosterAllocation] = {
        a.id: a
        for a in db.scalars(select(RosterAllocation).where(RosterAllocation.roster_id == target_roster.id)).all()
    }
    alloc_by_slot: dict[tuple[date, uuid.UUID, uuid.UUID], RosterAllocation] = {
        (a.date, a.brand_process_id, a.employee_id): a for a in alloc_by_id.values()
    }
    alloc_by_date_bp: dict[tuple[date, uuid.UUID], RosterAllocation] = {
        (a.date, a.brand_process_id): a for a in alloc_by_id.values()
    }

    def get_or_create_shift(emp_id: uuid.UUID, alloc_date: date, alloc_interval: TimeInterval) -> uuid.UUID:
        shift = existing_shifts_map.get((emp_id, alloc_date))
        if not shift:
            emp_rec = emp_records.get(emp_id)
            s_start = emp_rec.standard_start_time if emp_rec else alloc_interval.start_time
            s_end = emp_rec.standard_end_time if emp_rec else alloc_interval.end_time
            shift = EmployeeShift(
                id=uuid.uuid4(),
                roster_id=target_roster.id,
                employee_id=emp_id,
                date=alloc_date,
                start_time=s_start,
                end_time=s_end,
                is_working_day=True,
            )
            db.add(shift)
            existing_shifts_map[(emp_id, alloc_date)] = shift
        return shift.id

    # Apply changes transactionally
    for b in bundles_to_apply:
        for ch in b.changes:
            if ch.action_type == ActionType.NEW_ALLOCATION:
                s_id = get_or_create_shift(ch.employee_id, ch.date, ch.interval)
                new_alloc = RosterAllocation(
                    id=uuid.uuid4(),
                    roster_id=target_roster.id,
                    shift_id=s_id,
                    date=ch.date,
                    employee_id=ch.employee_id,
                    brand_process_id=ch.brand_process_id,
                    start_time=ch.interval.start_time,
                    end_time=ch.interval.end_time,
                    allocation_type=AllocationType.CROSS_POD_REASSIGNMENT if ch.is_cross_pod else AllocationType.SAME_POD_REASSIGNMENT,
                    reassignment_reason=ch.notes or b.description,
                    is_cross_pod_approved=ch.is_cross_pod,
                    approved_by_user_id=current_user.id if ch.is_cross_pod else None,
                    approved_at=now if ch.is_cross_pod else None,
                )
                db.add(new_alloc)
                alloc_by_id[new_alloc.id] = new_alloc
                alloc_by_slot[(ch.date, ch.brand_process_id, ch.employee_id)] = new_alloc
                alloc_by_date_bp[(ch.date, ch.brand_process_id)] = new_alloc
                applied_changes_count += 1

            elif ch.action_type in (ActionType.REASSIGN_ALLOCATION, ActionType.MOVE_ALLOCATION):
                # Look up existing allocation
                existing = None
                if ch.allocation_id:
                    existing = alloc_by_id.get(ch.allocation_id)
                if not existing:
                    existing = alloc_by_date_bp.get((ch.date, ch.brand_process_id))
                if existing:
                    s_id = get_or_create_shift(ch.employee_id, ch.date, ch.interval)
                    existing.shift_id = s_id
                    existing.reassigned_from_employee_id = existing.employee_id
                    existing.employee_id = ch.employee_id
                    existing.start_time = ch.interval.start_time
                    existing.end_time = ch.interval.end_time
                    existing.allocation_type = AllocationType.CROSS_POD_REASSIGNMENT if ch.is_cross_pod else AllocationType.SAME_POD_REASSIGNMENT
                    existing.reassignment_reason = ch.notes or b.description
                    existing.is_cross_pod_approved = ch.is_cross_pod
                    existing.approved_by_user_id = current_user.id if ch.is_cross_pod else None
                    existing.approved_at = now if ch.is_cross_pod else None
                    applied_changes_count += 1

            elif ch.action_type == ActionType.REMOVE_ALLOCATION:
                existing = None
                if ch.allocation_id:
                    existing = alloc_by_id.get(ch.allocation_id)
                if not existing:
                    existing = alloc_by_slot.get((ch.date, ch.brand_process_id, ch.employee_id))
                if existing:
                    db.delete(existing)
                    alloc_by_id.pop(existing.id, None)
                    alloc_by_slot.pop((ch.date, ch.brand_process_id, ch.employee_id), None)
                    applied_changes_count += 1

    db.flush()

    # Re-run IndependentValidator to guarantee absolute constraint safety
    updated_inputs = _load_solver_inputs(target_roster, db)
    # Build shifts for validator
    shifts_by_emp_date: dict[tuple[uuid.UUID, date], list[TimeInterval]] = {}
    for a in updated_inputs["existing_allocations"]:
        shifts_by_emp_date.setdefault((a.employee_id, a.date), []).append(a.interval)

    all_shifts = []
    for (eid, d), intervals in shifts_by_emp_date.items():
        min_start = min(i.start_time for i in intervals)
        max_end = max(i.end_time for i in intervals)
        all_shifts.append(
            ScheduledShift(
                id=uuid.uuid4(),
                employee_id=eid,
                date=d,
                interval=TimeInterval(min_start, max_end),
                is_working_day=True,
            )
        )

    val_conflicts = IndependentValidator.validate_roster(
        all_dates=updated_inputs["target_dates"],
        brand_processes=updated_inputs["brand_processes"],
        patterns=updated_inputs["patterns"],
        overrides=updated_inputs["overrides"],
        company_holidays=updated_inputs["holidays"],
        employees=updated_inputs["employees"],
        unavailabilities=updated_inputs["unavailabilities"],
        shifts=all_shifts,
        allocations=updated_inputs["existing_allocations"],
    )

    hard_violations = [vc for vc in val_conflicts if vc.severity == EngineConflictSeverity.HARD_VIOLATION]
    if len(hard_violations) > 0 and len(hard_violations) > len([c for c in result.validation_conflicts if c.severity == EngineConflictSeverity.HARD_VIOLATION]):
        # Rollback on safety degradation
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Independent validator rejected proposed changes: {hard_violations[0].description}",
        )

    # Sync RosterConflict table
    # Delete old conflicts for target roster
    old_conflicts = db.scalars(select(RosterConflict).where(RosterConflict.roster_id == target_roster.id)).all()
    for oc in old_conflicts:
        db.delete(oc)
    db.flush()

    # Insert updated conflicts
    for vc in val_conflicts:
        db.add(
            RosterConflict(
                roster_id=target_roster.id,
                date=vc.date,
                brand_process_id=vc.brand_process_id,
                employee_id=vc.employee_id,
                start_time=vc.interval.start_time if vc.interval else None,
                end_time=vc.interval.end_time if vc.interval else None,
                severity=ConflictSeverity.HARD_VIOLATION if vc.severity == EngineConflictSeverity.HARD_VIOLATION else ConflictSeverity.SOFT_WARNING,
                conflict_type=ConflictType(vc.conflict_type.value),
                description=vc.description,
                is_resolved=False,
            )
        )

    hard_count = len([vc for vc in val_conflicts if vc.severity == EngineConflictSeverity.HARD_VIOLATION])
    target_roster.config_hash = compute_config_hash(db)
    target_roster.status = RosterStatus.VALIDATED if hard_count == 0 else RosterStatus.DRAFT

    db.commit()

    total_demand = len(updated_inputs["existing_allocations"]) + hard_count
    cov_pct = round((len(updated_inputs["existing_allocations"]) / total_demand * 100.0), 1) if total_demand > 0 else 100.0

    return ResolverApplyResponse(
        status="SUCCESS",
        roster_id=target_roster.id,
        version=target_roster.version,
        is_new_version=is_new_version,
        applied_bundles_count=len(bundles_to_apply),
        applied_changes_count=applied_changes_count,
        resolved_conflicts_count=len(bundles_to_apply),
        remaining_conflicts_count=len(val_conflicts),
        coverage_pct=cov_pct,
        validation_passed=hard_count == 0,
        validation_conflicts_count=len(val_conflicts),
        applied_at=now,
    )


@router.post("/revalidate-all")
def revalidate_all_rosters(
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
) -> dict[str, Any]:
    """
    On-demand recomputation across active rosters using current database state.
    """
    from app.modules.roster.recompute import recompute_all_active_rosters_conflicts
    return recompute_all_active_rosters_conflicts(db)




