"""Add operating patterns, overrides, availability and roster versioning schema.

Revision ID: 20261111_0002
Revises: 20261111_0001
Create Date: 2026-11-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261111_0002"
down_revision: str | None = "20261111_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

holiday_behavior = sa.Enum(
    "CLOSED", "NORMAL", "REDUCED", name="holidaybehavior", native_enum=False, length=20
)
absence_reason_type = sa.Enum(
    "PLANNED_LEAVE", "SICK_LEAVE", "APPROVED_OFF", "COMP_OFF", "TRAINING",
    name="absencereasontype", native_enum=False, length=40
)
roster_status = sa.Enum(
    "DRAFT", "VALIDATED", "PUBLISHED", "STALE",
    name="rosterstatus", native_enum=False, length=20
)
allocation_type = sa.Enum(
    "PRIMARY", "SAME_POD_REASSIGNMENT", "CROSS_POD_REASSIGNMENT",
    name="allocationtype", native_enum=False, length=40
)
conflict_severity = sa.Enum(
    "HARD_VIOLATION", "SOFT_WARNING",
    name="conflictseverity", native_enum=False, length=20
)
conflict_type = sa.Enum(
    "UNCOVERED_SLOT", "PARTIAL_COVERAGE", "DOUBLE_BOOKING", "UNAVAILABLE_ALLOCATION",
    "SHIFT_BOUND_EXCEEDED", "SKILL_MISMATCH", "CROSS_POD_UNAPPROVED",
    name="conflicttype", native_enum=False, length=40
)


def upgrade() -> None:
    # 1. Operating patterns (recurring weekday schedule per brand_process)
    op.create_table(
        "operating_patterns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_process_id", sa.Uuid(), nullable=False),
        sa.Column("operating_days", sa.String(30), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("min_staffing_weekday", sa.Integer(), nullable=False),
        sa.Column("min_staffing_weekend", sa.Integer(), nullable=False),
        sa.Column("holiday_behavior", holiday_behavior, nullable=False),
        sa.Column("min_staffing_holiday", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("end_time > start_time", name="ck_operating_pattern_time_interval"),
        sa.CheckConstraint("min_staffing_weekday >= 0", name="ck_operating_pattern_min_weekday"),
        sa.CheckConstraint("min_staffing_weekend >= 0", name="ck_operating_pattern_min_weekend"),
        sa.CheckConstraint("min_staffing_holiday >= 0", name="ck_operating_pattern_min_holiday"),
        sa.ForeignKeyConstraint(["brand_process_id"], ["brand_processes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_process_id", name="uq_operating_pattern_brand_process"),
    )
    op.create_index("ix_operating_patterns_brand_process", "operating_patterns", ["brand_process_id"])

    # 2. Operating overrides (date-specific precedence overrides)
    op.create_table(
        "operating_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_process_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.Column("override_start_time", sa.Time()),
        sa.Column("override_end_time", sa.Time()),
        sa.Column("override_min_staffing", sa.Integer()),
        sa.Column("reason", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "override_end_time IS NULL OR override_start_time IS NULL OR override_end_time > override_start_time",
            name="ck_operating_override_time_interval",
        ),
        sa.CheckConstraint(
            "override_min_staffing IS NULL OR override_min_staffing >= 0",
            name="ck_operating_override_min_staffing",
        ),
        sa.ForeignKeyConstraint(["brand_process_id"], ["brand_processes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_process_id", "date", name="uq_operating_override_bp_date"),
    )
    op.create_index("ix_operating_overrides_bp", "operating_overrides", ["brand_process_id"])
    op.create_index("ix_operating_overrides_date", "operating_overrides", ["date"])

    # 3. Employee unavailability (hard absence covering complete shift)
    op.create_table(
        "employee_unavailability",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("reason_type", absence_reason_type, nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("notes", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "date", name="uq_employee_unavailability_date"),
    )
    op.create_index("ix_employee_unavailability_emp", "employee_unavailability", ["employee_id"])
    op.create_index("ix_employee_unavailability_date", "employee_unavailability", ["date"])

    # 4. Employee preferences (soft weekly-off preferences)
    op.create_table(
        "employee_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_weekly_off_days", sa.String(30), nullable=False),
        sa.Column("notes", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id"),
    )
    op.create_index("ix_employee_preferences_emp", "employee_preferences", ["employee_id"])

    # 5. Rosters (immutable versioning tree)
    op.create_table(
        "rosters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parent_roster_id", sa.Uuid()),
        sa.Column("status", roster_status, nullable=False),
        sa.Column("config_hash", sa.String(64)),
        sa.Column("created_by", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("month >= 1 AND month <= 12", name="ck_roster_month_range"),
        sa.CheckConstraint("version >= 1", name="ck_roster_version_positive"),
        sa.ForeignKeyConstraint(["parent_roster_id"], ["rosters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("month", "year", "version", name="uq_roster_month_year_version"),
    )
    op.create_index("ix_rosters_month", "rosters", ["month"])
    op.create_index("ix_rosters_year", "rosters", ["year"])
    op.create_index("ix_rosters_status", "rosters", ["status"])
    op.create_index("ix_rosters_parent", "rosters", ["parent_roster_id"])

    # 6. Employee shifts (max 1 shift per employee per date in a roster)
    op.create_table(
        "employee_shifts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("roster_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_working_day", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "end_time IS NULL OR start_time IS NULL OR end_time > start_time",
            name="ck_employee_shift_time_interval",
        ),
        sa.ForeignKeyConstraint(["roster_id"], ["rosters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roster_id", "employee_id", "date", name="uq_roster_employee_date_shift"),
    )
    op.create_index("ix_employee_shifts_roster", "employee_shifts", ["roster_id"])
    op.create_index("ix_employee_shifts_employee", "employee_shifts", ["employee_id"])
    op.create_index("ix_employee_shifts_date", "employee_shifts", ["date"])

    # 7. Roster allocations (process slices embedded inside employee shifts)
    op.create_table(
        "roster_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("roster_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("brand_process_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("allocation_type", allocation_type, nullable=False),
        sa.Column("reassigned_from_employee_id", sa.Uuid()),
        sa.Column("reassignment_reason", sa.String(255)),
        sa.Column("is_cross_pod_approved", sa.Boolean(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("end_time > start_time", name="ck_roster_allocation_time_interval"),
        sa.ForeignKeyConstraint(["roster_id"], ["rosters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shift_id"], ["employee_shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["brand_process_id"], ["brand_processes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reassigned_from_employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roster_allocations_roster", "roster_allocations", ["roster_id"])
    op.create_index("ix_roster_allocations_shift", "roster_allocations", ["shift_id"])
    op.create_index("ix_roster_allocations_employee", "roster_allocations", ["employee_id"])
    op.create_index("ix_roster_allocations_bp", "roster_allocations", ["brand_process_id"])
    op.create_index("ix_roster_allocations_date", "roster_allocations", ["date"])
    op.create_index("ix_roster_allocations_approved_by", "roster_allocations", ["approved_by_user_id"])

    # 8. Roster conflicts (interval-specific conflict records)
    op.create_table(
        "roster_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("roster_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("brand_process_id", sa.Uuid()),
        sa.Column("employee_id", sa.Uuid()),
        sa.Column("start_time", sa.Time()),
        sa.Column("end_time", sa.Time()),
        sa.Column("severity", conflict_severity, nullable=False),
        sa.Column("conflict_type", conflict_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["roster_id"], ["rosters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_process_id"], ["brand_processes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roster_conflicts_roster", "roster_conflicts", ["roster_id"])
    op.create_index("ix_roster_conflicts_date", "roster_conflicts", ["date"])
    op.create_index("ix_roster_conflicts_bp", "roster_conflicts", ["brand_process_id"])
    op.create_index("ix_roster_conflicts_emp", "roster_conflicts", ["employee_id"])


def downgrade() -> None:
    op.drop_table("roster_conflicts")
    op.drop_table("roster_allocations")
    op.drop_table("employee_shifts")
    op.drop_table("rosters")
    op.drop_table("employee_preferences")
    op.drop_table("employee_unavailability")
    op.drop_table("operating_overrides")
    op.drop_table("operating_patterns")

