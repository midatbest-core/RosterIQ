from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class EmployeeProfileRead(BaseModel):
    employee_id: UUID
    employee_code: str
    name: str
    email: str
    pod_id: UUID | None = None
    pod_name: str | None = None
    pod_lead_name: str | None = None
    pod_lead_email: str | None = None
    daily_capacity_minutes: int
    standard_start_time: str
    standard_end_time: str
    primary_assignments: list[dict]
    skills: list[dict]


class EmployeeTaskItem(BaseModel):
    allocation_id: UUID
    roster_id: UUID
    roster_name: str
    roster_status: str
    date: str
    day_of_week: str
    start_time: str
    end_time: str
    brand_name: str
    brand_code: str
    process_name: str
    process_code: str
    allocation_type: str
    status: str = "SCHEDULED"


class EmployeeAvailabilityRequestCreate(BaseModel):
    request_type: str = Field(description="LEAVE, SICK_LEAVE, WEEKLY_OFF, COMP_OFF, or PREFERENCE")
    start_date: str = Field(description="YYYY-MM-DD")
    end_date: str = Field(description="YYYY-MM-DD")
    reason_type: str = Field(description="PLANNED_LEAVE, SICK_LEAVE, APPROVED_OFF, COMP_OFF, TRAINING")
    notes: str = Field(min_length=3, max_length=255, description="Brief explanation")
    details: str | None = Field(default=None, description="Additional context")


class EmployeeAvailabilityRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    requested_by_user_id: UUID
    request_type: str
    start_date: date
    end_date: date
    reason_type: str
    notes: str | None = None
    details: str | None = None
    status: str
    review_notes: str | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    implemented_roster_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeReviewActionRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)
    manager_notes: str | None = Field(default=None, max_length=1000)


class EmployeeImpactPreview(BaseModel):
    request_id: UUID
    employee_id: UUID
    employee_name: str
    request_type: str
    dates: list[str]
    conflicting_allocations_count: int
    conflicting_allocations: list[dict]
    requires_reassignment: bool
    summary: str

