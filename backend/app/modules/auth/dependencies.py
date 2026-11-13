from __future__ import annotations

import hmac
from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.modules.auth.models import User, UserRole


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # 1. Bearer token in Authorization header (enables independent sessions per tab)
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    # 2. Query param (for EventSource SSE streams where custom headers cannot be set)
    if not token:
        token = request.query_params.get("token")

    # 3. Fall back to cookie (for backward compatibility with standard cookie clients)
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise AppError("NOT_AUTHENTICATED", "Authentication is required.", 401)
    payload = decode_access_token(token)
    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AppError("INVALID_TOKEN", "Authentication token is invalid.", 401) from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("NOT_AUTHENTICATED", "The user is inactive or no longer exists.", 401)
    if user.role == UserRole.POD_LEAD and not user.employee_id and user.pod_id:
        from app.modules.workforce.models import PodLead
        pl = db.scalar(select(PodLead).where(PodLead.pod_id == user.pod_id))
        if pl:
            user.employee_id = pl.employee_id
            db.commit()
            db.refresh(user)
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError("FORBIDDEN", "You do not have permission for this operation.", 403)
        return user

    return dependency


def verify_csrf(request: Request) -> None:
    # Requests authenticated via explicit Authorization header are immune to CSRF
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise AppError("CSRF_VALIDATION_FAILED", "A valid CSRF token is required.", 403)


def verify_csrf_for_logout(request: Request) -> None:
    # Requests authenticated via explicit Authorization header are immune to CSRF
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    if not header_token and not cookie_token:
        raise AppError("CSRF_VALIDATION_FAILED", "A valid CSRF token is required.", 403)
    if not header_token:
        raise AppError("CSRF_VALIDATION_FAILED", "A valid CSRF token is required.", 403)




require_manager = require_roles(UserRole.ADMIN, UserRole.OPERATIONS_MANAGER)
require_admin = require_roles(UserRole.ADMIN)
require_lead_or_manager = require_roles(UserRole.ADMIN, UserRole.OPERATIONS_MANAGER, UserRole.POD_LEAD)
require_brand_user = require_roles(UserRole.ADMIN, UserRole.OPERATIONS_MANAGER, UserRole.BRAND_USER)
require_employee_user = require_roles(UserRole.ADMIN, UserRole.OPERATIONS_MANAGER, UserRole.POD_LEAD, UserRole.EMPLOYEE)


def check_brand_scope(user: User, brand_id: UUID) -> None:
    """Enforces tenant isolation: brand users can only view or manage their own brand."""
    if user.role == UserRole.BRAND_USER and user.brand_id != brand_id:
        raise AppError("FORBIDDEN", "You are not authorized to view or modify other brand data.", 403)


def check_employee_scope(user: User, employee_id: UUID) -> None:
    """Enforces employee isolation: employees can only view or submit requests for themselves."""
    if user.role == UserRole.EMPLOYEE and user.employee_id != employee_id:
        raise AppError("FORBIDDEN", "You are not authorized to access another employee's records.", 403)


def check_pod_scope(user: User, pod_id: UUID) -> None:
    """Enforces pod boundary isolation: Pod Leads can only view resources within their pod."""
    if user.role == UserRole.POD_LEAD and user.pod_id != pod_id:
        raise AppError("FORBIDDEN", "Pod Leads are restricted to their assigned pod.", 403)


