from __future__ import annotations

from datetime import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.session import get_db
from app.modules.auth.dependencies import require_lead_or_manager, require_manager, verify_csrf
from app.modules.auth.models import User, UserRole
from app.modules.operations.models import Process
from app.modules.workforce.models import (
    Employee,
    EmployeeProcessSkill,
    EmployeeStatus,
    Pod,
    PodLead,
)
from app.modules.workforce.schemas import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    PodCreate,
    PodRead,
    PodUpdate,
    SkillRead,
    SkillSet,
)

router = APIRouter(tags=["workforce"], dependencies=[Depends(require_lead_or_manager)])
mutation_dependencies = [Depends(require_manager), Depends(verify_csrf)]


def require_employee(db: Session, employee_id: UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise AppError("EMPLOYEE_NOT_FOUND", "Employee was not found.", 404)
    return employee


def check_employee_pod_scope(user: User, employee: Employee) -> None:
    if user.role == UserRole.POD_LEAD and user.pod_id:
        if employee.pod_id != user.pod_id:
            raise AppError("FORBIDDEN", "You do not have permission to view employees from other pods.", 403)


def require_pod(db: Session, pod_id: UUID) -> Pod:
    pod = db.scalar(select(Pod).options(selectinload(Pod.lead)).where(Pod.id == pod_id))
    if pod is None:
        raise AppError("POD_NOT_FOUND", "Pod was not found.", 404)
    return pod


def require_record(db: Session, model: type, record_id: UUID, code: str, label: str):
    record = db.get(model, record_id)
    if record is None:
        raise AppError(code, f"{label} was not found.", 404)
    return record



def validate_pod(db: Session, pod_id: UUID | None) -> None:
    if pod_id is not None and db.get(Pod, pod_id) is None:
        raise AppError("POD_NOT_FOUND", "Assigned pod was not found.", 422)


def validate_shift(start: time, end: time, capacity: int) -> None:
    if end <= start:
        raise AppError("INVALID_SHIFT", "Shift end must be later than shift start.", 422)
    duration = end.hour * 60 + end.minute - start.hour * 60 - start.minute
    if duration > capacity:
        raise AppError("INVALID_CAPACITY", "Shift duration cannot exceed daily capacity.", 422)


def pod_read(pod: Pod) -> PodRead:
    return PodRead(
        id=pod.id,
        name=pod.name,
        is_active=pod.is_active,
        lead_employee_id=pod.lead.employee_id if pod.lead else None,
    )


def set_pod_lead(db: Session, pod: Pod, employee_id: UUID | None) -> None:
    if pod.lead is not None:
        db.delete(pod.lead)
        db.flush()
    if employee_id is not None:
        employee = require_employee(db, employee_id)
        if employee.pod_id != pod.id:
            raise AppError("INVALID_POD_LEAD", "Pod lead must be an employee in the same pod.", 422)
        pod.lead = PodLead(pod_id=pod.id, employee_id=employee_id)


@router.get("/pods", response_model=list[PodRead])
def list_pods(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[PodRead]:
    pods = db.scalars(
        select(Pod).options(selectinload(Pod.lead)).order_by(Pod.name).offset(offset).limit(limit)
    ).all()
    return [pod_read(pod) for pod in pods]


@router.post("/pods", response_model=PodRead, status_code=status.HTTP_201_CREATED, dependencies=mutation_dependencies)
def create_pod(payload: PodCreate, db: Session = Depends(get_db)) -> PodRead:
    pod = Pod(name=payload.name.strip())
    db.add(pod)
    db.flush()
    if payload.lead_employee_id is not None:
        set_pod_lead(db, pod, payload.lead_employee_id)
    db.commit()
    return pod_read(require_pod(db, pod.id))


@router.get("/pods/{pod_id}", response_model=PodRead)
def get_pod(pod_id: UUID, db: Session = Depends(get_db)) -> PodRead:
    return pod_read(require_pod(db, pod_id))


@router.patch("/pods/{pod_id}", response_model=PodRead, dependencies=mutation_dependencies)
def update_pod(pod_id: UUID, payload: PodUpdate, db: Session = Depends(get_db)) -> PodRead:
    pod = require_pod(db, pod_id)
    data = payload.model_dump(exclude_unset=True)
    lead_was_set = "lead_employee_id" in data
    lead_id = data.pop("lead_employee_id", None)
    for field, value in data.items():
        setattr(pod, field, value.strip() if isinstance(value, str) else value)
    if lead_was_set:
        set_pod_lead(db, pod, lead_id)
    db.commit()
    return pod_read(require_pod(db, pod.id))


@router.delete("/pods/{pod_id}", status_code=204, dependencies=mutation_dependencies)
def deactivate_pod(pod_id: UUID, db: Session = Depends(get_db)) -> None:
    pod = require_pod(db, pod_id)
    pod.is_active = False
    db.commit()


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(
    pod_id: UUID | None = None,
    employee_status: EmployeeStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> list[Employee]:
    statement = select(Employee).order_by(Employee.employee_code).offset(offset).limit(limit)
    if current_user.role == UserRole.POD_LEAD and current_user.pod_id:
        statement = statement.where(Employee.pod_id == current_user.pod_id)
    elif pod_id is not None:
        statement = statement.where(Employee.pod_id == pod_id)
    if employee_status is not None:
        statement = statement.where(Employee.status == employee_status)
    return list(db.scalars(statement).all())


@router.post("/employees", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED, dependencies=mutation_dependencies)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> Employee:
    validate_pod(db, payload.pod_id)
    data = payload.model_dump()
    data["employee_code"] = payload.employee_code.upper()
    data["email"] = str(payload.email).lower()
    employee = Employee(**data)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> Employee:
    employee = require_employee(db, employee_id)
    check_employee_pod_scope(current_user, employee)
    return employee


@router.patch("/employees/{employee_id}", response_model=EmployeeRead, dependencies=mutation_dependencies)
def update_employee(employee_id: UUID, payload: EmployeeUpdate, db: Session = Depends(get_db)) -> Employee:
    employee = require_employee(db, employee_id)
    data = payload.model_dump(exclude_unset=True)
    if "pod_id" in data:
        validate_pod(db, data["pod_id"])
    if data.get("employee_code"):
        data["employee_code"] = data["employee_code"].upper()
    if data.get("email"):
        data["email"] = str(data["email"]).lower()
    start = data.get("standard_start_time", employee.standard_start_time)
    end = data.get("standard_end_time", employee.standard_end_time)
    capacity = data.get("daily_capacity_minutes", employee.daily_capacity_minutes)
    validate_shift(start, end, capacity)
    for field, value in data.items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/employees/{employee_id}", status_code=204, dependencies=mutation_dependencies)
def deactivate_employee(employee_id: UUID, db: Session = Depends(get_db)) -> None:
    employee = require_employee(db, employee_id)
    employee.status = EmployeeStatus.INACTIVE
    db.commit()


@router.get("/employees/{employee_id}/skills", response_model=list[SkillRead])
def list_employee_skills(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> list[EmployeeProcessSkill]:
    employee = require_employee(db, employee_id)
    check_employee_pod_scope(current_user, employee)
    return list(
        db.scalars(
            select(EmployeeProcessSkill)
            .where(EmployeeProcessSkill.employee_id == employee_id)
            .order_by(EmployeeProcessSkill.process_id)
        ).all()
    )


@router.put("/employees/{employee_id}/skills", response_model=list[SkillRead], dependencies=mutation_dependencies)
def replace_employee_skills(
    employee_id: UUID,
    payload: SkillSet,
    db: Session = Depends(get_db),
) -> list[EmployeeProcessSkill]:
    require_employee(db, employee_id)
    process_ids = [skill.process_id for skill in payload.skills]
    if len(process_ids) != len(set(process_ids)):
        raise AppError("DUPLICATE_SKILL", "Each process may appear only once in the skill set.", 422)
    existing_processes = set(db.scalars(select(Process.id).where(Process.id.in_(process_ids))).all())
    missing = set(process_ids) - existing_processes
    if missing:
        raise AppError("PROCESS_NOT_FOUND", "One or more skill processes do not exist.", 422, {"ids": [str(item) for item in missing]})
    db.execute(delete(EmployeeProcessSkill).where(EmployeeProcessSkill.employee_id == employee_id))
    db.add_all(
        [EmployeeProcessSkill(employee_id=employee_id, **skill.model_dump()) for skill in payload.skills]
    )
    db.commit()
    return list(
        db.scalars(select(EmployeeProcessSkill).where(EmployeeProcessSkill.employee_id == employee_id)).all()
    )


from app.modules.workforce.availability_models import (
    EmployeePreference,
    EmployeeUnavailability,
)
from app.modules.workforce.schemas import (
    EmployeePreferenceRead,
    EmployeePreferenceWrite,
    EmployeeUnavailabilityCreate,
    EmployeeUnavailabilityRead,
)


@router.get("/employees/{employee_id}/unavailability", response_model=list[EmployeeUnavailabilityRead])
def list_employee_unavailability(
    employee_id: UUID, db: Session = Depends(get_db)
) -> list[EmployeeUnavailability]:
    require_record(db, Employee, employee_id, "EMPLOYEE_NOT_FOUND", "Employee")
    return list(
        db.scalars(
            select(EmployeeUnavailability)
            .where(EmployeeUnavailability.employee_id == employee_id)
            .order_by(EmployeeUnavailability.date)
        ).all()
    )


@router.post(
    "/employees/{employee_id}/unavailability",
    response_model=EmployeeUnavailabilityRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=mutation_dependencies,
)
def add_employee_unavailability(
    employee_id: UUID,
    payload: EmployeeUnavailabilityCreate,
    db: Session = Depends(get_db),
) -> EmployeeUnavailability:
    require_record(db, Employee, employee_id, "EMPLOYEE_NOT_FOUND", "Employee")
    existing = db.scalar(
        select(EmployeeUnavailability).where(
            EmployeeUnavailability.employee_id == employee_id,
            EmployeeUnavailability.date == payload.date,
        )
    )
    if existing:
        raise AppError("CONFLICT", "Unavailability record already exists for this date.", 409)

    item = EmployeeUnavailability(
        employee_id=employee_id,
        date=payload.date,
        reason_type=payload.reason_type,
        is_approved=payload.is_approved,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/employees/{employee_id}/unavailability/{unavailability_id}",
    status_code=204,
    dependencies=mutation_dependencies,
)
def delete_employee_unavailability(
    employee_id: UUID, unavailability_id: UUID, db: Session = Depends(get_db)
) -> None:
    item = require_record(
        db, EmployeeUnavailability, unavailability_id, "UNAVAILABILITY_NOT_FOUND", "Unavailability record"
    )
    db.delete(item)
    db.commit()


@router.get("/employees/{employee_id}/preferences", response_model=EmployeePreferenceRead | None)
def get_employee_preferences(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> EmployeePreference | None:
    employee = require_record(db, Employee, employee_id, "EMPLOYEE_NOT_FOUND", "Employee")
    check_employee_pod_scope(current_user, employee)
    return db.scalar(
        select(EmployeePreference).where(EmployeePreference.employee_id == employee_id)
    )


@router.put(
    "/employees/{employee_id}/preferences",
    response_model=EmployeePreferenceRead,
    dependencies=mutation_dependencies,
)
def set_employee_preferences(
    employee_id: UUID,
    payload: EmployeePreferenceWrite,
    db: Session = Depends(get_db),
) -> EmployeePreference:
    require_record(db, Employee, employee_id, "EMPLOYEE_NOT_FOUND", "Employee")
    pref = db.scalar(
        select(EmployeePreference).where(EmployeePreference.employee_id == employee_id)
    )
    if not pref:
        pref = EmployeePreference(
            employee_id=employee_id,
            preferred_weekly_off_days=payload.preferred_weekly_off_days,
            notes=payload.notes,
        )
        db.add(pref)
    else:
        pref.preferred_weekly_off_days = payload.preferred_weekly_off_days
        pref.notes = payload.notes

    db.commit()
    db.refresh(pref)
    return pref
