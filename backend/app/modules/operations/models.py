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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RecordStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class HolidayBehavior(str, enum.Enum):
    CLOSED = "CLOSED"
    NORMAL = "NORMAL"
    REDUCED = "REDUCED"


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, length=20), default=RecordStatus.ACTIVE, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    brand_processes: Mapped[list[BrandProcess]] = relationship(back_populates="brand")


class Process(Base):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, native_enum=False, length=20), default=RecordStatus.ACTIVE, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    brand_processes: Mapped[list[BrandProcess]] = relationship(back_populates="process")


class HolidayCalendar(Base):
    __tablename__ = "holiday_calendars"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    region: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    holidays: Mapped[list[Holiday]] = relationship(back_populates="calendar", cascade="all, delete-orphan")


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("holiday_calendar_id", "date", name="uq_holiday_calendar_date"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    holiday_calendar_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("holiday_calendars.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str] = mapped_column(String(160))

    calendar: Mapped[HolidayCalendar] = relationship(back_populates="holidays")


class BrandProcess(Base):
    __tablename__ = "brand_processes"
    __table_args__ = (
        UniqueConstraint("brand_id", "process_id", name="uq_brand_process"),
        CheckConstraint(
            "holiday_min_employees IS NULL OR holiday_min_employees >= 0",
            name="ck_brand_process_holiday_min_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="RESTRICT"), index=True
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processes.id", ondelete="RESTRICT"), index=True
    )
    holiday_calendar_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("holiday_calendars.id", ondelete="SET NULL"), index=True
    )
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    holiday_behavior: Mapped[HolidayBehavior] = mapped_column(
        Enum(HolidayBehavior, native_enum=False, length=20), default=HolidayBehavior.NORMAL
    )
    holiday_min_employees: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    brand: Mapped[Brand] = relationship(back_populates="brand_processes")
    process: Mapped[Process] = relationship(back_populates="brand_processes")
    holiday_calendar: Mapped[HolidayCalendar | None] = relationship()
    assignments: Mapped[list[PrimaryAssignment]] = relationship(back_populates="brand_process")


class PrimaryAssignment(Base):
    __tablename__ = "primary_assignments"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "brand_process_id",
            "effective_from",
            name="uq_primary_assignment_effective_start",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_primary_assignment_date_range",
        ),
        CheckConstraint("priority >= 1", name="ck_primary_assignment_priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    brand_process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_processes.id", ondelete="RESTRICT"), index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    brand_process: Mapped[BrandProcess] = relationship(back_populates="assignments")

