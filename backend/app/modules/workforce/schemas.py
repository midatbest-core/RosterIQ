from __future__ import annotations

from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.modules.workforce.models import EmployeeStatus, SkillProficiency


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    pod_id: UUID | None = None
    daily_capacity_minutes: int = Field(default=480, ge=1, le=1440)
    standard_start_time: time
    standard_end_time: time

    @model_validator(mode="after")
    def validate_same_day_shift(self) -> EmployeeBase:
        if self.standard_end_time <= self.standard_start_time:
            raise ValueError("standard_end_time must be later than standard_start_time")
        start = self.standard_start_time.hour * 60 + self.standard_start_time.minute
        end = self.standard_end_time.hour * 60 + self.standard_end_time.minute
        if end - start > self.daily_capacity_minutes:
            raise ValueError("standard shift duration cannot exceed daily_capacity_minutes")
        return self


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    employee_code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    email: EmailStr | None = None
    pod_id: UUID | None = None
    status: EmployeeStatus | None = None
    daily_capacity_minutes: int | None = Field(default=None, ge=1, le=1440)
    standard_start_time: time | None = None
    standard_end_time: time | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: EmployeeStatus


class PodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lead_employee_id: UUID | None = None


class PodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    lead_employee_id: UUID | None = None
    is_active: bool | None = None


class PodRead(BaseModel):
    id: UUID
    name: str
    is_active: bool
    lead_employee_id: UUID | None


class SkillWrite(BaseModel):
    process_id: UUID
    proficiency: SkillProficiency
    is_active: bool = True


class SkillRead(SkillWrite):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID


class SkillSet(BaseModel):
    skills: list[SkillWrite]


from datetime import date
from pydantic import BaseModel, ConfigDict
from app.modules.workforce.availability_models import AbsenceReasonType


class EmployeeUnavailabilityCreate(BaseModel):
    date: date
    reason_type: AbsenceReasonType = AbsenceReasonType.PLANNED_LEAVE
    is_approved: bool = True
    notes: str | None = None


class EmployeeUnavailabilityRead(EmployeeUnavailabilityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID


class EmployeePreferenceWrite(BaseModel):
    preferred_weekly_off_days: str = "0,6"  # comma-separated e.g. "0,6"
    notes: str | None = None


class EmployeePreferenceRead(EmployeePreferenceWrite):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
