from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_access_token, new_csrf_token, verify_password
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, verify_csrf
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, LoginResponse, UserRead

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
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return LoginResponse(user=UserRead.model_validate(user), csrf_token=csrf_token)


@router.post("/logout", status_code=204, dependencies=[Depends(verify_csrf)])
def logout(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")


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


