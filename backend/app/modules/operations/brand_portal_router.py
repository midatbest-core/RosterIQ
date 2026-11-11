from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, time, date
import calendar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_user,
    require_brand_user,
    require_manager,
    check_brand_scope,
    verify_csrf,
)
from app.modules.auth.models import User, UserRole
from app.modules.auth.notifications import create_notification, notify_managers
from app.modules.operations.models import Brand, BrandProcess, Process, HolidayBehavior
from app.modules.operations.pattern_models import OperatingPattern, OperatingOverride
from app.modules.operations.request_models import BrandChangeRequest, RequestStatus
from app.modules.operations.brand_portal_schemas import (
    BrandPlanChangeRequestCreate,
    BrandChangeRequestRead,
    BrandImpactPreview,
    BrandReviewActionRequest,
)
from app.modules.roster.models import Roster, RosterAllocation, RosterStatus
from app.modules.roster.router import compute_config_hash, check_and_mark_stale_rosters
from app.modules.workforce.models import Employee

router = APIRouter(prefix="/brand-portal", tags=["brand-portal"])


@router.get("/me")
def get_brand_profile(
    db: Session = Depends(get_db),
    user: User = Depends(require_brand_user),
) -> dict:
    """Returns the authenticated brand user's brand profile, processes, active patterns, and overrides."""
    if not user.brand_id:
        raise AppError("FORBIDDEN", "User is not linked to any brand.", 403)

    brand = db.get(Brand, user.brand_id)
    if not brand:
        raise AppError("NOT_FOUND", "Brand not found.", 404)

    bps = db.scalars(select(BrandProcess).where(BrandProcess.brand_id == brand.id)).all()
    bp_ids = [bp.id for bp in bps]

    patterns = {
        p.brand_process_id: p
        for p in db.scalars(select(OperatingPattern).where(OperatingPattern.brand_process_id.in_(bp_ids))).all()
    }
    overrides = db.scalars(
        select(OperatingOverride).where(OperatingOverride.brand_process_id.in_(bp_ids))
    ).all()
    proc_map = {p.id: p.name for p in db.scalars(select(Process)).all()}

    processes_data = []
    for bp in bps:
        pat = patterns.get(bp.id)
        processes_data.append({
            "brand_process_id": str(bp.id),
            "process_id": str(bp.process_id),
            "process_name": proc_map.get(bp.process_id, "Unknown Process"),
            "operating_days": [int(d) for d in pat.operating_days.split(",") if d.strip()] if pat else [0, 1, 2, 3, 4],
            "start_time": pat.start_time.isoformat() if pat else "09:00:00",
            "end_time": pat.end_time.isoformat() if pat else "18:00:00",
            "min_staffing_weekday": pat.min_staffing_weekday if pat else 1,
            "min_staffing_weekend": pat.min_staffing_weekend if pat else 1,
            "holiday_behavior": pat.holiday_behavior.value if pat and hasattr(pat.holiday_behavior, "value") else "NORMAL",
        })

    return {
        "brand_id": str(brand.id),
        "code": brand.code,
        "name": brand.name,
        "timezone": getattr(brand, "timezone", "UTC"),
        "processes": processes_data,
        "active_overrides_count": len(overrides),
    }


@router.post("/requests", response_model=BrandChangeRequestRead, status_code=status.HTTP_201_CREATED)
def submit_brand_change_request(
    payload: BrandPlanChangeRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_brand_user),
) -> BrandChangeRequestRead:
    """Submits a brand operating plan change request without mutating active rules."""
    if not user.brand_id:
        raise AppError("FORBIDDEN", "User has no associated brand.", 403)

    brand = db.get(Brand, user.brand_id)
    if not brand:
        raise AppError("NOT_FOUND", "Brand not found.", 404)

    # Tenant scoping & IDOR prevention
    if payload.brand_process_id:
        bp = db.get(BrandProcess, payload.brand_process_id)
        if not bp or bp.brand_id != user.brand_id:
            raise AppError("FORBIDDEN", "The specified brand process does not belong to your brand.", 403)

    # Fetch current configuration
    current_cfg = {}
    if payload.brand_process_id:
        pat = db.scalar(select(OperatingPattern).where(OperatingPattern.brand_process_id == payload.brand_process_id))
        if pat:
            current_cfg = {
                "operating_days": [int(d) for d in pat.operating_days.split(",") if d.strip()],
                "start_time": pat.start_time.isoformat(),
                "end_time": pat.end_time.isoformat(),
                "min_staffing_weekday": pat.min_staffing_weekday,
                "min_staffing_weekend": pat.min_staffing_weekend,
                "holiday_behavior": pat.holiday_behavior.value if hasattr(pat.holiday_behavior, "value") else str(pat.holiday_behavior),
            }
    else:
        # Brand-wide change
        current_cfg = {"scope": "ALL_BRAND_PROCESSES"}

    requested_cfg = {
        "request_type": payload.request_type,
        "reason": payload.reason,
    }
    if payload.operating_days is not None:
        requested_cfg["operating_days"] = payload.operating_days
    if payload.start_time:
        requested_cfg["start_time"] = payload.start_time
    if payload.end_time:
        requested_cfg["end_time"] = payload.end_time
    if payload.min_staffing_weekday is not None:
        requested_cfg["min_staffing_weekday"] = payload.min_staffing_weekday
    if payload.min_staffing_weekend is not None:
        requested_cfg["min_staffing_weekend"] = payload.min_staffing_weekend
    if payload.holiday_behavior:
        requested_cfg["holiday_behavior"] = payload.holiday_behavior
    if payload.override_date:
        requested_cfg["override_date"] = payload.override_date
    if payload.is_closed is not None:
        requested_cfg["is_closed"] = payload.is_closed

    req = BrandChangeRequest(
        id=uuid.uuid4(),
        brand_id=user.brand_id,
        brand_process_id=payload.brand_process_id,
        requested_by_user_id=user.id,
        request_type=payload.request_type,
        current_configuration=json.dumps(current_cfg),
        requested_configuration=json.dumps(requested_cfg),
        status=RequestStatus.PENDING.value,
    )
    db.add(req)
    db.flush()

    # Notify managers persistently
    notify_managers(
        db=db,
        title=f"New Brand Plan Request: {brand.name}",
        message=f"{brand.name} requested {payload.request_type.replace('_', ' ').title()}: {payload.reason}",
        notification_type="BRAND_REQUEST_SUBMITTED",
        reference_type="brand_change_request",
        reference_id=req.id,
    )
    db.commit()
    db.refresh(req)

    res = BrandChangeRequestRead.model_validate(req)
    res.brand_name = brand.name
    res.requested_by_email = user.email
    return res


@router.get("/requests", response_model=list[BrandChangeRequestRead])
def list_brand_change_requests(
    brand_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BrandChangeRequestRead]:
    """Lists change requests. Brand users are strictly scoped to their own brand."""
    stmt = select(BrandChangeRequest).order_by(BrandChangeRequest.created_at.desc())

    if user.role == UserRole.BRAND_USER:
        if not user.brand_id:
            return []
        stmt = stmt.where(BrandChangeRequest.brand_id == user.brand_id)
    else:
        # Operations Managers / Admins can optionally filter
        if brand_id:
            stmt = stmt.where(BrandChangeRequest.brand_id == brand_id)

    if status_filter:
        stmt = stmt.where(BrandChangeRequest.status == status_filter.upper())

    records = db.scalars(stmt).all()
    brand_map = {b.id: b.name for b in db.scalars(select(Brand)).all()}
    user_map = {u.id: u.email for u in db.scalars(select(User)).all()}
    bp_proc_map = {}
    for bp in db.scalars(select(BrandProcess)).all():
        proc = db.get(Process, bp.process_id)
        if proc:
            bp_proc_map[bp.id] = proc.name

    result = []
    for r in records:
        item = BrandChangeRequestRead.model_validate(r)
        item.brand_name = brand_map.get(r.brand_id, "Unknown Brand")
        item.requested_by_email = user_map.get(r.requested_by_user_id, "Unknown User")
        item.process_name = bp_proc_map.get(r.brand_process_id) if r.brand_process_id else "All Processes"
        result.append(item)
    return result


@router.get("/requests/{request_id}", response_model=BrandChangeRequestRead)
def get_brand_change_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BrandChangeRequestRead:
    """Retrieves a single request with strict tenant isolation."""
    req = db.get(BrandChangeRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Change request not found.", 404)

    if user.role == UserRole.BRAND_USER:
        check_brand_scope(user, req.brand_id)

    brand = db.get(Brand, req.brand_id)
    creator = db.get(User, req.requested_by_user_id)

    item = BrandChangeRequestRead.model_validate(req)
    item.brand_name = brand.name if brand else "Unknown Brand"
    item.requested_by_email = creator.email if creator else "Unknown User"
    return item


@router.post("/requests/{request_id}/preview-impact", response_model=BrandImpactPreview)
def preview_brand_request_impact(
    request_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> BrandImpactPreview:
    """Analyzes the exact impact of an operating change on current rosters before approving."""
    req = db.get(BrandChangeRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Change request not found.", 404)

    brand = db.get(Brand, req.brand_id)
    if not brand:
        raise AppError("NOT_FOUND", "Brand not found.", 404)

    req_cfg = json.loads(req.requested_configuration)
    curr_cfg = json.loads(req.current_configuration)

    bps = (
        [db.get(BrandProcess, req.brand_process_id)]
        if req.brand_process_id
        else db.scalars(select(BrandProcess).where(BrandProcess.brand_id == brand.id)).all()
    )
    bp_ids = [bp.id for bp in bps if bp]

    # Find affected draft rosters (e.g. November 2026)
    draft_rosters = db.scalars(
        select(Roster).where(Roster.status.in_([RosterStatus.DRAFT, RosterStatus.VALIDATED, RosterStatus.STALE]))
    ).all()

    affected_dates: set[str] = set()
    affected_employees: dict[UUID, dict] = {}
    invalid_existing = 0
    new_uncovered = 0

    # Calculate days impacted
    if req.request_type == "OPERATING_DAYS" and "operating_days" in req_cfg:
        new_days = set(req_cfg["operating_days"])
        old_days = set(curr_cfg.get("operating_days", [0, 1, 2, 3, 4]))
        added_days = new_days - old_days
        removed_days = old_days - new_days

        # Scan active draft roster allocations
        for r in draft_rosters:
            num_days = calendar.monthrange(r.year, r.month)[1]
            for d_idx in range(1, num_days + 1):
                d = date(r.year, r.month, d_idx)
                wd = d.weekday()
                if wd in added_days:
                    affected_dates.add(d.isoformat())
                    new_uncovered += len(bp_ids) * req_cfg.get("min_staffing_weekend" if wd in (5, 6) else "min_staffing_weekday", 1)
                elif wd in removed_days:
                    affected_dates.add(d.isoformat())
                    # Check existing allocations falling on newly closed days
                    allocs = db.scalars(
                        select(RosterAllocation).where(
                            RosterAllocation.roster_id == r.id,
                            RosterAllocation.date == d,
                            RosterAllocation.brand_process_id.in_(bp_ids),
                        )
                    ).all()
                    invalid_existing += len(allocs)
                    for a in allocs:
                        emp = db.get(Employee, a.employee_id)
                        if emp:
                            affected_employees[emp.id] = {"id": str(emp.id), "name": emp.name, "date": str(d)}

    elif req.request_type == "MIN_STAFFING":
        old_staff = curr_cfg.get("min_staffing_weekday", 1)
        new_staff = req_cfg.get("min_staffing_weekday", old_staff)
        staff_diff = new_staff - old_staff
        summary_txt = f"Staffing requirement changing from {old_staff} to {new_staff} per interval."
        for r in draft_rosters:
            num_days = calendar.monthrange(r.year, r.month)[1]
            for d_idx in range(1, num_days + 1):
                d = date(r.year, r.month, d_idx)
                if d.weekday() < 5 and staff_diff > 0:
                    affected_dates.add(d.isoformat())
                    new_uncovered += staff_diff * len(bp_ids)

    summary = (
        f"Request impacts {len(affected_dates)} calendar dates across {len(bp_ids)} brand processes. "
        f"{invalid_existing} existing allocations become invalid, and {new_uncovered} new staffing vacancies are created. "
        f"Approval will flag {len(draft_rosters)} draft roster(s) as STALE awaiting resolution."
    )

    proc_names = [db.get(Process, bp.process_id).name for bp in bps if bp and db.get(Process, bp.process_id)]

    return BrandImpactPreview(
        request_id=req.id,
        brand_id=brand.id,
        brand_name=brand.name,
        request_type=req.request_type,
        affected_dates=sorted(list(affected_dates))[:15],
        affected_processes=proc_names,
        old_requirement=json.dumps(curr_cfg),
        new_requirement=json.dumps(req_cfg),
        affected_employees_count=len(affected_employees),
        affected_employees=list(affected_employees.values())[:10],
        invalid_existing_allocations_count=invalid_existing,
        new_uncovered_intervals_count=new_uncovered,
        affected_draft_rosters=[{"id": str(r.id), "name": r.name, "status": r.status.value} for r in draft_rosters],
        summary=summary,
    )


@router.post("/requests/{request_id}/approve", response_model=BrandChangeRequestRead)
def approve_brand_request(
    request_id: UUID,
    payload: BrandReviewActionRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> BrandChangeRequestRead:
    """Transactionally approves brand request, updates operating pattern, marks rosters STALE, and sets ROSTER_PENDING."""
    req = db.get(BrandChangeRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)
    if req.status in (RequestStatus.APPROVED.value, RequestStatus.ROSTER_PENDING.value, RequestStatus.IMPLEMENTED.value):
        raise AppError("CONFLICT", f"Request is already in {req.status} state.", 409)

    brand = db.get(Brand, req.brand_id)
    req_cfg = json.loads(req.requested_configuration)
    now = datetime.now(timezone.utc)

    # 1. Update OperatingPattern or create OperatingOverride
    bps = (
        [db.get(BrandProcess, req.brand_process_id)]
        if req.brand_process_id
        else db.scalars(select(BrandProcess).where(BrandProcess.brand_id == brand.id)).all()
    )

    for bp in bps:
        if not bp:
            continue
        pat = db.scalar(select(OperatingPattern).where(OperatingPattern.brand_process_id == bp.id))
        if not pat:
            pat = OperatingPattern(brand_process_id=bp.id)
            db.add(pat)

        if "operating_days" in req_cfg:
            pat.operating_days = ",".join(str(d) for d in req_cfg["operating_days"])
        if "start_time" in req_cfg:
            pat.start_time = time.fromisoformat(req_cfg["start_time"])
        if "end_time" in req_cfg:
            pat.end_time = time.fromisoformat(req_cfg["end_time"])
        if "min_staffing_weekday" in req_cfg:
            pat.min_staffing_weekday = int(req_cfg["min_staffing_weekday"])
        if "min_staffing_weekend" in req_cfg:
            pat.min_staffing_weekend = int(req_cfg["min_staffing_weekend"])
        if "holiday_behavior" in req_cfg:
            pat.holiday_behavior = HolidayBehavior(req_cfg["holiday_behavior"])

        if req.request_type == "DATE_OVERRIDE" and "override_date" in req_cfg:
            ov_date = date.fromisoformat(req_cfg["override_date"])
            ov = db.scalar(select(OperatingOverride).where(
                OperatingOverride.brand_process_id == bp.id,
                OperatingOverride.date == ov_date,
            ))
            if not ov:
                ov = OperatingOverride(brand_process_id=bp.id, date=ov_date)
                db.add(ov)
            ov.is_closed = req_cfg.get("is_closed", False)
            if "start_time" in req_cfg:
                ov.override_start_time = time.fromisoformat(req_cfg["start_time"])
            if "end_time" in req_cfg:
                ov.override_end_time = time.fromisoformat(req_cfg["end_time"])
            if "min_staffing" in req_cfg:
                ov.override_min_staffing = int(req_cfg["min_staffing"])

    # 2. Mark affected draft rosters as STALE
    new_hash = compute_config_hash(db)
    check_and_mark_stale_rosters(db, new_hash)

    # 3. Transition status to ROSTER_PENDING
    req.status = RequestStatus.ROSTER_PENDING.value
    review_notes = (payload.manager_notes or payload.notes) if payload else "Approved by Operations Manager."
    req.review_notes = review_notes
    req.reviewed_by_user_id = user.id
    req.reviewed_at = now
    db.flush()

    # 4. Notify Brand User
    create_notification(
        db=db,
        user_id=req.requested_by_user_id,
        title=f"Plan Request Approved: {brand.name}",
        message=f"Your operating plan change for {brand.name} was approved by operations and is now pending roster resolution & publishing.",
        notification_type="BRAND_REQUEST_APPROVED",
        reference_type="brand_change_request",
        reference_id=req.id,
    )
    db.commit()
    db.refresh(req)

    res = BrandChangeRequestRead.model_validate(req)
    res.brand_name = brand.name
    return res


@router.post("/requests/{request_id}/reject", response_model=BrandChangeRequestRead)
def reject_brand_request(
    request_id: UUID,
    payload: BrandReviewActionRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> BrandChangeRequestRead:
    """Rejects brand request with notes and notifies the brand user."""
    req = db.get(BrandChangeRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)
    if req.status in (RequestStatus.APPROVED.value, RequestStatus.IMPLEMENTED.value):
        raise AppError("CONFLICT", f"Cannot reject request in {req.status} state.", 409)

    brand = db.get(Brand, req.brand_id)
    now = datetime.now(timezone.utc)
    notes = payload.notes if payload and payload.notes else "Request rejected after capacity review."

    req.status = RequestStatus.REJECTED.value
    req.review_notes = notes
    req.reviewed_by_user_id = user.id
    req.reviewed_at = now
    db.flush()

    create_notification(
        db=db,
        user_id=req.requested_by_user_id,
        title=f"Plan Request Rejected: {brand.name if brand else 'Brand'}",
        message=f"Your operating plan request was rejected: {notes}",
        notification_type="BRAND_REQUEST_REJECTED",
        reference_type="brand_change_request",
        reference_id=req.id,
    )
    db.commit()
    db.refresh(req)

    res = BrandChangeRequestRead.model_validate(req)
    if brand:
        res.brand_name = brand.name
    return res


@router.post("/requests/{request_id}/mark-implemented", response_model=BrandChangeRequestRead)
def mark_request_implemented(
    request_id: UUID,
    roster_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
) -> BrandChangeRequestRead:
    """Marks request IMPLEMENTED after successful roster resolution and publication."""
    req = db.get(BrandChangeRequest, request_id)
    if not req:
        raise AppError("NOT_FOUND", "Request not found.", 404)

    if roster_id:
        roster = db.get(Roster, roster_id)
        if not roster or roster.status != RosterStatus.PUBLISHED:
            raise AppError("BAD_REQUEST", "Target roster must be PUBLISHED to mark request implemented.", 400)
        req.implemented_roster_id = roster.id

    brand = db.get(Brand, req.brand_id)
    req.status = RequestStatus.IMPLEMENTED.value
    roster = None
    if roster_id:
        roster = db.get(Roster, roster_id)
        if not roster or roster.status != RosterStatus.PUBLISHED:
            raise AppError("BAD_REQUEST", "Target roster must be PUBLISHED to mark request implemented.", 400)
        req.implemented_roster_id = roster.id
    db.flush()

    message = (
        f"Your approved operating plan changes are now live in published Roster v{roster.version} ({roster.name})."
        if roster
        else "Your approved operating plan changes have been marked as implemented in active rosters."
    )

    create_notification(
        db=db,
        user_id=req.requested_by_user_id,
        title=f"Schedule Published: {brand.name if brand else 'Brand'}",
        message=message,
        notification_type="ROSTER_PUBLISHED_FOR_BRAND",
        reference_type="roster" if roster else "brand_change_request",
        reference_id=roster.id if roster else req.id,
    )
    db.commit()
    db.refresh(req)

    res = BrandChangeRequestRead.model_validate(req)
    if brand:
        res.brand_name = brand.name
    return res
