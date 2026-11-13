from __future__ import annotations

from datetime import time
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, select, func, update
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import hash_password
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


@router.delete("/pods/{pod_id}", dependencies=mutation_dependencies)
def delete_pod(pod_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    pod = require_pod(db, pod_id)
    
    # 1. Find all employees currently in this pod
    pod_employees = db.scalars(select(Employee).where(Employee.pod_id == pod_id)).all()
    
    # 2. Find other active pods to relocate members to
    other_pods = db.scalars(select(Pod).where(Pod.id != pod_id, Pod.is_active == True)).all()
    target_pod = None
    moved_count = len(pod_employees)
    
    if other_pods:
        # Find the other pod with the least active employees
        counts = []
        for op in other_pods:
            c = db.scalar(
                select(func.count(Employee.id)).where(
                    Employee.pod_id == op.id,
                    Employee.status == EmployeeStatus.ACTIVE,
                )
            ) or 0
            counts.append((c, op))
        counts.sort(key=lambda x: (x[0], x[1].name))
        target_pod = counts[0][1]
        
        # Move all employees to target pod
        target_id = target_pod.id if target_pod else None
        db.execute(
            update(Employee)
            .where(Employee.pod_id == pod_id)
            .values(pod_id=target_id)
        )
        emp_ids = [e.id for e in pod_employees]
        if emp_ids:
            db.execute(
                update(User)
                .where(User.employee_id.in_(emp_ids))
                .values(pod_id=target_id)
            )
        # Detach employees from pod relationship collection so SQLAlchemy UOW won't null out pod_id on cascade
        pod.employees = []
    else:
        db.execute(
            update(Employee)
            .where(Employee.pod_id == pod_id)
            .values(pod_id=None)
        )
        emp_ids = [e.id for e in pod_employees]
        if emp_ids:
            db.execute(
                update(User)
                .where(User.employee_id.in_(emp_ids))
                .values(pod_id=None)
            )
        pod.employees = []
                
    # 3. Clean up any pod lead mapping for this pod
    db.execute(delete(PodLead).where(PodLead.pod_id == pod_id))
    
    # 4. Delete the pod
    pod_name = pod.name
    db.delete(pod)
    db.commit()
    
    return {
        "status": "SUCCESS",
        "deleted_pod_id": str(pod_id),
        "deleted_pod_name": pod_name,
        "moved_employees_count": moved_count,
        "target_pod_id": str(target_pod.id) if target_pod else None,
        "target_pod_name": target_pod.name if target_pod else "Unassigned",
        "message": (
            f"Pod '{pod_name}' deleted successfully. "
            f"{moved_count} employees relocated to '{target_pod.name}' (pod with least members)."
            if target_pod
            else f"Pod '{pod_name}' deleted. {moved_count} employees set to unassigned."
        ),
    }


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

    # Provision User credentials for the newly created employee
    temp_pass = "EmployeePass123!"
    user = db.scalar(select(User).where(User.email == employee.email))
    if not user:
        user = User(
            email=employee.email,
            password_hash=hash_password(temp_pass),
            role=UserRole.EMPLOYEE,
            employee_id=employee.id,
            pod_id=employee.pod_id,
            is_active=True,
        )
        db.add(user)
        db.commit()
    else:
        user.employee_id = employee.id
        user.pod_id = employee.pod_id
        db.commit()

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


@router.get("/employees/{employee_id}/reallocation-preview", dependencies=[Depends(require_lead_or_manager)])
def get_employee_reallocation_preview(
    employee_id: UUID,
    target_pod_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> dict[str, Any]:
    employee = require_employee(db, employee_id)
    check_employee_pod_scope(current_user, employee)

    if current_user.role == UserRole.POD_LEAD and current_user.pod_id:
        if target_pod_id and target_pod_id != current_user.pod_id:
            raise AppError("FORBIDDEN", "Pod Leads cannot reallocate employees to another pod.", 403)

    current_pod = db.get(Pod, employee.pod_id) if employee.pod_id else None
    target_pod = db.get(Pod, target_pod_id) if target_pod_id else None

    # 1. Brand coverage & primary assignments
    from app.modules.operations.models import Brand, BrandProcess, PrimaryAssignment
    from app.modules.roster.models import RosterAllocation
    from app.modules.workforce.availability_models import EmployeeUnavailability

    primaries = db.scalars(
        select(PrimaryAssignment)
        .where(PrimaryAssignment.employee_id == employee_id, PrimaryAssignment.is_active == True)
    ).all()

    services = []
    for pa in primaries:
        bp = db.get(BrandProcess, pa.brand_process_id)
        if bp:
            b = db.get(Brand, bp.brand_id)
            p = db.get(Process, bp.process_id)
            services.append({
                "brand_name": b.name if b else "Brand",
                "process_name": p.name if p else "Process",
                "brand_process_id": str(bp.id),
            })

    # 2. Approved leaves
    leaves_count = db.scalar(
        select(func.count(EmployeeUnavailability.id))
        .where(EmployeeUnavailability.employee_id == employee_id, EmployeeUnavailability.is_approved == True)
    ) or 0

    # 3. Existing draft allocations
    allocs_count = db.scalar(
        select(func.count(RosterAllocation.id)).where(RosterAllocation.employee_id == employee_id)
    ) or 0

    # 4. Employee skills
    skills = db.scalars(
        select(EmployeeProcessSkill).where(EmployeeProcessSkill.employee_id == employee_id, EmployeeProcessSkill.is_active == True)
    ).all()
    skill_names = []
    for s in skills:
        proc = db.get(Process, s.process_id)
        if proc:
            skill_names.append(proc.name)

    is_cross_pod = bool(target_pod_id and target_pod_id != employee.pod_id)

    return {
        "employee_id": str(employee.id),
        "employee_name": employee.name,
        "current_pod_id": str(employee.pod_id) if employee.pod_id else None,
        "current_pod_name": current_pod.name if current_pod else "Unassigned",
        "target_pod_id": str(target_pod.id) if target_pod else None,
        "target_pod_name": target_pod.name if target_pod else "Unassigned",
        "is_cross_pod": is_cross_pod,
        "requires_ops_manager_approval": is_cross_pod,
        "affected_services": services,
        "affected_services_count": len(services),
        "employee_skills": skill_names,
        "approved_leaves_count": leaves_count,
        "existing_allocations_count": allocs_count,
        "warning": (
            "WARNING: THIS REALLOCATION MAY AFFECT BRAND SERVICES. "
            "Reassigning this employee may cause staffing shortages or scheduling violations in the services currently supported by the employee."
        ),
    }


@router.patch("/employees/{employee_id}", response_model=EmployeeRead, dependencies=mutation_dependencies)
def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_lead_or_manager),
) -> Employee:
    employee = require_employee(db, employee_id)
    data = payload.model_dump(exclude_unset=True)

    if current_user.role == UserRole.POD_LEAD and current_user.pod_id:
        if employee.pod_id != current_user.pod_id or ("pod_id" in data and data["pod_id"] != current_user.pod_id):
            raise AppError("FORBIDDEN", "Pod Leads cannot reallocate employees to another pod.", 403)

    if "pod_id" in data and data["pod_id"] is not None:
        validate_pod(db, data["pod_id"])

    # If pod changed, update linked user record too
    if "pod_id" in data and data["pod_id"] != employee.pod_id:
        from app.modules.roster.models import Roster, RosterStatus
        db.execute(
            update(User)
            .where(User.employee_id == employee_id)
            .values(pod_id=data["pod_id"])
        )
        # Mark draft rosters as STALE
        draft_rosters = db.scalars(
            select(Roster).where(Roster.status.in_([RosterStatus.DRAFT, RosterStatus.VALIDATED]))
        ).all()
        for r in draft_rosters:
            r.status = RosterStatus.STALE

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


@router.get("/employees/{employee_id}/deletion-impact", dependencies=[Depends(require_lead_or_manager)])
def get_employee_deletion_impact(
    employee_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_lead_or_manager),
) -> dict[str, Any]:
    employee = require_employee(db, employee_id)
    check_employee_pod_scope(_user, employee)

    pod = db.get(Pod, employee.pod_id) if employee.pod_id else None

    # 1. Active brand/process assignments
    from app.modules.operations.models import Brand, BrandProcess, PrimaryAssignment
    from app.modules.roster.models import Roster, RosterAllocation, RosterStatus

    primaries = db.scalars(
        select(PrimaryAssignment)
        .where(PrimaryAssignment.employee_id == employee_id, PrimaryAssignment.is_active == True)
    ).all()

    assigned_services = []
    for pa in primaries:
        bp = db.get(BrandProcess, pa.brand_process_id)
        if bp:
            b = db.get(Brand, bp.brand_id)
            p = db.get(Process, bp.process_id)
            assigned_services.append({
                "brand_process_id": str(bp.id),
                "brand_name": b.name if b else "Brand",
                "process_name": p.name if p else "Process",
                "priority": pa.priority,
            })

    # 2. Upcoming draft roster impact
    draft_rosters = db.scalars(
        select(Roster).where(Roster.status.in_([RosterStatus.DRAFT, RosterStatus.VALIDATED]))
    ).all()

    # 3. Published historical allocations count
    pub_allocs_count = db.scalar(
        select(func.count(RosterAllocation.id))
        .join(Roster, RosterAllocation.roster_id == Roster.id)
        .where(RosterAllocation.employee_id == employee_id, Roster.status == RosterStatus.PUBLISHED)
    ) or 0

    return {
        "employee_id": str(employee_id),
        "employee_name": employee.name,
        "employee_code": employee.employee_code,
        "pod_name": pod.name if pod else "Unassigned",
        "active_services": assigned_services,
        "active_services_count": len(assigned_services),
        "draft_rosters_affected_count": len(draft_rosters),
        "has_published_history": pub_allocs_count > 0,
        "published_allocations_count": pub_allocs_count,
        "historical_records_preserved": True,
    }


@router.delete("/employees/{employee_id}", dependencies=mutation_dependencies)
def deactivate_employee(employee_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    employee = require_employee(db, employee_id)
    emp_name = employee.name
    
    # 1. Soft deletion / deactivation
    employee.status = EmployeeStatus.INACTIVE

    # 2. Deactivate primary assignments for this employee
    from app.modules.operations.models import PrimaryAssignment
    from app.modules.roster.models import Roster, RosterStatus

    db.execute(
        update(PrimaryAssignment)
        .where(PrimaryAssignment.employee_id == employee_id)
        .values(is_active=False)
    )

    # 3. Mark affected draft rosters as STALE
    draft_rosters = db.scalars(
        select(Roster).where(Roster.status.in_([RosterStatus.DRAFT, RosterStatus.VALIDATED]))
    ).all()
    for r in draft_rosters:
        r.status = RosterStatus.STALE

    db.commit()

    return {
        "status": "SUCCESS",
        "employee_id": str(employee_id),
        "employee_name": emp_name,
        "new_status": "INACTIVE",
        "message": f"Employee '{emp_name}' deactivated successfully. Historical allocations and audit logs are preserved.",
    }


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
