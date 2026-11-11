from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BrandPlanChangeRequestCreate(BaseModel):
    brand_process_id: UUID | None = None
    request_type: str = Field(description="OPERATING_DAYS, OPERATING_HOURS, MIN_STAFFING, HOLIDAY_BEHAVIOR, or DATE_OVERRIDE")
    operating_days: list[int] | None = Field(default=None, description="Active weekdays: 0=Mon, 1=Tue, ..., 6=Sun")
    start_time: str | None = Field(default=None, description="HH:MM:SS format")
    end_time: str | None = Field(default=None, description="HH:MM:SS format")
    min_staffing_weekday: int | None = None
    min_staffing_weekend: int | None = None
    holiday_behavior: str | None = Field(default=None, description="CLOSED, NORMAL, or REDUCED")
    override_date: str | None = Field(default=None, description="YYYY-MM-DD for date-specific overrides")
    is_closed: bool | None = None
    reason: str = Field(min_length=3, max_length=500, description="Business justification for the requested change")


class BrandChangeRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brand_id: UUID
    brand_name: str | None = None
    brand_process_id: UUID | None = None
    process_name: str | None = None
    requested_by_user_id: UUID
    requested_by_email: str | None = None
    request_type: str
    current_configuration: str
    requested_configuration: str
    status: str
    review_notes: str | None = None
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    implemented_roster_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class BrandImpactPreview(BaseModel):
    request_id: UUID
    brand_id: UUID
    brand_name: str
    request_type: str
    affected_dates: list[str]
    affected_processes: list[str]
    old_requirement: str
    new_requirement: str
    affected_employees_count: int
    affected_employees: list[dict]
    invalid_existing_allocations_count: int
    new_uncovered_intervals_count: int
    affected_draft_rosters: list[dict]
    summary: str


class BrandReviewActionRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)
    manager_notes: str | None = Field(default=None, max_length=1000)
