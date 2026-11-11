from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AbsenceReasonType(str, enum.Enum):
    PLANNED_LEAVE = "PLANNED_LEAVE"
    SICK_LEAVE = "SICK_LEAVE"
    APPROVED_OFF = "APPROVED_OFF"
    COMP_OFF = "COMP_OFF"
    TRAINING = "TRAINING"


class EmployeeUnavailability(Base):
    __tablename__ = "employee_unavailability"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_employee_unavailability_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    reason_type: Mapped[AbsenceReasonType] = mapped_column(
        Enum(AbsenceReasonType, native_enum=False, length=40),
        default=AbsenceReasonType.PLANNED_LEAVE,
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    notes: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmployeePreference(Base):
    __tablename__ = "employee_preferences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Stored as comma-separated days, e.g. "0,6" (0=Mon...6=Sun) for database portability
    preferred_weekly_off_days: Mapped[str] = mapped_column(String(30), default="0,6")
    notes: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

