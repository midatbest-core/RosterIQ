from __future__ import annotations

from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.dependencies import require_lead_or_manager, require_manager, verify_csrf
from app.modules.operations.models import (
    Brand,
    BrandProcess,
    HolidayBehavior,
    HolidayCalendar,
    PrimaryAssignment,
    Process,
    RecordStatus,
)
from app.modules.operations.schemas import (
    BrandCreate,
    BrandProcessCreate,
    BrandProcessRead,
    BrandProcessUpdate,
    BrandRead,
    BrandUpdate,
    PrimaryAssignmentCreate,
    PrimaryAssignmentRead,
    PrimaryAssignmentUpdate,
    ProcessCreate,
    ProcessRead,
    ProcessUpdate,
)
from app.modules.workforce.models import Employee, EmployeeStatus

router = APIRouter(tags=["operations"], dependencies=[Depends(require_lead_or_manager)])
mutation_dependencies = [Depends(require_manager), Depends(verify_csrf)]


def require_record(db: Session, model: type, record_id: UUID, code: str, label: str):
    record = db.get(model, record_id)
    if record is None:
        raise AppError(code, f"{label} was not found.", 404)
    return record


def normalize_code(value: str) -> str:
    return value.strip().upper()


@router.get("/brands", response_model=list[BrandRead])
def list_brands(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Brand]:
    return list(db.scalars(select(Brand).order_by(Brand.name).offset(offset).limit(limit)).all())


@router.post("/brands", response_model=BrandRead, status_code=status.HTTP_201_CREATED, dependencies=mutation_dependencies)
def create_brand(payload: BrandCreate, db: Session = Depends(get_db)) -> Brand:
    brand = Brand(code=normalize_code(payload.code), name=payload.name.strip())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.get("/brands/{brand_id}", response_model=BrandRead)
def get_brand(brand_id: UUID, db: Session = Depends(get_db)) -> Brand:
    return require_record(db, Brand, brand_id, "BRAND_NOT_FOUND", "Brand")


@router.get("/brands/{brand_id}/operating-schedule")
def get_brand_operating_schedule(brand_id: UUID, db: Session = Depends(get_db)):
    brand = require_record(db, Brand, brand_id, "BRAND_NOT_FOUND", "Brand")
    from app.modules.operations.pattern_models import OperatingPattern, OperatingOverride
    from app.modules.workforce.models import Pod

    bps = db.scalars(
        select(BrandProcess).where(BrandProcess.brand_id == brand_id, BrandProcess.is_active == True)
    ).all()

    processes_data = []
    for bp in bps:
        proc = db.get(Process, bp.process_id)
        pattern = db.scalar(select(OperatingPattern).where(OperatingPattern.brand_process_id == bp.id))
        overrides = db.scalars(
            select(OperatingOverride)
            .where(OperatingOverride.brand_process_id == bp.id)
            .order_by(OperatingOverride.date)
        ).all()

        primaries = db.scalars(
            select(PrimaryAssignment)
            .where(PrimaryAssignment.brand_process_id == bp.id, PrimaryAssignment.is_active == True)
        ).all()
        assigned_emps = []
        for p in primaries:
            emp = db.get(Employee, p.employee_id)
            if emp:
                pod = db.get(Pod, emp.pod_id) if emp.pod_id else None
                assigned_emps.append({
                    "id": str(emp.id),
                    "code": emp.employee_code,
                    "name": emp.name,
                    "pod_name": pod.name if pod else "Unassigned",
                    "priority": p.priority,
                })

        pattern_label = "Custom Schedule"
        if pattern:
            days_set = set(int(d.strip()) for d in pattern.operating_days.split(",") if d.strip())
            if days_set == {0, 1, 2, 3, 4, 5, 6}:
                pattern_label = "365-Day Operations (Every Day)"
            elif days_set == {0, 1, 2, 3, 4, 5}:
                pattern_label = "Monday – Saturday (Sundays Off)"
            elif days_set == {0, 1, 2, 3, 4}:
                pattern_label = "Monday – Friday (Weekends Off)"
            elif days_set == {5, 6}:
                pattern_label = "Weekend Only Operations"

        processes_data.append({
            "brand_process_id": str(bp.id),
            "process_id": str(bp.process_id),
            "process_name": proc.name if proc else "Unknown Process",
            "process_code": proc.code if proc else "UNK",
            "pattern_label": pattern_label,
            "operating_days": [int(d.strip()) for d in pattern.operating_days.split(",") if d.strip()] if pattern else [0, 1, 2, 3, 4],
            "start_time": pattern.start_time.isoformat() if pattern else "09:00:00",
            "end_time": pattern.end_time.isoformat() if pattern else "18:00:00",
            "min_staffing_weekday": pattern.min_staffing_weekday if pattern else 1,
            "min_staffing_weekend": pattern.min_staffing_weekend if pattern else 0,
            "holiday_behavior": (pattern.holiday_behavior.value if hasattr(pattern.holiday_behavior, "value") else str(pattern.holiday_behavior)) if pattern else bp.holiday_behavior.value,
            "min_staffing_holiday": pattern.min_staffing_holiday if pattern else (bp.holiday_min_employees or 0),
            "overrides": [
                {
                    "date": o.date.isoformat(),
                    "is_closed": o.is_closed,
                    "override_start_time": o.override_start_time.isoformat() if o.override_start_time else None,
                    "override_end_time": o.override_end_time.isoformat() if o.override_end_time else None,
                    "override_min_staffing": o.override_min_staffing,
                    "reason": o.reason,
                }
                for o in overrides
            ],
            "assigned_employees": assigned_emps,
        })

    return {
        "brand_id": str(brand.id),
        "brand_name": brand.name,
        "brand_code": brand.code,
        "status": brand.status.value,
        "processes": processes_data,
    }


@router.patch("/brands/{brand_id}", response_model=BrandRead, dependencies=mutation_dependencies)
def update_brand(brand_id: UUID, payload: BrandUpdate, db: Session = Depends(get_db)) -> Brand:
    brand = require_record(db, Brand, brand_id, "BRAND_NOT_FOUND", "Brand")
    data = payload.model_dump(exclude_unset=True)
    if data.get("code"):
        data["code"] = normalize_code(data["code"])
    if data.get("name"):
        data["name"] = data["name"].strip()
    for field, value in data.items():
        setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/brands/{brand_id}", status_code=204, dependencies=mutation_dependencies)
def deactivate_brand(brand_id: UUID, db: Session = Depends(get_db)) -> None:
    brand = require_record(db, Brand, brand_id, "BRAND_NOT_FOUND", "Brand")
    brand.status = RecordStatus.INACTIVE
    db.commit()


@router.get("/processes", response_model=list[ProcessRead])
def list_processes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Process]:
    return list(db.scalars(select(Process).order_by(Process.name).offset(offset).limit(limit)).all())


@router.post("/processes", response_model=ProcessRead, status_code=status.HTTP_201_CREATED, dependencies=mutation_dependencies)
def create_process(payload: ProcessCreate, db: Session = Depends(get_db)) -> Process:
    process = Process(
        code=normalize_code(payload.code),
        name=payload.name.strip(),
        description=payload.description,
    )
    db.add(process)
    db.commit()
    db.refresh(process)
    return process


@router.get("/processes/{process_id}", response_model=ProcessRead)
def get_process(process_id: UUID, db: Session = Depends(get_db)) -> Process:
    return require_record(db, Process, process_id, "PROCESS_NOT_FOUND", "Process")


@router.patch("/processes/{process_id}", response_model=ProcessRead, dependencies=mutation_dependencies)
def update_process(process_id: UUID, payload: ProcessUpdate, db: Session = Depends(get_db)) -> Process:
    process = require_record(db, Process, process_id, "PROCESS_NOT_FOUND", "Process")
    data = payload.model_dump(exclude_unset=True)
    if data.get("code"):
        data["code"] = normalize_code(data["code"])
    if data.get("name"):
        data["name"] = data["name"].strip()
    for field, value in data.items():
        setattr(process, field, value)
    db.commit()
    db.refresh(process)
    return process


@router.delete("/processes/{process_id}", status_code=204, dependencies=mutation_dependencies)
def deactivate_process(process_id: UUID, db: Session = Depends(get_db)) -> None:
    process = require_record(db, Process, process_id, "PROCESS_NOT_FOUND", "Process")
    process.status = RecordStatus.INACTIVE
    db.commit()


def validate_holiday_policy(data: dict, current: BrandProcess | None = None) -> None:
    timezone = data.get("timezone", current.timezone if current else "Asia/Kolkata")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise AppError("INVALID_TIMEZONE", "Timezone must be a valid IANA timezone.", 422) from exc
    behavior = data.get("holiday_behavior", current.holiday_behavior if current else HolidayBehavior.NORMAL)
    minimum = data.get(
        "holiday_min_employees",
        current.holiday_min_employees if current else None,
    )
    if behavior == HolidayBehavior.REDUCED and minimum is None:
        raise AppError("INVALID_HOLIDAY_POLICY", "Reduced holiday behavior requires holiday_min_employees.", 422)
    if behavior != HolidayBehavior.REDUCED and minimum is not None:
        raise AppError("INVALID_HOLIDAY_POLICY", "holiday_min_employees is valid only for reduced holidays.", 422)


@router.get("/brand-processes", response_model=list[BrandProcessRead])
def list_brand_processes(
    brand_id: UUID | None = None,
    process_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[BrandProcess]:
    statement = select(BrandProcess).order_by(BrandProcess.brand_id, BrandProcess.process_id)
    if brand_id is not None:
        statement = statement.where(BrandProcess.brand_id == brand_id)
    if process_id is not None:
        statement = statement.where(BrandProcess.process_id == process_id)
    return list(db.scalars(statement.offset(offset).limit(limit)).all())


@router.post("/brand-processes", response_model=BrandProcessRead, status_code=status.HTTP_201_CREATED, dependencies=mutation_dependencies)
def create_brand_process(payload: BrandProcessCreate, db: Session = Depends(get_db)) -> BrandProcess:
    brand = require_record(db, Brand, payload.brand_id, "BRAND_NOT_FOUND", "Brand")
    process = require_record(db, Process, payload.process_id, "PROCESS_NOT_FOUND", "Process")
    if brand.status != RecordStatus.ACTIVE or process.status != RecordStatus.ACTIVE:
        raise AppError("INACTIVE_REFERENCE", "Brand and process must both be active.", 422)
    if payload.holiday_calendar_id is not None:
        require_record(db, HolidayCalendar, payload.holiday_calendar_id, "HOLIDAY_CALENDAR_NOT_FOUND", "Holiday calendar")
    item = BrandProcess(**payload.model_dump())
    db.add(item)
    db.flush()

    from app.modules.operations.pattern_models import OperatingPattern
    default_pattern = OperatingPattern(
        brand_process_id=item.id,
        operating_days="0,1,2,3,4",
        min_staffing_weekday=1,
        min_staffing_weekend=0,
    )
    db.add(default_pattern)
    db.commit()
    db.refresh(item)
    return item


@router.get("/brand-processes/{brand_process_id}", response_model=BrandProcessRead)
def get_brand_process(brand_process_id: UUID, db: Session = Depends(get_db)) -> BrandProcess:
    return require_record(db, BrandProcess, brand_process_id, "BRAND_PROCESS_NOT_FOUND", "Brand-process")


@router.patch("/brand-processes/{brand_process_id}", response_model=BrandProcessRead, dependencies=mutation_dependencies)
def update_brand_process(
    brand_process_id: UUID,
    payload: BrandProcessUpdate,
    db: Session = Depends(get_db),
) -> BrandProcess:
    item = require_record(db, BrandProcess, brand_process_id, "BRAND_PROCESS_NOT_FOUND", "Brand-process")
    data = payload.model_dump(exclude_unset=True)
    if "holiday_calendar_id" in data and data["holiday_calendar_id"] is not None:
        require_record(db, HolidayCalendar, data["holiday_calendar_id"], "HOLIDAY_CALENDAR_NOT_FOUND", "Holiday calendar")
    validate_holiday_policy(data, item)
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/brand-processes/{brand_process_id}", status_code=204, dependencies=mutation_dependencies)
def deactivate_brand_process(brand_process_id: UUID, db: Session = Depends(get_db)) -> None:
    item = require_record(db, BrandProcess, brand_process_id, "BRAND_PROCESS_NOT_FOUND", "Brand-process")
    item.is_active = False
    db.commit()


def validate_assignment_references(db: Session, employee_id: UUID, brand_process_id: UUID) -> None:
    employee = require_record(db, Employee, employee_id, "EMPLOYEE_NOT_FOUND", "Employee")
    brand_process = require_record(
        db, BrandProcess, brand_process_id, "BRAND_PROCESS_NOT_FOUND", "Brand-process"
    )
    if employee.status != EmployeeStatus.ACTIVE or not brand_process.is_active:
        raise AppError("INACTIVE_REFERENCE", "Employee and brand-process must both be active.", 422)


def ensure_no_assignment_overlap(
    db: Session,
    employee_id: UUID,
    brand_process_id: UUID,
    effective_from: date,
    effective_to: date | None,
    exclude_id: UUID | None = None,
) -> None:
    end = effective_to or date.max
    statement = select(PrimaryAssignment.id).where(
        PrimaryAssignment.employee_id == employee_id,
        PrimaryAssignment.brand_process_id == brand_process_id,
        PrimaryAssignment.is_active.is_(True),
        PrimaryAssignment.effective_from <= end,
        or_(PrimaryAssignment.effective_to.is_(None), PrimaryAssignment.effective_to >= effective_from),
    )
    if exclude_id is not None:
        statement = statement.where(PrimaryAssignment.id != exclude_id)
    if db.scalar(statement) is not None:
        raise AppError(
            "ASSIGNMENT_DATE_OVERLAP",
            "An active assignment already covers part of this effective date range.",
            409,
        )


@router.get("/assignments", response_model=list[PrimaryAssignmentRead], dependencies=[Depends(require_manager)])
def list_assignments(
    employee_id: UUID | None = None,
    brand_process_id: UUID | None = None,
    active_only: bool = True,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[PrimaryAssignment]:
    statement = select(PrimaryAssignment).order_by(PrimaryAssignment.effective_from)
    if employee_id is not None:
        statement = statement.where(PrimaryAssignment.employee_id == employee_id)
    if brand_process_id is not None:
        statement = statement.where(PrimaryAssignment.brand_process_id == brand_process_id)
    if active_only:
        statement = statement.where(PrimaryAssignment.is_active.is_(True))
    return list(db.scalars(statement.offset(offset).limit(limit)).all())


@router.post("/assignments", response_model=PrimaryAssignmentRead, status_code=status.HTTP_201_CREATED, dependencies=mutation_dependencies)
def create_assignment(
    payload: PrimaryAssignmentCreate,
    db: Session = Depends(get_db),
) -> PrimaryAssignment:
    validate_assignment_references(db, payload.employee_id, payload.brand_process_id)
    ensure_no_assignment_overlap(
        db,
        payload.employee_id,
        payload.brand_process_id,
        payload.effective_from,
        payload.effective_to,
    )
    assignment = PrimaryAssignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments/{assignment_id}", response_model=PrimaryAssignmentRead, dependencies=[Depends(require_manager)])
def get_assignment(assignment_id: UUID, db: Session = Depends(get_db)) -> PrimaryAssignment:
    return require_record(db, PrimaryAssignment, assignment_id, "ASSIGNMENT_NOT_FOUND", "Assignment")


@router.patch("/assignments/{assignment_id}", response_model=PrimaryAssignmentRead, dependencies=mutation_dependencies)
def update_assignment(
    assignment_id: UUID,
    payload: PrimaryAssignmentUpdate,
    db: Session = Depends(get_db),
) -> PrimaryAssignment:
    assignment = require_record(db, PrimaryAssignment, assignment_id, "ASSIGNMENT_NOT_FOUND", "Assignment")
    data = payload.model_dump(exclude_unset=True)
    start = data.get("effective_from", assignment.effective_from)
    end = data.get("effective_to", assignment.effective_to)
    if end is not None and end < start:
        raise AppError("INVALID_DATE_RANGE", "effective_to cannot be earlier than effective_from.", 422)
    if data.get("is_active", assignment.is_active):
        ensure_no_assignment_overlap(
            db,
            assignment.employee_id,
            assignment.brand_process_id,
            start,
            end,
            assignment.id,
        )
    for field, value in data.items():
        setattr(assignment, field, value)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/assignments/{assignment_id}", status_code=204, dependencies=mutation_dependencies)
def end_assignment(assignment_id: UUID, db: Session = Depends(get_db)) -> None:
    assignment = require_record(db, PrimaryAssignment, assignment_id, "ASSIGNMENT_NOT_FOUND", "Assignment")
    assignment.is_active = False
    today = date.today()
    if assignment.effective_to is None or assignment.effective_to > today:
        assignment.effective_to = max(assignment.effective_from, today)
    db.commit()

