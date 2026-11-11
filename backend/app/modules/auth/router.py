from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
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

