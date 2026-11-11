from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RosterStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    STALE = "STALE"


class AllocationType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SAME_POD_REASSIGNMENT = "SAME_POD_REASSIGNMENT"
    CROSS_POD_REASSIGNMENT = "CROSS_POD_REASSIGNMENT"


class ConflictSeverity(str, enum.Enum):
    HARD_VIOLATION = "HARD_VIOLATION"
    SOFT_WARNING = "SOFT_WARNING"


class ConflictType(str, enum.Enum):
    UNCOVERED_SLOT = "UNCOVERED_SLOT"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    DOUBLE_BOOKING = "DOUBLE_BOOKING"
    UNAVAILABLE_ALLOCATION = "UNAVAILABLE_ALLOCATION"
    SHIFT_BOUND_EXCEEDED = "SHIFT_BOUND_EXCEEDED"
    SKILL_MISMATCH = "SKILL_MISMATCH"
    CROSS_POD_UNAPPROVED = "CROSS_POD_UNAPPROVED"


class Roster(Base):
    __tablename__ = "rosters"
    __table_args__ = (
        UniqueConstraint("month", "year", "version", name="uq_roster_month_year_version"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_roster_month_range"),
        CheckConstraint("version >= 1", name="ck_roster_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    month: Mapped[int] = mapped_column(Integer, index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_roster_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rosters.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[RosterStatus] = mapped_column(
        Enum(RosterStatus, native_enum=False, length=20),
        default=RosterStatus.DRAFT,
        index=True,
    )
    config_hash: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(160), default="Operations Manager")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shifts: Mapped[list[EmployeeShift]] = relationship(
        back_populates="roster", cascade="all, delete-orphan"
    )
    allocations: Mapped[list[RosterAllocation]] = relationship(
        back_populates="roster", cascade="all, delete-orphan"
    )
    conflicts: Mapped[list[RosterConflict]] = relationship(
        back_populates="roster", cascade="all, delete-orphan"
    )


class EmployeeShift(Base):
    """At most one working shift per employee per date in a roster."""

    __tablename__ = "employee_shifts"
    __table_args__ = (
        UniqueConstraint("roster_id", "employee_id", "date", name="uq_roster_employee_date_shift"),
        CheckConstraint(
            "end_time IS NULL OR start_time IS NULL OR end_time > start_time",
            name="ck_employee_shift_time_interval",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rosters.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    end_time: Mapped[time] = mapped_column(Time, default=time(18, 0))
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roster: Mapped[Roster] = relationship(back_populates="shifts")
    allocations: Mapped[list[RosterAllocation]] = relationship(
        back_populates="shift", cascade="all, delete-orphan"
    )


class RosterAllocation(Base):
    """Process allocations strictly within the employee's shift."""

    __tablename__ = "roster_allocations"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_roster_allocation_time_interval"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rosters.id", ondelete="CASCADE"), index=True
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employee_shifts.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    brand_process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_processes.id", ondelete="RESTRICT"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    allocation_type: Mapped[AllocationType] = mapped_column(
        Enum(AllocationType, native_enum=False, length=40),
        default=AllocationType.PRIMARY,
    )
    reassigned_from_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    reassignment_reason: Mapped[str | None] = mapped_column(String(255))
    is_cross_pod_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roster: Mapped[Roster] = relationship(back_populates="allocations")
    shift: Mapped[EmployeeShift] = relationship(back_populates="allocations")


class RosterConflict(Base):
    """Interval-specific scheduling conflicts detected by the engine."""

    __tablename__ = "roster_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    roster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rosters.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    brand_process_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("brand_processes.id", ondelete="SET NULL"), index=True
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    severity: Mapped[ConflictSeverity] = mapped_column(
        Enum(ConflictSeverity, native_enum=False, length=20),
        default=ConflictSeverity.HARD_VIOLATION,
    )
    conflict_type: Mapped[ConflictType] = mapped_column(
        Enum(ConflictType, native_enum=False, length=40)
    )
    description: Mapped[str] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roster: Mapped[Roster] = relationship(back_populates="conflicts")

