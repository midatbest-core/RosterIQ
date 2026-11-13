from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.auth.models import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole
    brand_id: UUID | None = None
    employee_id: UUID | None = None
    pod_id: UUID | None = None
    is_active: bool
    last_login_at: datetime | None


class LoginResponse(BaseModel):
    user: UserRead
    csrf_token: str
    access_token: str | None = None


class DemoLoginRequest(BaseModel):
    role: str = Field(..., description="Role to authenticate as: ADMIN, OPERATIONS_MANAGER, POD_LEAD, BRAND_USER, EMPLOYEE")


class DemoRoleRead(BaseModel):
    role: str
    name: str
    description: str
    email: str

