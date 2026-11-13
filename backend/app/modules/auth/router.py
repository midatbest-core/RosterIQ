from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, new_csrf_token, verify_password
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, verify_csrf, verify_csrf_for_logout
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import (
    DemoLoginRequest,
    DemoRoleRead,
    LoginRequest,
    LoginResponse,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)

    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    settings = get_settings()
    access_token = create_access_token(user.id, user.role.value)
    csrf_token = new_csrf_token()
    samesite_val = settings.effective_cookie_samesite
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite_val,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=samesite_val,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return LoginResponse(
        user=UserRead.model_validate(user),
        csrf_token=csrf_token,
        access_token=access_token,
    )


@router.post("/logout", status_code=204, dependencies=[Depends(verify_csrf_for_logout)])
def logout(response: Response) -> None:
    settings = get_settings()
    samesite_val = settings.effective_cookie_samesite
    response.delete_cookie(
        "access_token",
        path="/",
        secure=settings.cookie_secure,
        samesite=samesite_val,
    )
    response.delete_cookie(
        "csrf_token",
        path="/",
        secure=settings.cookie_secure,
        samesite=samesite_val,
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


def _get_reference_status(db: Session, ref_type: str | None, ref_id: uuid.UUID | None) -> str | None:
    if not ref_type or not ref_id:
        return None
    if ref_type == "employee_availability_request":
        from app.modules.workforce.request_models import EmployeeAvailabilityRequest
        req = db.get(EmployeeAvailabilityRequest, ref_id)
        return req.status if req else None
    elif ref_type == "brand_change_request":
        from app.modules.operations.request_models import BrandChangeRequest
        req = db.get(BrandChangeRequest, ref_id)
        return req.status if req else None
    return None


@router.get("/notifications")
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Returns the authenticated user's notifications sorted newest first."""
    from app.modules.auth.notification_models import Notification
    notifs = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "reference_type": n.reference_type,
            "reference_id": str(n.reference_id) if n.reference_id else None,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "request_status": _get_reference_status(db, n.reference_type, n.reference_id),
        }
        for n in notifs
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Marks a notification as read."""
    from app.modules.auth.notification_models import Notification
    import uuid
    notif = db.get(Notification, uuid.UUID(notification_id))
    if not notif or notif.user_id != user.id:
        raise AppError("NOT_FOUND", "Notification not found.", 404)
    notif.is_read = True
    db.commit()
    return {"status": "ok"}


@router.delete("/notifications/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Deletes a user's notification. Fails with 404/403 if it does not belong to the user."""
    from app.modules.auth.notification_models import Notification
    import uuid
    notif = db.get(Notification, uuid.UUID(notification_id))
    if not notif or notif.user_id != user.id:
        raise AppError("NOT_FOUND", "Notification not found.", 404)
    db.delete(notif)
    db.commit()
    return {"status": "deleted", "id": notification_id}


@router.get("/notifications/stream")
async def stream_notifications(
    request: Request,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) endpoint delivering real-time notifications to the authenticated user.
    Maintains periodic heartbeats and isolates notifications per user.
    """
    import asyncio
    import json
    from app.modules.auth.broadcaster import broadcaster

    queue = await broadcaster.subscribe(user.id)

    async def event_generator():
        try:
            # Send initial connected handshake event
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'user_id': str(user.id)})}\n\n"
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                try:
                    # Wait up to 15 seconds for new notification, otherwise emit heartbeat
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: notification\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield f"event: ping\ndata: {json.dumps({'time': datetime.now(UTC).isoformat()})}\n\n"
        finally:
            await broadcaster.unsubscribe(user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@router.get("/quick-login-accounts")
def get_quick_login_accounts(db: Session = Depends(get_db)) -> dict:
    """Returns all available demo brand and employee accounts with login credentials.
    Strictly forbidden in production mode."""
    settings = get_settings()
    if settings.environment.lower() == "production":
        raise AppError("FORBIDDEN", "Demo accounts directory is strictly disabled in production.", 403)
    if not settings.enable_demo_credentials:
        raise AppError("FORBIDDEN", "Demo access is disabled.", 403)

    from app.modules.workforce.models import Employee, Pod
    from app.modules.operations.models import Brand

    employees = db.scalars(
        select(Employee).where(
            Employee.status == "ACTIVE",
            ~Employee.employee_code.in_(["EMP55", "EMP56", "EMP57", "EMP001"]),
            ~Employee.email.in_(["aditya@example.com", "demo@example.com", "rohit@example.com", "botemp@email.com"]),
        ).order_by(Employee.name)
    ).all()
    pod_map = {p.id: p.name for p in db.scalars(select(Pod)).all()}

    emp_list = []
    for emp in employees:
        pod_name = pod_map.get(emp.pod_id, "Unassigned Pod")
        emp_list.append({
            "id": str(emp.id),
            "name": emp.name,
            "employee_code": emp.employee_code,
            "email": emp.email,
            "password": "EmployeePass123!",
            "pod_name": pod_name,
            "role": "EMPLOYEE",
        })

    brands = db.scalars(
        select(Brand).where(
            Brand.status == "ACTIVE",
            ~Brand.name.ilike("%new brand%"),
            ~Brand.code.in_(["NEW", "TEST"]),
        ).order_by(Brand.name)
    ).all()
    brand_list = []
    for b in brands:
        b_clean = b.code.lower().replace("_", "").replace("-", "")
        brand_list.append({
            "id": str(b.id),
            "name": b.name,
            "code": b.code,
            "email": f"brand.{b_clean}@example.com",
            "password": "BrandPass123!",
            "role": "BRAND_USER",
        })

    return {
        "employees": emp_list,
        "brands": brand_list,
    }


@router.get("/demo-accounts")


def get_demo_accounts(db: Session = Depends(get_db)) -> dict:
    """Returns local demonstration accounts grouped by role, pod, and brand. Only available in local/demo mode."""
    settings = get_settings()
    if settings.environment != "development":
        raise AppError("FORBIDDEN", "Demo accounts directory is disabled in production.", 403)

    from app.modules.workforce.models import Employee, Pod
    from app.modules.operations.models import Brand

    users = db.scalars(select(User).where(User.is_active == True)).all()
    emp_map = {e.id: e for e in db.scalars(select(Employee)).all()}
    pod_map = {p.id: p for p in db.scalars(select(Pod)).all()}
    brand_map = {b.id: b for b in db.scalars(select(Brand)).all()}

    admins = []
    ops = []
    leads = []
    brands = []
    employees_by_pod: dict[str, list[dict]] = {}

    for u in users:
        emp = emp_map.get(u.employee_id) if u.employee_id else None
        b = brand_map.get(u.brand_id) if u.brand_id else None
        p = pod_map.get(u.pod_id) if u.pod_id else (pod_map.get(emp.pod_id) if emp and emp.pod_id else None)
        pod_name = p.name if p else "Unassigned Pod"

        item = {
            "id": str(u.id),
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "name": emp.name if emp else (b.name if b else u.email.split("@")[0].title()),
            "brand_id": str(u.brand_id) if u.brand_id else None,
            "brand_name": b.name if b else None,
            "employee_id": str(u.employee_id) if u.employee_id else None,
            "pod_id": str(p.id) if p else None,
            "pod_name": pod_name,
        }

        role_str = u.role.value if hasattr(u.role, "value") else str(u.role)
        if role_str == "ADMIN":
            admins.append(item)
        elif role_str == "OPERATIONS_MANAGER":
            ops.append(item)
        elif role_str == "POD_LEAD":
            leads.append(item)
        elif role_str == "BRAND_USER":
            brands.append(item)
        elif role_str == "EMPLOYEE":
            employees_by_pod.setdefault(pod_name, []).append(item)

    return {
        "admins": admins,
        "operations_managers": ops,
        "pod_leads": leads,
        "brand_users": sorted(brands, key=lambda x: x["name"] or ""),
        "employees_by_pod": {k: sorted(v, key=lambda x: x["name"]) for k, v in employees_by_pod.items()},
    }


@router.get("/presentation-demo-accounts")
def get_presentation_demo_accounts() -> list[dict[str, str]]:
    """
    Returns presentation demo accounts for college demonstrations.
    Strictly forbidden when production environment is active.
    Requires settings.enable_demo_credentials to be True.
    """
    settings = get_settings()

    # Rule 1: Forbid unconditionally if environment is production
    if settings.environment.lower() == "production":
        raise AppError(
            code="FORBIDDEN",
            message="Presentation demo accounts are strictly disabled in production.",
            status_code=403,
        )

    # Rule 2: Require explicit demo-credentials flag to be enabled
    if not settings.enable_demo_credentials:
        raise AppError(
            code="FORBIDDEN",
            message="Presentation demo credentials flag (ROSTERIQ_ENABLE_DEMO_CREDENTIALS) is disabled.",
            status_code=403,
        )

    role_display_names = {
        "ADMIN": "System Admin",
        "OPERATIONS_MANAGER": "Operations Manager",
        "POD_LEAD": "Pod Lead",
        "BRAND_USER": "Brand User",
        "EMPLOYEE": "Employee",
    }

    accounts: list[dict[str, str]] = []

    # Check local staging credentials file
    candidate_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.staging_test_credentials.local")),
        os.path.abspath("backend/.staging_test_credentials.local"),
        os.path.abspath(".staging_test_credentials.local"),
    ]
    file_path = next((p for p in candidate_paths if os.path.exists(p)), None)

    if file_path:
        current_account: dict[str, str] = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    if current_account.get("email") and current_account.get("password"):
                        accounts.append(current_account)
                    role = line[1:-1]
                    current_account = {
                        "role": role,
                        "role_name": role_display_names.get(role, role),
                        "email": "",
                        "password": "",
                        "description": "",
                    }
                elif line.startswith("Email: ") and current_account:
                    current_account["email"] = line.split("Email: ", 1)[1].strip()
                elif line.startswith("Password: ") and current_account:
                    current_account["password"] = line.split("Password: ", 1)[1].strip()
                elif line.startswith("Description: ") and current_account:
                    current_account["description"] = line.split("Description: ", 1)[1].strip()
            if current_account.get("email") and current_account.get("password"):
                accounts.append(current_account)

    # Fallback to demo_credentials_json if running on hosted container without local file
    if not accounts:
        raw_json = (
            settings.demo_credentials_json
            or os.environ.get("ROSTERIQ_DEMO_CREDENTIALS_JSON", "")
            or os.environ.get("DEMO_CREDENTIALS_JSON", "")
        )
        if raw_json and raw_json.strip():
            raw_stripped = raw_json.strip()
            parsed = None
            try:
                parsed = json.loads(raw_stripped)
            except Exception:
                try:
                    import ast

                    parsed = ast.literal_eval(raw_stripped)
                except Exception:
                    pass

            # Handle double-stringified JSON (e.g. pasted into cloud dashboard with outer quotes)
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed.strip())
                except Exception:
                    try:
                        import ast

                        parsed = ast.literal_eval(parsed.strip())
                    except Exception:
                        pass

            if isinstance(parsed, list):
                accounts = [item for item in parsed if isinstance(item, dict)]

    if not accounts:
        raise AppError(
            code="NOT_FOUND",
            message="No staging demo credentials configured.",
            status_code=404,
        )

    # Ensure role_name is populated
    for acc in accounts:
        if "role" in acc and not acc.get("role_name"):
            acc["role_name"] = role_display_names.get(acc["role"], acc["role"])

    order = ["ADMIN", "OPERATIONS_MANAGER", "POD_LEAD", "BRAND_USER", "EMPLOYEE"]
    account_map = {a.get("role"): a for a in accounts}
    sorted_accounts = [account_map[r] for r in order if r in account_map]
    return sorted_accounts if sorted_accounts else accounts


@router.get("/demo-roles", response_model=list[DemoRoleRead])
def get_demo_roles(db: Session = Depends(get_db)) -> list[DemoRoleRead]:
    """
    Returns predefined staging demo roles for 1-click presentation login.
    Strictly disabled when environment is production.
    No passwords are ever exposed.
    """
    settings = get_settings()
    if settings.environment.lower() == "production":
        raise AppError(
            code="FORBIDDEN",
            message="Demo roles are strictly disabled in production.",
            status_code=403,
        )

    if not settings.enable_demo_credentials:
        raise AppError(
            code="FORBIDDEN",
            message="Demo access is disabled.",
            status_code=403,
        )

    roles_metadata = [
        {
            "role": "ADMIN",
            "name": "System Admin",
            "description": "Full company-wide visibility, system configuration & audits",
            "default_email": "admin.staging@rosteriq.io",
        },
        {
            "role": "OPERATIONS_MANAGER",
            "name": "Operations Manager",
            "description": "Roster generation, constraint rules & requests review center",
            "default_email": "ops.staging@rosteriq.io",
        },
        {
            "role": "POD_LEAD",
            "name": "Pod Lead",
            "description": "Pod Alpha team scheduling, unavailability logging & approvals",
            "default_email": "lead.staging@rosteriq.io",
        },
        {
            "role": "BRAND_USER",
            "name": "Brand User",
            "description": "Kavya Organic Skincare portal, operating calendar & change requests",
            "default_email": "brand.staging@rosteriq.io",
        },
        {
            "role": "EMPLOYEE",
            "name": "Employee",
            "description": "Aarav Sharma (EMP-001) personal schedule, shifts & leave requests",
            "default_email": "employee.staging@rosteriq.io",
        },
    ]

    results: list[DemoRoleRead] = []
    for r in roles_metadata:
        role_enum = UserRole(r["role"])
        user = db.scalar(select(User).where(User.email == r["default_email"], User.is_active == True))
        if not user:
            user = db.scalar(select(User).where(User.role == role_enum, User.is_active == True))
        email_display = user.email if user else r["default_email"]
        results.append(
            DemoRoleRead(
                role=r["role"],
                name=r["name"],
                description=r["description"],
                email=email_display,
            )
        )

    return results


@router.post("/demo-login", response_model=LoginResponse)
def demo_login(
    payload: DemoLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    1-Click direct authentication for presentation demo roles.
    Authenticates the client directly into the real database account with appropriate
    permissions and tenant scope, setting secure authentication cookies.
    Strictly disabled in production.
    """
    settings = get_settings()
    if settings.environment.lower() == "production":
        raise AppError(
            code="FORBIDDEN",
            message="Demo login is strictly disabled in production.",
            status_code=403,
        )

    if not settings.enable_demo_credentials:
        raise AppError(
            code="FORBIDDEN",
            message="Demo login is disabled.",
            status_code=403,
        )

    role_str = payload.role.strip().upper()
    try:
        role_enum = UserRole(role_str)
    except ValueError:
        raise AppError(
            code="INVALID_ROLE",
            message=f"Invalid demo role: {payload.role}",
            status_code=400,
        )

    staging_email_map = {
        UserRole.ADMIN: "admin.staging@rosteriq.io",
        UserRole.OPERATIONS_MANAGER: "ops.staging@rosteriq.io",
        UserRole.POD_LEAD: "lead.staging@rosteriq.io",
        UserRole.BRAND_USER: "brand.staging@rosteriq.io",
        UserRole.EMPLOYEE: "employee.staging@rosteriq.io",
    }

    target_email = staging_email_map.get(role_enum)
    user = None
    if target_email:
        user = db.scalar(select(User).where(User.email == target_email, User.is_active == True))

    if user is None:
        user = db.scalar(select(User).where(User.role == role_enum, User.is_active == True))

    if user is None:
        raise AppError(
            code="NOT_FOUND",
            message=f"No active account found for role {role_str}",
            status_code=404,
        )

    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user.id, user.role.value)
    csrf_token = new_csrf_token()
    samesite_val = settings.effective_cookie_samesite

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite_val,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=samesite_val,
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return LoginResponse(
        user=UserRead.model_validate(user),
        csrf_token=csrf_token,
        access_token=access_token,
    )



