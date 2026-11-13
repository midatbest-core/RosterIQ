from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.errors import AppError
from app.modules.auth.dependencies import (
    check_employee_scope,
    check_pod_scope,
    get_current_user,
    require_employee_user,
    require_lead_or_manager,
    require_manager,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.notifications import create_notification, notify_managers
from app.modules.operations.models import Brand, BrandProcess, Process
from app.modules.roster.engine.domain import ConflictType
from app.modules.roster.models import (
    ConflictSeverity,
    EmployeeShift,
    Roster,
    RosterAllocation,
    RosterConflict,
    RosterStatus,
)
from app.modules.roster.router import check_and_mark_stale_rosters, compute_config_hash
from app.modules.workforce.availability_models import AbsenceReasonType, EmployeeUnavailability
from app.modules.workforce.employee_portal_schemas import (
    EmployeeAvailabilityRequestCreate,
    EmployeeAvailabilityRequestRead,
    EmployeeImpactPreview,
    EmployeeProfileRead,
    EmployeeReviewActionRequest,
    EmployeeTaskItem,
    PodCapacityImpact,
    StaffingShortageItem,
)
from app.modules.workforce.models import Employee, EmployeeProcessSkill, EmployeeStatus, Pod, PodLead
from app.modules.workforce.request_models import EmployeeAvailabilityRequest, RequestStatus

router = APIRouter(prefix="/employee-portal", tags=["Employee Portal"])


@router.get("/me", response_model=EmployeeProfileRead)
def get_employee_profile(
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_user),
) -> EmployeeProfileRead:
    """Returns the authenticated employee's personal profile, pod lead info, skills, and primary assignments."""
    if not user.employee_id:
        raise AppError("FORBIDDEN", "User is not linked to any employee record.", 403)

    emp = db.get(Employee, user.employee_id)
    if not emp:
        raise AppError("NOT_FOUND", "Employee record not found.", 404)

    pod = db.get(Pod, emp.pod_id) if emp.pod_id else None
    pod_lead_name = None
    pod_lead_email = None

    if pod:
        # Check PodLead
        lead_link = db.scalar(select(PodLead).where(PodLead.pod_id == pod.id))
        if lead_link:
            lead_emp = db.get(Employee, lead_link.employee_id)
            if lead_emp:
                pod_lead_name = lead_emp.name
                pod_lead_email = lead_emp.email

    # Primary assignments
    assignments_data = []
    for pa in getattr(emp, "primary_assignments", []):
        bp = db.get(BrandProcess, pa.brand_process_id)
        if bp:
            b = db.get(Brand, bp.brand_id)
            p = db.get(Process, bp.process_id)
            assignments_data.append({
                "assignment_id": str(pa.id),
                "brand_id": str(b.id) if b else None,
                "brand_name": b.name if b else "Unknown",
                "process_id": str(p.id) if p else None,
                "process_name": p.name if p else "Unknown",
                "effective_from": pa.effective_from.isoformat() if pa.effective_from else None,
            })

    # Skills
    skills_data = []
    skills = db.scalars(select(EmployeeProcessSkill).where(EmployeeProcessSkill.employee_id == emp.id)).all()
    for s in skills:
        proc = db.get(Process, s.process_id)
        skills_data.append({
            "process_id": str(s.process_id),
            "process_name": proc.name if proc else "Unknown",
            "proficiency": s.proficiency.value if hasattr(s.proficiency, "value") else str(s.proficiency),
        })

    return EmployeeProfileRead(
        employee_id=emp.id,
        employee_code=emp.employee_code,
        name=emp.name,
        email=emp.email,
        pod_id=emp.pod_id,
        pod_name=pod.name if pod else None,
        pod_lead_name=pod_lead_name,
        pod_lead_email=pod_lead_email,
        daily_capacity_minutes=emp.daily_capacity_minutes,
        standard_start_time=emp.standard_start_time.isoformat(),
        standard_end_time=emp.standard_end_time.isoformat(),
        primary_assignments=assignments_data,
        skills=skills_data,
    )


@router.get("/tasks", response_model=list[EmployeeTaskItem])
def get_employee_tasks(
    month: int | None = None,
    year: int | None = None,
    published_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_user),
) -> list[EmployeeTaskItem]:
    """Returns the employee's scheduled work items/allocations as a structured task checklist."""
    if not user.employee_id:
        raise AppError("FORBIDDEN", "User is not linked to any employee record.", 403)

    target_rosters_q = select(Roster)
    if month:
        target_rosters_q = target_rosters_q.where(Roster.month == month)
    if year:
        target_rosters_q = target_rosters_q.where(Roster.year == year)
    if published_only:
        target_rosters_q = target_rosters_q.where(Roster.status == RosterStatus.PUBLISHED)

    from sqlalchemy import case
    target_roster = db.scalar(
        target_rosters_q.order_by(
            case((Roster.status == RosterStatus.PUBLISHED, 0), else_=1),
            Roster.version.desc(),
            Roster.created_at.desc(),
        )
    )

    query = select(RosterAllocation).where(RosterAllocation.employee_id == user.employee_id)
    if target_roster:
        query = query.where(RosterAllocation.roster_id == target_roster.id)

    # Filter to active published or draft rosters
    allocs = db.scalars(query).all()
    # Cache rosters, brands, processes
    roster_cache: dict[UUID, Roster] = {}
    bp_cache: dict[UUID, BrandProcess] = {}
    brand_cache: dict[UUID, Brand] = {}
    proc_cache: dict[UUID, Process] = {}

    tasks: list[EmployeeTaskItem] = []
    for a in allocs:
        if a.roster_id not in roster_cache:
            r = db.get(Roster, a.roster_id)
            if r:
                roster_cache[a.roster_id] = r
        roster = roster_cache.get(a.roster_id)
        if not roster:
            continue
        if published_only and roster.status != RosterStatus.PUBLISHED:
            continue

        if month and roster.month != month:
            continue
        if year and roster.year != year:
            continue

        if a.brand_process_id not in bp_cache:
            bp = db.get(BrandProcess, a.brand_process_id)
            if bp:
                bp_cache[a.brand_process_id] = bp
        bp = bp_cache.get(a.brand_process_id)
        if not bp:
            continue

        if bp.brand_id not in brand_cache:
            b = db.get(Brand, bp.brand_id)
            if b:
                brand_cache[bp.brand_id] = b
        brand = brand_cache.get(bp.brand_id)

        if bp.process_id not in proc_cache:
            p = db.get(Process, bp.process_id)
            if p:
                proc_cache[bp.process_id] = p
        process = proc_cache.get(bp.process_id)

        day_name = a.date.strftime("%A")
        tasks.append(
            EmployeeTaskItem(
                allocation_id=a.id,
                roster_id=roster.id,
                roster_name=roster.name,
                roster_status=roster.status.value,
                date=a.date.isoformat(),
                day_of_week=day_name,
                start_time=a.start_time.isoformat(),
                end_time=a.end_time.isoformat(),
                brand_name=brand.name if brand else "Brand",
                brand_code=brand.code if brand else "",
                process_name=process.name if process else "Process",
                process_code=process.code if process else "",
                allocation_type=a.allocation_type.value if hasattr(a.allocation_type, "value") else str(a.allocation_type),
                employee_id=a.employee_id,
            )
        )

    tasks.sort(key=lambda t: (t.date, t.start_time))
    return tasks


@router.get("/pod-allocations", response_model=list[EmployeeTaskItem])
def get_pod_allocations(
    month: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_user),
) -> list[EmployeeTaskItem]:
    """Returns all published allocations for employees in the user's pod."""
    if not user.pod_id:
        raise AppError("FORBIDDEN", "User is not associated with any pod.", 403)

    pod_emps = db.scalars(select(Employee).where(Employee.pod_id == user.pod_id)).all()
    emp_map = {e.id: e.name for e in pod_emps}
    if not emp_map:
        return []

    allocs = db.scalars(
        select(RosterAllocation).where(RosterAllocation.employee_id.in_(list(emp_map.keys())))
    ).all()

    roster_cache: dict[UUID, Roster] = {}
    bp_cache: dict[UUID, BrandProcess] = {}
    brand_cache: dict[UUID, Brand] = {}
    proc_cache: dict[UUID, Process] = {}

    tasks: list[EmployeeTaskItem] = []
    for a in allocs:
        if a.roster_id not in roster_cache:
            r = db.get(Roster, a.roster_id)
            if r:
                roster_cache[a.roster_id] = r
        roster = roster_cache.get(a.roster_id)
        if not roster or roster.status != RosterStatus.PUBLISHED:
            continue

        if month and roster.month != month:
            continue
        if year and roster.year != year:
            continue

        if a.brand_process_id not in bp_cache:
            bp = db.get(BrandProcess, a.brand_process_id)
            if bp:
                bp_cache[a.brand_process_id] = bp
        bp = bp_cache.get(a.brand_process_id)
        if not bp:
            continue

        if bp.brand_id not in brand_cache:
            b = db.get(Brand, bp.brand_id)
            if b:
                brand_cache[bp.brand_id] = b
        brand = brand_cache.get(bp.brand_id)

        if bp.process_id not in proc_cache:
            p = db.get(Process, bp.process_id)
            if p:
                proc_cache[bp.process_id] = p
        process = proc_cache.get(bp.process_id)

        day_name = a.date.strftime("%A")
        tasks.append(
            EmployeeTaskItem(
                allocation_id=a.id,
                roster_id=roster.id,
                roster_name=roster.name,
                roster_status=roster.status.value,
                date=a.date.isoformat(),
                day_of_week=day_name,
                start_time=a.start_time.isoformat(),
                end_time=a.end_time.isoformat(),
                brand_name=brand.name if brand else "Brand",
                brand_code=brand.code if brand else "",
                process_name=process.name if process else "Process",
                process_code=process.code if process else "",
                allocation_type=a.allocation_type.value if hasattr(a.allocation_type, "value") else str(a.allocation_type),
                employee_id=a.employee_id,
                employee_name=emp_map.get(a.employee_id, "Pod Colleague"),
            )
        )

    tasks.sort(key=lambda t: (t.date, t.start_time, t.employee_name or ""))
    return tasks


@router.post("/requests", response_model=EmployeeAvailabilityRequestRead, status_code=201)
def submit_availability_request(
    payload: EmployeeAvailabilityRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_user),
) -> EmployeeAvailabilityRequestRead:
    """Submits an employee absence or availability adjustment request. Employees submit for themselves; Pod Leads can submit for their pod members."""
    target_emp_id = None
    if user.role == UserRole.POD_LEAD:
        target_emp_id = payload.employee_id or user.employee_id
    elif user.role == UserRole.EMPLOYEE:
        target_emp_id = user.employee_id
    else:
        target_emp_id = payload.employee_id or user.employee_id

    if not target_emp_id:
        raise AppError("FORBIDDEN", "Target employee not specified or user is not linked to any employee record.", 403)

    emp = db.get(Employee, target_emp_id)
    if not emp:
        raise AppError("NOT_FOUND", "Employee not found.", 404)

    # Tenant scoping:
    if user.role == UserRole.POD_LEAD:
        if emp.pod_id != user.pod_id:
            raise AppError("FORBIDDEN", "Pod Leads can only submit requests for employees within their own pod.", 403)
    elif user.role == UserRole.EMPLOYEE:
        if emp.id != user.employee_id:
            raise AppError("FORBIDDEN", "Employees can only submit absence requests for themselves.", 403)

    start_d = date.fromisoformat(payload.start_date)
    end_d = date.fromisoformat(payload.end_date)
    if end_d < start_d:
        raise AppError("VALIDATION_ERROR", "End date cannot be earlier than start date.", 422)

    req = EmployeeAvailabilityRequest(
        employee_id=emp.id,
        requested_by_user_id=user.id,
        request_type=payload.request_type,
        start_date=start_d,
        end_date=end_d,
        reason_type=payload.reason_type,
        notes=payload.notes,
        details=payload.details,
        status=RequestStatus.PENDING.value,
    )
    db.add(req)
    db.flush()

    # Notify Ops Managers
    submitted_by = f"Pod Lead ({user.email})" if user.role == UserRole.POD_LEAD else emp.name
    notify_managers(
        db=db,
        title=f"New Leave Request: {emp.name}",
        message=f"{submitted_by} submitted {payload.reason_type} for {emp.name} from {payload.start_date} to {payload.end_date}: {payload.notes}",
        notification_type="NEW_EMPLOYEE_REQUEST",
        reference_type="employee_availability_request",
        reference_id=req.id,
    )

    db.commit()
    db.refresh(req)

    res = EmployeeAvailabilityRequestRead.model_validate(req)
    res.employee_name = emp.name
    return res


@router.get("/requests", response_model=list[EmployeeAvailabilityRequestRead])
def list_employee_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EmployeeAvailabilityRequestRead]:
    """Lists employee availability requests scoped to the user's role (Employee -> own, Pod Lead -> pod, Manager/Admin -> all)."""
    query = select(EmployeeAvailabilityRequest).order_by(EmployeeAvailabilityRequest.created_at.desc())

    if user.role == UserRole.EMPLOYEE:
        if not user.employee_id:
            return []
        query = query.where(EmployeeAvailabilityRequest.employee_id == user.employee_id)
    elif user.role == UserRole.POD_LEAD:
        if not user.pod_id:
            return []
        # Join employee to filter by pod_id
        pod_emps = db.scalars(select(Employee.id).where(Employee.pod_id == user.pod_id)).all()
        query = query.where(EmployeeAvailabilityRequest.employee_id.in_(pod_emps))

    items = db.scalars(query).all()
    emp_map = {e.id: e.name for e in db.scalars(select(Employee)).all()}

    results = []
    for item in items:
        r = EmployeeAvailabilityRequestRead.model_validate(item)
        r.employee_name = emp_map.get(item.employee_id, "Unknown Employee")
        results.append(r)
    return results


@router.get("/requests/{request_id}", response_model=EmployeeAvailabilityRequestRead)
def get_employee_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EmployeeAvailabilityRequestRead:
    """Gets details of an employee availability request with strict IDOR verification."""
    req = db.get(EmployeeAvailabilityRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)

    emp = db.get(Employee, req.employee_id)
    if not emp:
        raise AppError("NOT_FOUND", "Employee not found.", 404)

    # Scoping checks
    check_employee_scope(user, req.employee_id)
    if emp.pod_id:
        check_pod_scope(user, emp.pod_id)

    res = EmployeeAvailabilityRequestRead.model_validate(req)
    res.employee_name = emp.name
    return res


@router.post("/requests/{request_id}/preview-impact", response_model=EmployeeImpactPreview)
def preview_employee_request_impact(
    request_id: UUID,
    roster_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> EmployeeImpactPreview:
    """Analyzes the exact impact of an employee absence request on active roster allocations."""
    req = db.get(EmployeeAvailabilityRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)

    emp = db.get(Employee, req.employee_id)
    if not emp:
        raise AppError("NOT_FOUND", "Employee not found.", 404)

    if emp.pod_id:
        check_pod_scope(user, emp.pod_id)

    # Resolve target roster
    target_roster = None
    if roster_id:
        target_roster = db.get(Roster, roster_id)
    if not target_roster:
        target_roster = db.scalar(
            select(Roster)
            .where(
                Roster.month == req.start_date.month,
                Roster.year == req.start_date.year,
                Roster.status == RosterStatus.PUBLISHED,
            )
            .order_by(Roster.version.desc())
        )
    if not target_roster:
        target_roster = db.scalar(
            select(Roster)
            .where(Roster.month == req.start_date.month, Roster.year == req.start_date.year)
            .order_by(Roster.version.desc(), Roster.created_at.desc())
        )

    # Dates range
    curr = req.start_date
    dates_list = []
    while curr <= req.end_date:
        dates_list.append(curr)
        curr += timedelta(days=1)

    # Check allocations filtered to the targeted operational roster
    alloc_filter = [
        RosterAllocation.employee_id == emp.id,
        RosterAllocation.date.in_(dates_list),
    ]
    if target_roster:
        alloc_filter.append(RosterAllocation.roster_id == target_roster.id)

    conflicts = db.scalars(select(RosterAllocation).where(*alloc_filter)).all()

    bp_cache: dict[UUID, BrandProcess] = {}
    b_cache: dict[UUID, Brand] = {}
    p_cache: dict[UUID, Process] = {}

    conflict_data = []
    for c in conflicts:
        if c.brand_process_id not in bp_cache:
            bp = db.get(BrandProcess, c.brand_process_id)
            if bp:
                bp_cache[c.brand_process_id] = bp
        bp = bp_cache.get(c.brand_process_id)

        brand_name = "Brand"
        proc_name = "Process"
        if bp:
            if bp.brand_id not in b_cache:
                b = db.get(Brand, bp.brand_id)
                if b:
                    b_cache[bp.brand_id] = b
            brand = b_cache.get(bp.brand_id)
            if brand:
                brand_name = brand.name

            if bp.process_id not in p_cache:
                p = db.get(Process, bp.process_id)
                if p:
                    p_cache[bp.process_id] = p
            proc = p_cache.get(bp.process_id)
            if proc:
                proc_name = proc.name

        conflict_data.append({
            "allocation_id": str(c.id),
            "date": c.date.isoformat(),
            "time": f"{c.start_time.isoformat()} - {c.end_time.isoformat()}",
            "brand": brand_name,
            "process": proc_name,
        })

    # Pod Capacity Impact
    pod_capacity = None
    if emp.pod_id:
        pod = db.get(Pod, emp.pod_id)
        if pod:
            pod_emps = db.scalars(
                select(Employee).where(
                    Employee.pod_id == emp.pod_id,
                    Employee.status == EmployeeStatus.ACTIVE,
                )
            ).all()
            pod_emp_ids = [e.id for e in pod_emps]
            unavails = db.scalars(
                select(EmployeeUnavailability).where(
                    EmployeeUnavailability.employee_id.in_(pod_emp_ids),
                    EmployeeUnavailability.date.in_(dates_list),
                    EmployeeUnavailability.is_approved == True,
                )
            ).all()
            on_leave_ids = {u.employee_id for u in unavails} | {emp.id}
            on_leave_count = len(on_leave_ids)
            total_members = len(pod_emps)
            available_members = max(0, total_members - on_leave_count)

            if available_members == 0:
                impact_level = "CRITICAL"
                summary_pod = f"Critical: All {total_members} members of {pod.name} unavailable on requested date(s)."
            elif available_members <= max(1, total_members // 2):
                impact_level = "ATTENTION"
                summary_pod = f"High capacity impact: {pod.name} reduced to {available_members}/{total_members} available staff."
            else:
                impact_level = "NORMAL"
                summary_pod = f"{pod.name} has {available_members}/{total_members} available staff during requested period."

            pod_capacity = PodCapacityImpact(
                pod_id=pod.id,
                pod_name=pod.name,
                total_members=total_members,
                available_members=available_members,
                on_leave_members=on_leave_count,
                impact_level=impact_level,
                summary=summary_pod,
            )

    # Staffing Shortages & Uncovered Slots Analysis
    shortages: list[StaffingShortageItem] = []
    seen_shortage_keys = set()

    # A. Target roster unresolved conflicts (uncovered slots, insufficient staffing)
    if target_roster:
        rcs = db.scalars(
            select(RosterConflict).where(
                RosterConflict.roster_id == target_roster.id,
                RosterConflict.date.in_(dates_list),
                RosterConflict.is_resolved == False,
            )
        ).all()
        for rc in rcs:
            desc_lower = rc.description.lower()
            is_shortage = (
                rc.conflict_type in (
                    ConflictType.UNCOVERED_SLOT,
                    ConflictType.PARTIAL_COVERAGE,
                    ConflictType.UNAVAILABLE_ALLOCATION,
                    ConflictType.SHIFT_BOUND_EXCEEDED,
                )
                or rc.employee_id == emp.id
                or "shortfall" in desc_lower
                or "insufficient" in desc_lower
                or "uncovered" in desc_lower
                or "staffing" in desc_lower
                or "shortage" in desc_lower
                or "unavailab" in desc_lower
            )
            if is_shortage:
                b_name = "General Brand"
                p_name = "General Process"
                if rc.brand_process_id:
                    if rc.brand_process_id not in bp_cache:
                        bp_obj = db.get(BrandProcess, rc.brand_process_id)
                        if bp_obj:
                            bp_cache[rc.brand_process_id] = bp_obj
                    bp = bp_cache.get(rc.brand_process_id)
                    if bp:
                        if bp.brand_id not in b_cache:
                            b_obj = db.get(Brand, bp.brand_id)
                            if b_obj:
                                b_cache[bp.brand_id] = b_obj
                        if bp.process_id not in p_cache:
                            p_obj = db.get(Process, bp.process_id)
                            if p_obj:
                                p_cache[bp.process_id] = p_obj
                        b_name = b_cache[bp.brand_id].name if bp.brand_id in b_cache else "Brand"
                        p_name = p_cache[bp.process_id].name if bp.process_id in p_cache else "Process"

                key = (rc.date.isoformat(), b_name, p_name, rc.description[:40])
                if key not in seen_shortage_keys:
                    seen_shortage_keys.add(key)
                    shortages.append(
                        StaffingShortageItem(
                            date=rc.date.isoformat(),
                            brand=b_name,
                            process=p_name,
                            description=rc.description,
                        )
                    )

    # B. Conflicting shifts note: each active assigned shift will become unstaffed
    for c in conflicts:
        bp = bp_cache.get(c.brand_process_id)
        b_name = b_cache[bp.brand_id].name if bp and bp.brand_id in b_cache else "Brand"
        p_name = p_cache[bp.process_id].name if bp and bp.process_id in p_cache else "Process"
        time_str = f"{c.start_time.strftime('%H:%M')} - {c.end_time.strftime('%H:%M')}"
        desc = f"Direct shift on {c.date.isoformat()} ({time_str}) will be unstaffed upon leave approval."
        key = (c.date.isoformat(), b_name, p_name, desc[:40])
        if key not in seen_shortage_keys:
            seen_shortage_keys.add(key)
            shortages.append(
                StaffingShortageItem(
                    date=c.date.isoformat(),
                    brand=b_name,
                    process=p_name,
                    description=desc,
                )
            )

    # C. Pod capacity warning: if no explicit shortage conflict records yet,
    # note pod capacity reduction so staffing impact is always explicit
    if not shortages and pod_capacity:
        for d in dates_list:
            desc = f"Absence reduces {pod_capacity.pod_name} staffing capacity from {pod_capacity.total_members} to {pod_capacity.available_members} active staff."
            shortages.append(
                StaffingShortageItem(
                    date=d.isoformat(),
                    brand=pod_capacity.pod_name,
                    process="Pod Staffing Capacity",
                    description=desc,
                )
            )

    # Synthesize comprehensive summary
    if conflicts and shortages:
        summary = (
            f"Coincides with {len(conflicts)} scheduled shift(s) and raises "
            f"{len(shortages)} staffing shortage/capacity deficit(s)."
        )
    elif conflicts:
        summary = f"Request coincides with {len(conflicts)} active shift(s) that require reassignment."
    elif shortages:
        summary = (
            f"No direct shifts scheduled for {emp.name}, but leave raises "
            f"{len(shortages)} staffing shortage/capacity warning(s) on target dates."
        )
    else:
        summary = "No scheduled shifts coincide with this request period."

    requires_reassignment = len(conflicts) > 0 or len(shortages) > 0

    return EmployeeImpactPreview(
        request_id=req.id,
        employee_id=emp.id,
        employee_name=emp.name,
        request_type=req.request_type,
        dates=[d.isoformat() for d in dates_list],
        conflicting_allocations_count=len(conflicts),
        conflicting_allocations=conflict_data,
        staffing_shortages_count=len(shortages),
        staffing_shortages=shortages,
        pod_capacity_impact=pod_capacity,
        requires_reassignment=requires_reassignment,
        summary=summary,
    )


@router.post("/requests/{request_id}/approve", response_model=EmployeeAvailabilityRequestRead)
def approve_employee_request(
    request_id: UUID,
    payload: EmployeeReviewActionRequest | None = None,
    roster_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> EmployeeAvailabilityRequestRead:
    """Transactionally approves employee leave, creates EmployeeUnavailability records, marks rosters STALE, and sets ROSTER_PENDING."""
    req = db.get(EmployeeAvailabilityRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)
    if req.status in (RequestStatus.APPROVED.value, RequestStatus.ROSTER_PENDING.value, RequestStatus.IMPLEMENTED.value):
        raise AppError("CONFLICT", f"Request is already in {req.status} state.", 409)

    emp = db.get(Employee, req.employee_id)
    now = datetime.now(timezone.utc)

    # 1. Map reason_type to AbsenceReasonType enum
    try:
        r_enum = AbsenceReasonType[req.reason_type]
    except KeyError:
        r_enum = AbsenceReasonType.PLANNED_LEAVE

    # 2. Insert EmployeeUnavailability for each date
    curr = req.start_date
    while curr <= req.end_date:
        existing = db.scalar(
            select(EmployeeUnavailability).where(
                EmployeeUnavailability.employee_id == emp.id,
                EmployeeUnavailability.date == curr,
            )
        )
        if not existing:
            unavail = EmployeeUnavailability(
                employee_id=emp.id,
                date=curr,
                reason_type=r_enum,
                is_approved=True,
                notes=req.notes,
            )
            db.add(unavail)
        else:
            existing.is_approved = True
            existing.reason_type = r_enum
            existing.notes = req.notes
        curr += timedelta(days=1)

    # 3. Mark draft rosters STALE and recompute conflicts on draft rosters
    new_hash = compute_config_hash(db)
    check_and_mark_stale_rosters(db, new_hash)
    from app.modules.roster.recompute import recompute_roster_conflicts_sync

    # Resolve target roster: prioritise requested roster or PUBLISHED production roster
    target_roster = None
    if roster_id:
        target_roster = db.get(Roster, roster_id)
    if not target_roster:
        target_roster = db.scalar(
            select(Roster)
            .where(
                Roster.month == req.start_date.month,
                Roster.year == req.start_date.year,
                Roster.status == RosterStatus.PUBLISHED,
            )
            .order_by(Roster.version.desc())
        )
    if not target_roster:
        target_roster = db.scalar(
            select(Roster)
            .where(Roster.month == req.start_date.month, Roster.year == req.start_date.year)
            .order_by(Roster.version.desc(), Roster.created_at.desc())
        )

    if target_roster:
        if target_roster.status == RosterStatus.PUBLISHED:
            # Fork child draft from published parent
            max_v = max(
                r.version
                for r in db.scalars(
                    select(Roster).where(
                        Roster.month == target_roster.month, Roster.year == target_roster.year
                    )
                ).all()
            )
            child = Roster(
                id=uuid.uuid4(),
                name=f"{target_roster.name} (v{max_v + 1})",
                month=target_roster.month,
                year=target_roster.year,
                version=max_v + 1,
                parent_roster_id=target_roster.id,
                status=RosterStatus.DRAFT,
                config_hash=new_hash,
                created_by=user.email,
            )
            db.add(child)
            db.flush()

            parent_shifts = db.scalars(
                select(EmployeeShift).where(EmployeeShift.roster_id == target_roster.id)
            ).all()
            shift_map: dict[uuid.UUID, uuid.UUID] = {}
            for s in parent_shifts:
                new_s = EmployeeShift(
                    id=uuid.uuid4(),
                    roster_id=child.id,
                    employee_id=s.employee_id,
                    date=s.date,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    is_working_day=s.is_working_day,
                )
                db.add(new_s)
                shift_map[s.id] = new_s.id
            db.flush()

            parent_allocs = db.scalars(
                select(RosterAllocation).where(RosterAllocation.roster_id == target_roster.id)
            ).all()
            for a in parent_allocs:
                new_sid = shift_map.get(a.shift_id)
                if not new_sid:
                    continue
                new_a = RosterAllocation(
                    id=uuid.uuid4(),
                    roster_id=child.id,
                    shift_id=new_sid,
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
                db.add(new_a)
            db.flush()
            target_roster = child

        # Recompute conflicts on the draft / child roster
        recompute_roster_conflicts_sync(db, target_roster.id)
        req.implemented_roster_id = target_roster.id

    # 4. Update status
    req.status = RequestStatus.ROSTER_PENDING.value
    review_notes = (payload.manager_notes or payload.notes) if payload else "Approved by Operations Manager."
    req.review_notes = review_notes
    req.reviewed_by_user_id = user.id
    req.reviewed_at = now
    db.flush()

    # 5. Notify Employee
    create_notification(
        db=db,
        user_id=req.requested_by_user_id,
        title=f"Leave Request Approved ({req.reason_type})",
        message=f"Your request for {req.start_date} to {req.end_date} was approved. Any conflicting shifts are being rescheduled.",
        notification_type="EMPLOYEE_REQUEST_APPROVED",
        reference_type="employee_availability_request",
        reference_id=req.id,
    )

    db.commit()
    db.refresh(req)

    res = EmployeeAvailabilityRequestRead.model_validate(req)
    if emp:
        res.employee_name = emp.name
    return res



@router.post("/requests/{request_id}/reject", response_model=EmployeeAvailabilityRequestRead)
def reject_employee_request(
    request_id: UUID,
    payload: EmployeeReviewActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> EmployeeAvailabilityRequestRead:
    """Rejects an employee availability request with mandatory notes."""
    req = db.get(EmployeeAvailabilityRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)
    if req.status in (RequestStatus.APPROVED.value, RequestStatus.IMPLEMENTED.value):
        raise AppError("CONFLICT", f"Cannot reject request in {req.status} state.", 409)

    notes = payload.manager_notes or payload.notes
    if not notes or len(notes.strip()) < 3:
        raise AppError("VALIDATION_ERROR", "Manager review notes are required when rejecting a request.", 422)

    emp = db.get(Employee, req.employee_id)
    now = datetime.now(timezone.utc)

    req.status = RequestStatus.REJECTED.value
    req.review_notes = notes
    req.reviewed_by_user_id = user.id
    req.reviewed_at = now
    db.flush()

    create_notification(
        db=db,
        user_id=req.requested_by_user_id,
        title=f"Leave Request Rejected ({req.reason_type})",
        message=f"Your request for {req.start_date} to {req.end_date} was not approved: {notes}",
        notification_type="EMPLOYEE_REQUEST_REJECTED",
        reference_type="employee_availability_request",
        reference_id=req.id,
    )

    db.commit()
    db.refresh(req)

    res = EmployeeAvailabilityRequestRead.model_validate(req)
    if emp:
        res.employee_name = emp.name
    return res



@router.post("/requests/{request_id}/mark-implemented", response_model=EmployeeAvailabilityRequestRead)
def mark_employee_request_implemented(
    request_id: UUID,
    roster_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> EmployeeAvailabilityRequestRead:
    """Transitions request to IMPLEMENTED once the affected roster has been resolved and published."""
    req = db.get(EmployeeAvailabilityRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)

    # 1. State integrity checks: reject repetitive or invalid transitions
    if req.status == RequestStatus.IMPLEMENTED.value:
        raise AppError("CONFLICT", "Request is already marked as IMPLEMENTED.", 409)
    if req.status == RequestStatus.REJECTED.value:
        raise AppError("CONFLICT", "Cannot mark a rejected request as implemented.", 409)
    if req.status == RequestStatus.PENDING.value:
        raise AppError("CONFLICT", "Cannot mark a pending request as implemented. Request must be reviewed and approved first.", 409)

    # 2. Resolve associated roster
    roster = None
    if roster_id:
        roster = db.get(Roster, roster_id)
    elif req.implemented_roster_id:
        roster = db.get(Roster, req.implemented_roster_id)

    if not roster:
        raise AppError("BAD_REQUEST", "No associated child roster found to verify implementation.", 400)

    # 3. Lineage validation: roster must cover request period and match lineage
    if roster.month != req.start_date.month or roster.year != req.start_date.year:
        raise AppError("BAD_REQUEST", "Target roster does not cover the month and year of the request period.", 400)
    if req.implemented_roster_id and roster.id != req.implemented_roster_id and roster.parent_roster_id != req.implemented_roster_id:
        raise AppError("BAD_REQUEST", "Target roster does not belong to the approved child version lineage.", 400)

    # 4. Roster publication verification
    if roster.status != RosterStatus.PUBLISHED:
        raise AppError("BAD_REQUEST", f"Target roster must be PUBLISHED to mark request implemented (current status: {roster.status.value}).", 400)

    # 5. Independent conflict validation: no blocking conflicts remaining on published roster
    blocking_conflicts = db.scalars(
        select(RosterConflict).where(
            RosterConflict.roster_id == roster.id,
            RosterConflict.severity == ConflictSeverity.HARD_VIOLATION,
        )
    ).all()
    if blocking_conflicts:
        raise AppError("CONFLICT", f"Cannot mark implemented: target roster has {len(blocking_conflicts)} unresolved blocking conflicts.", 409)

    # 6. Reflection verification: ensure employee has no scheduled shifts on approved leave dates
    violating_allocations = db.scalars(
        select(RosterAllocation).where(
            RosterAllocation.roster_id == roster.id,
            RosterAllocation.employee_id == req.employee_id,
            RosterAllocation.date >= req.start_date,
            RosterAllocation.date <= req.end_date,
        )
    ).all()
    if violating_allocations:
        raise AppError(
            "CONFLICT",
            f"Cannot mark implemented: {len(violating_allocations)} conflicting shifts remain scheduled on the published roster during approved leave.",
            409,
        )

    # 7. Transition to IMPLEMENTED
    req.status = RequestStatus.IMPLEMENTED.value
    req.implemented_roster_id = roster.id
    db.flush()

    emp = db.get(Employee, req.employee_id)
    message = (
        f"Your approved leave schedule is now fully resolved and live in published Roster v{roster.version} ({roster.name})."
    )

    create_notification(
        db=db,
        user_id=req.requested_by_user_id,
        title="Leave Schedule Published",
        message=message,
        notification_type="ROSTER_PUBLISHED_FOR_EMPLOYEE",
        reference_type="roster",
        reference_id=roster.id,
    )

    db.commit()
    db.refresh(req)

    res = EmployeeAvailabilityRequestRead.model_validate(req)
    if emp:
        res.employee_name = emp.name
    return res


@router.get("/export/csv")
def export_employee_schedule_csv(
    roster_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_user),
) -> Response:
    """Exports the authenticated employee's personal schedule to CSV for a specified or latest active roster."""
    if not user.employee_id:
        raise AppError("FORBIDDEN", "User has no associated employee record.", 403)

    if not roster_id:
        roster = db.scalars(
            select(Roster)
            .where(Roster.status == RosterStatus.PUBLISHED)
            .order_by(Roster.year.desc(), Roster.month.desc(), Roster.version.desc())
        ).first()
        if not roster:
            roster = db.scalars(select(Roster).order_by(Roster.created_at.desc())).first()
        if not roster:
            raise HTTPException(status_code=404, detail="No active roster found to export")
        roster_id = roster.id

    from app.modules.roster.router import export_roster_csv
    return export_roster_csv(roster_id=roster_id, view_type="employee", filter_id=user.employee_id, db=db, _user=user)


class EmployeeGoogleSheetsExportRequest(BaseModel):
    roster_id: UUID | None = None
    google_access_token: str | None = None


@router.post("/export/google-sheets")
def export_employee_schedule_google_sheets(
    payload: EmployeeGoogleSheetsExportRequest = EmployeeGoogleSheetsExportRequest(),
    db: Session = Depends(get_db),
    user: User = Depends(require_employee_user),
) -> dict:
    """Exports the authenticated employee's schedule directly to a new Google Spreadsheet."""
    if not user.employee_id:
        raise AppError("FORBIDDEN", "User has no associated employee record.", 403)

    target_roster_id = payload.roster_id
    if not target_roster_id:
        roster = db.scalars(
            select(Roster)
            .where(Roster.status == RosterStatus.PUBLISHED)
            .order_by(Roster.year.desc(), Roster.month.desc(), Roster.version.desc())
        ).first()
        if not roster:
            roster = db.scalars(select(Roster).order_by(Roster.created_at.desc())).first()
        if not roster:
            raise HTTPException(status_code=404, detail="No active roster found to export")
        target_roster_id = roster.id

    from app.modules.roster.router import export_roster_google_sheets, GoogleSheetsExportRequest
    sheets_payload = GoogleSheetsExportRequest(
        view_type="employee", filter_id=user.employee_id, google_access_token=payload.google_access_token
    )
    res = export_roster_google_sheets(roster_id=target_roster_id, payload=sheets_payload, db=db, _user=user)
    return res.model_dump()

