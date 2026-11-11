from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
import uuid


class HolidayBehavior(str, Enum):
    CLOSED = "CLOSED"
    NORMAL = "NORMAL"
    REDUCED = "REDUCED"


class ConflictSeverity(str, Enum):
    HARD_VIOLATION = "HARD_VIOLATION"
    SOFT_WARNING = "SOFT_WARNING"


class ConflictType(str, Enum):
    UNCOVERED_SLOT = "UNCOVERED_SLOT"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    DOUBLE_BOOKING = "DOUBLE_BOOKING"
    UNAVAILABLE_ALLOCATION = "UNAVAILABLE_ALLOCATION"
    SHIFT_BOUND_EXCEEDED = "SHIFT_BOUND_EXCEEDED"
    SKILL_MISMATCH = "SKILL_MISMATCH"
    INVALID_SHIFT = "INVALID_SHIFT"
    CROSS_POD_UNAPPROVED = "CROSS_POD_UNAPPROVED"
    DAILY_CAPACITY_EXCEEDED = "DAILY_CAPACITY_EXCEEDED"


class AllocationType(str, Enum):
    PRIMARY = "PRIMARY"
    SAME_POD_REASSIGNMENT = "SAME_POD_REASSIGNMENT"
    CROSS_POD_REASSIGNMENT = "CROSS_POD_REASSIGNMENT"


@dataclass(frozen=True)
class TimeInterval:
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        if self.start_time >= self.end_time:
            raise ValueError(
                f"Invalid time interval: start_time ({self.start_time}) must be strictly earlier than end_time ({self.end_time})"
            )

    @property
    def duration_minutes(self) -> int:
        return (
            (self.end_time.hour * 60 + self.end_time.minute)
            - (self.start_time.hour * 60 + self.start_time.minute)
        )

    def overlaps(self, other: TimeInterval) -> bool:
        """True if intervals overlap by at least 1 minute (touching endpoints do not overlap)."""
        return max(self.start_time, other.start_time) < min(self.end_time, other.end_time)

    def contains(self, other: TimeInterval) -> bool:
        """True if self completely covers other."""
        return self.start_time <= other.start_time and self.end_time >= other.end_time


@dataclass(frozen=True)
class OperatingPatternSpec:
    brand_process_id: uuid.UUID
    operating_days: tuple[int, ...]  # 0=Mon, ..., 6=Sun
    start_time: time
    end_time: time
    min_staffing_weekday: int
    min_staffing_weekend: int
    holiday_behavior: HolidayBehavior = HolidayBehavior.NORMAL
    min_staffing_holiday: int = 0


@dataclass(frozen=True)
class OperatingOverrideSpec:
    brand_process_id: uuid.UUID
    date: date
    is_closed: bool
    override_start_time: time | None = None
    override_end_time: time | None = None
    override_min_staffing: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class DemandSlot:
    """Resolved demand for a single brand-process on a specific date."""
    brand_process_id: uuid.UUID
    brand_id: uuid.UUID
    process_id: uuid.UUID
    date: date
    interval: TimeInterval
    required_staff: int
    is_operating: bool
    resolution_source: str  # e.g. "OVERRIDE", "WEEKDAY_RULE", "HOLIDAY_BEHAVIOR", "NON_OPERATING_DAY"


@dataclass(frozen=True)
class EmployeeSpec:
    id: uuid.UUID
    name: str
    email: str
    pod_id: uuid.UUID | None
    daily_capacity_minutes: int
    standard_start_time: time
    standard_end_time: time
    skill_process_ids: frozenset[uuid.UUID]
    is_active: bool = True


@dataclass(frozen=True)
class UnavailabilitySpec:
    employee_id: uuid.UUID
    date: date
    reason_type: str
    is_approved: bool = True


@dataclass(frozen=True)
class PreferenceSpec:
    employee_id: uuid.UUID
    preferred_weekly_off_days: tuple[int, ...]  # 0=Mon...6=Sun


@dataclass(frozen=True)
class PrimaryAssignmentSpec:
    employee_id: uuid.UUID
    brand_process_id: uuid.UUID
    priority: int = 1
    effective_from: date = date.min
    effective_to: date | None = None


@dataclass
class ScheduledAllocation:
    id: uuid.UUID
    employee_id: uuid.UUID
    brand_process_id: uuid.UUID
    date: date
    interval: TimeInterval
    allocation_type: AllocationType = AllocationType.PRIMARY
    reassigned_from_employee_id: uuid.UUID | None = None
    is_cross_pod_approved: bool = False
    approved_by_user_id: uuid.UUID | None = None
    notes: str | None = None


@dataclass
class ScheduledShift:
    id: uuid.UUID
    employee_id: uuid.UUID
    date: date
    interval: TimeInterval
    is_working_day: bool = True


@dataclass(frozen=True)
class CrossPodCandidate:
    employee_id: uuid.UUID
    employee_name: str
    pod_id: uuid.UUID | None
    brand_process_id: uuid.UUID
    date: date
    interval: TimeInterval
    prefers_off_on_day: bool


@dataclass(frozen=True)
class ValidationConflict:
    conflict_type: ConflictType
    severity: ConflictSeverity
    date: date
    description: str
    brand_process_id: uuid.UUID | None = None
    employee_id: uuid.UUID | None = None
    interval: TimeInterval | None = None


@dataclass
class RosterScheduleResult:
    shifts: list[ScheduledShift] = field(default_factory=list)
    allocations: list[ScheduledAllocation] = field(default_factory=list)
    conflicts: list[ValidationConflict] = field(default_factory=list)
    uncovered_demand: list[DemandSlot] = field(default_factory=list)
    cross_pod_candidates: list[CrossPodCandidate] = field(default_factory=list)
