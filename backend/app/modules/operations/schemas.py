from __future__ import annotations

from typing import Any
from datetime import date
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.operations.models import HolidayBehavior, RecordStatus


class BrandCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)


class BrandUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    status: RecordStatus | None = None


class BrandRead(BrandCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RecordStatus
    temporary_password: str | None = None
    login_email: str | None = None


class ProcessCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class ProcessUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    status: RecordStatus | None = None


class ProcessRead(ProcessCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RecordStatus


class BrandProcessBase(BaseModel):
    brand_id: UUID
    process_id: UUID
    holiday_calendar_id: UUID | None = None
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=64)
    holiday_behavior: HolidayBehavior = HolidayBehavior.NORMAL
    holiday_min_employees: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_holiday_policy(self) -> BrandProcessBase:
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        if self.holiday_behavior == HolidayBehavior.REDUCED and self.holiday_min_employees is None:
            raise ValueError("holiday_min_employees is required for REDUCED holiday behavior")
        if self.holiday_behavior != HolidayBehavior.REDUCED and self.holiday_min_employees is not None:
            raise ValueError("holiday_min_employees is only valid for REDUCED holiday behavior")
        return self


class BrandProcessCreate(BrandProcessBase):
    pass


class BrandProcessUpdate(BaseModel):
    holiday_calendar_id: UUID | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    holiday_behavior: HolidayBehavior | None = None
    holiday_min_employees: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class BrandProcessRead(BrandProcessBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    conflict_check: dict[str, Any] | None = None


class PrimaryAssignmentBase(BaseModel):
    employee_id: UUID
    brand_process_id: UUID
    effective_from: date
    effective_to: date | None = None
    priority: int = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> PrimaryAssignmentBase:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be earlier than effective_from")
        return self


class PrimaryAssignmentCreate(PrimaryAssignmentBase):
    pass


class PrimaryAssignmentUpdate(BaseModel):
    effective_from: date | None = None
    effective_to: date | None = None
    priority: int | None = Field(default=None, ge=1, le=100)
    is_active: bool | None = None


class PrimaryAssignmentRead(PrimaryAssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conflict_check: dict[str, Any] | None = None
    is_active: bool

