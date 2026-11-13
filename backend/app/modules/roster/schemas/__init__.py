from __future__ import annotations

from datetime import date, datetime, time
import uuid

from pydantic import BaseModel, Field

from app.modules.roster.models import (
    AllocationType,
    ConflictSeverity,
    ConflictType,
    RosterStatus,
)


class RosterGenerateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020, le=2100)


class RosterSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    month: int
    year: int
    version: int
    parent_roster_id: uuid.UUID | None
    status: RosterStatus
    config_hash: str | None
    created_by: str
    created_at: datetime
    published_at: datetime | None
    total_shifts: int = 0
    total_allocations: int = 0
    total_conflicts: int = 0
    hard_violations_count: int = 0
    soft_warnings_count: int = 0


class RosterConflictResponse(BaseModel):
    id: uuid.UUID
    date: date
    brand_process_id: uuid.UUID | None
    employee_id: uuid.UUID | None
    start_time: time | None
    end_time: time | None
    severity: ConflictSeverity
    conflict_type: ConflictType
    description: str
    is_resolved: bool
    brand_name: str | None = None
    process_name: str | None = None
    required_skill: str | None = None
    pod_name: str | None = None
    pod_id: uuid.UUID | None = None


class AllocationCell(BaseModel):
    allocation_id: uuid.UUID
    brand_process_id: uuid.UUID
    brand_id: uuid.UUID
    brand_name: str
    process_id: uuid.UUID
    process_name: str
    employee_id: uuid.UUID
    employee_name: str
    start_time: str
    end_time: str
    allocation_type: AllocationType
    reassigned_from_employee_id: uuid.UUID | None
    is_cross_pod_approved: bool


class DayCell(BaseModel):
    date: str
    day_of_week: int  # 0=Mon...6=Sun
    is_working: bool
    shift_start: str | None = None
    shift_end: str | None = None
    allocations: list[AllocationCell] = []
    conflicts: list[str] = []


class GridRow(BaseModel):
    row_id: str
    row_type: str  # "EMPLOYEE", "POD", "BRAND", "PROCESS"
    title: str
    subtitle: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    days: dict[str, DayCell]  # date string YYYY-MM-DD -> DayCell


class RosterGridViewResponse(BaseModel):
    roster_id: uuid.UUID
    month: int
    year: int
    version: int
    status: RosterStatus
    view_type: str
    dates: list[str]
    rows: list[GridRow]
    summary_conflicts: list[RosterConflictResponse]


class ReassignPreviewRequest(BaseModel):
    date: date
    brand_process_id: uuid.UUID
    start_time: time
    end_time: time
    target_employee_id: uuid.UUID
    source_employee_id: uuid.UUID | None = None


class ReassignPreviewResponse(BaseModel):
    is_eligible: bool
    rejection_reason: str | None = None
    allocation_type: AllocationType
    requires_ops_manager_approval: bool
    affected_conflicts_count: int


class ReassignApplyRequest(BaseModel):
    date: date
    brand_process_id: uuid.UUID
    start_time: time
    end_time: time
    target_employee_id: uuid.UUID
    source_employee_id: uuid.UUID | None = None
    reason: str | None = None
    confirm_cross_pod_approval: bool = False


class BackupCandidateResponse(BaseModel):
    employee_id: uuid.UUID
    name: str
    pod_id: uuid.UUID | None
    pod_name: str | None
    is_same_pod: bool
    requires_approval: bool
    prefers_off_on_day: bool


class AllocationLogItem(BaseModel):
    id: uuid.UUID
    roster_id: uuid.UUID
    date: date
    start_time: str
    end_time: str
    brand_id: uuid.UUID
    brand_name: str
    process_id: uuid.UUID
    process_name: str
    employee_id: uuid.UUID
    employee_name: str
    employee_pod_name: str | None = None
    allocation_type: AllocationType
    reassigned_from_employee_id: uuid.UUID | None = None
    reassigned_from_employee_name: str | None = None
    reassignment_reason: str | None = None
    is_cross_pod_approved: bool = False
    approved_by_user_id: uuid.UUID | None = None
    approved_by_email: str | None = None
    approved_at: datetime | None = None
    created_at: datetime


class PodAnalytics(BaseModel):
    pod_id: uuid.UUID
    pod_name: str
    lead_name: str
    employee_count: int
    available_capacity_hours: float
    scheduled_hours: float
    utilization_pct: float
    status: str  # "DEFICIT" | "BALANCED" | "SURPLUS"
    net_hours_gap: float
    employees_needed: int
    free_employees_count: int
    skills_summary: list[str]


class WorkforceAnalyticsResponse(BaseModel):
    roster_id: uuid.UUID
    month: int
    year: int
    status: str
    total_demand_slots: int
    total_demand_hours: float
    scheduled_allocations: int
    scheduled_hours: float
    demand_coverage_pct: float
    total_employees: int
    total_capacity_hours: float
    workforce_utilization_pct: float
    hard_conflicts_count: int
    pods: list[PodAnalytics]
    recommendations: list[str]


class ResolverBundleResponse(BaseModel):
    bundle_id: uuid.UUID
    requires_cross_pod_approval: bool
    explanation: str
    affected_dates: list[date]
    changes: list[dict]
    affected_conflicts_count: int


class ResolverShortageResponse(BaseModel):
    demand_slot_id: uuid.UUID
    date: date
    brand_name: str
    process_name: str
    start_time: str
    end_time: str
    primary_employee_names: list[str]
    root_cause: str
    explanation: str


class ResolverPreviewResponse(BaseModel):
    roster_id: uuid.UUID
    target_roster_id: uuid.UUID
    is_published: bool
    requires_child_revision: bool
    status: str
    initial_conflicts_count: int
    resolvable_conflicts_count: int
    unresolvable_conflicts_count: int
    coverage_before_pct: float
    coverage_after_pct: float
    automatically_resolvable_bundles: list[ResolverBundleResponse]
    pending_approval_bundles: list[ResolverBundleResponse]
    unresolvable_shortages: list[ResolverShortageResponse]
    passes: list[dict]
    validation_passed: bool
    validation_conflicts: list[dict]


class ResolverApplyRequest(BaseModel):
    roster_id: uuid.UUID
    approve_cross_pod: bool = False
    approved_bundle_ids: list[uuid.UUID] | None = None
    create_child_if_published: bool = True
    idempotency_token: str | None = None


class ResolverApplyResponse(BaseModel):
    status: str
    roster_id: uuid.UUID
    version: int
    is_new_version: bool
    applied_bundles_count: int
    applied_changes_count: int
    resolved_conflicts_count: int
    remaining_conflicts_count: int
    coverage_pct: float
    validation_passed: bool
    validation_conflicts_count: int
    applied_at: datetime



