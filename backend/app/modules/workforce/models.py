from __future__ import annotations

import enum
import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SkillProficiency(str, enum.Enum):
    BASIC = "BASIC"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class Pod(Base):
    __tablename__ = "pods"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employees: Mapped[list[Employee]] = relationship(back_populates="pod")
    lead: Mapped[PodLead | None] = relationship(
        back_populates="pod", cascade="all, delete-orphan", uselist=False
    )


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "daily_capacity_minutes > 0 AND daily_capacity_minutes <= 1440",
            name="ck_employee_capacity",
        ),
        CheckConstraint(
            "standard_end_time > standard_start_time",
            name="ck_employee_same_day_shift",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    pod_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pods.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, native_enum=False, length=20),
        default=EmployeeStatus.ACTIVE,
        index=True,
    )
    daily_capacity_minutes: Mapped[int] = mapped_column(Integer, default=480)
    standard_start_time: Mapped[time] = mapped_column(Time)
    standard_end_time: Mapped[time] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pod: Mapped[Pod | None] = relationship(back_populates="employees")
    led_pod: Mapped[PodLead | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )
    process_skills: Mapped[list[EmployeeProcessSkill]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )


class PodLead(Base):
    __tablename__ = "pod_leads"

    pod_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pods.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), unique=True, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pod: Mapped[Pod] = relationship(back_populates="lead")
    employee: Mapped[Employee] = relationship(back_populates="led_pod")


class EmployeeProcessSkill(Base):
    __tablename__ = "employee_process_skills"
    __table_args__ = (UniqueConstraint("employee_id", "process_id", name="uq_employee_process_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processes.id", ondelete="CASCADE"), index=True
    )
    proficiency: Mapped[SkillProficiency] = mapped_column(
        Enum(SkillProficiency, native_enum=False, length=20)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship(back_populates="process_skills")

