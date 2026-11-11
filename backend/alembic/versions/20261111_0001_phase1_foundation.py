"""Phase 1 foundation schema.

Revision ID: 20261111_0001
Revises:
Create Date: 2026-11-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261111_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("ADMIN", "OPERATIONS_MANAGER", name="userrole", native_enum=False, length=40)
employee_status = sa.Enum("ACTIVE", "INACTIVE", name="employeestatus", native_enum=False, length=20)
record_status = sa.Enum("ACTIVE", "INACTIVE", name="recordstatus", native_enum=False, length=20)
skill_proficiency = sa.Enum(
    "BASIC", "INTERMEDIATE", "ADVANCED", name="skillproficiency", native_enum=False, length=20
)
holiday_behavior = sa.Enum(
    "CLOSED", "NORMAL", "REDUCED", name="holidaybehavior", native_enum=False, length=20
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "pods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_brands_code", "brands", ["code"], unique=True)
    op.create_index("ix_brands_status", "brands", ["status"])

    op.create_table(
        "processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("status", record_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_processes_code", "processes", ["code"], unique=True)
    op.create_index("ix_processes_status", "processes", ["status"])

    op.create_table(
        "holiday_calendars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("region", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("pod_id", sa.Uuid()),
        sa.Column("status", employee_status, nullable=False),
        sa.Column("daily_capacity_minutes", sa.Integer(), nullable=False),
        sa.Column("standard_start_time", sa.Time(), nullable=False),
        sa.Column("standard_end_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pod_id"], ["pods.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("employee_code"),
        sa.CheckConstraint("daily_capacity_minutes > 0 AND daily_capacity_minutes <= 1440", name="ck_employee_capacity"),
        sa.CheckConstraint("standard_end_time > standard_start_time", name="ck_employee_same_day_shift"),
    )
    op.create_index("ix_employees_employee_code", "employees", ["employee_code"], unique=True)
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)
    op.create_index("ix_employees_name", "employees", ["name"])
    op.create_index("ix_employees_pod_id", "employees", ["pod_id"])
    op.create_index("ix_employees_status", "employees", ["status"])

    op.create_table(
        "pod_leads",
        sa.Column("pod_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pod_id"], ["pods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pod_id"),
        sa.UniqueConstraint("employee_id"),
    )
    op.create_index("ix_pod_leads_employee_id", "pod_leads", ["employee_id"], unique=True)

    op.create_table(
        "holidays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("holiday_calendar_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.ForeignKeyConstraint(["holiday_calendar_id"], ["holiday_calendars.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("holiday_calendar_id", "date", name="uq_holiday_calendar_date"),
    )
    op.create_index("ix_holidays_calendar", "holidays", ["holiday_calendar_id"])
    op.create_index("ix_holidays_date", "holidays", ["date"])

    op.create_table(
        "employee_process_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("proficiency", skill_proficiency, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "process_id", name="uq_employee_process_skill"),
    )
    op.create_index("ix_employee_skills_employee", "employee_process_skills", ["employee_id"])
    op.create_index("ix_employee_skills_process", "employee_process_skills", ["process_id"])

    op.create_table(
        "brand_processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("holiday_calendar_id", sa.Uuid()),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("holiday_behavior", holiday_behavior, nullable=False),
        sa.Column("holiday_min_employees", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "holiday_min_employees IS NULL OR holiday_min_employees >= 0",
            name="ck_brand_process_holiday_min_nonnegative",
        ),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["holiday_calendar_id"], ["holiday_calendars.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "process_id", name="uq_brand_process"),
    )
    op.create_index("ix_brand_processes_brand", "brand_processes", ["brand_id"])
    op.create_index("ix_brand_processes_process", "brand_processes", ["process_id"])
    op.create_index("ix_brand_processes_calendar", "brand_processes", ["holiday_calendar_id"])

    op.create_table(
        "primary_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("brand_process_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_primary_assignment_date_range",
        ),
        sa.CheckConstraint("priority >= 1", name="ck_primary_assignment_priority"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["brand_process_id"], ["brand_processes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id", "brand_process_id", "effective_from", name="uq_primary_assignment_effective_start"
        ),
    )
    op.create_index("ix_assignments_employee", "primary_assignments", ["employee_id"])
    op.create_index("ix_assignments_brand_process", "primary_assignments", ["brand_process_id"])
    op.create_index("ix_assignments_effective_from", "primary_assignments", ["effective_from"])
    op.create_index("ix_assignments_effective_to", "primary_assignments", ["effective_to"])


def downgrade() -> None:
    op.drop_table("primary_assignments")
    op.drop_table("brand_processes")
    op.drop_table("employee_process_skills")
    op.drop_table("holidays")
    op.drop_table("pod_leads")
    op.drop_table("employees")
    op.drop_table("holiday_calendars")
    op.drop_table("processes")
    op.drop_table("brands")
    op.drop_table("pods")
    op.drop_table("users")

