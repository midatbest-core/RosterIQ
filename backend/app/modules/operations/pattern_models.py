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
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.operations.models import HolidayBehavior


class OperatingPattern(Base):
    __tablename__ = "operating_patterns"
    __table_args__ = (
        UniqueConstraint("brand_process_id", name="uq_operating_pattern_brand_process"),
        CheckConstraint("end_time > start_time", name="ck_operating_pattern_time_interval"),
        CheckConstraint("min_staffing_weekday >= 0", name="ck_operating_pattern_min_weekday"),
        CheckConstraint("min_staffing_weekend >= 0", name="ck_operating_pattern_min_weekend"),
        CheckConstraint("min_staffing_holiday >= 0", name="ck_operating_pattern_min_holiday"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_processes.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Comma-separated active days of week: 0=Mon, 1=Tue, ..., 6=Sun (e.g. "0,1,2,3,4,5" for Mon-Sat)
    operating_days: Mapped[str] = mapped_column(String(30), default="0,1,2,3,4")
    start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    end_time: Mapped[time] = mapped_column(Time, default=time(18, 0))
    min_staffing_weekday: Mapped[int] = mapped_column(Integer, default=1)
    min_staffing_weekend: Mapped[int] = mapped_column(Integer, default=1)
    holiday_behavior: Mapped[HolidayBehavior] = mapped_column(
        Enum(HolidayBehavior, native_enum=False, length=20), default=HolidayBehavior.NORMAL
    )
    min_staffing_holiday: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OperatingOverride(Base):
    __tablename__ = "operating_overrides"
    __table_args__ = (
        UniqueConstraint("brand_process_id", "date", name="uq_operating_override_bp_date"),
        CheckConstraint(
            "override_end_time IS NULL OR override_start_time IS NULL OR override_end_time > override_start_time",
            name="ck_operating_override_time_interval",
        ),
        CheckConstraint(
            "override_min_staffing IS NULL OR override_min_staffing >= 0",
            name="ck_operating_override_min_staffing",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brand_processes.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    override_start_time: Mapped[time | None] = mapped_column(Time)
    override_end_time: Mapped[time | None] = mapped_column(Time)
    override_min_staffing: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

