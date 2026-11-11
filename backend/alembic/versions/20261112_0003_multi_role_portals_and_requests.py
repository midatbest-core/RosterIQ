"""Add multi-role user associations, brand change requests, employee requests, and notifications.

Revision ID: 20261112_0003
Revises: 20261111_0002
Create Date: 2026-11-12
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261112_0003"
down_revision: str | None = "20261111_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add tenant and employee link columns to users table
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("brand_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("employee_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("pod_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key("fk_users_brand_id", "brands", ["brand_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_users_employee_id", "employees", ["employee_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key("fk_users_pod_id", "pods", ["pod_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_users_brand_id", ["brand_id"])
        batch_op.create_index("ix_users_employee_id", ["employee_id"])
        batch_op.create_index("ix_users_pod_id", ["pod_id"])

    # 2. Brand Change Requests table
    op.create_table(
        "brand_change_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=False),
        sa.Column("brand_process_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("current_configuration", sa.Text(), nullable=False),
        sa.Column("requested_configuration", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), server_default="PENDING", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_roster_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_process_id"], ["brand_processes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["implemented_roster_id"], ["rosters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bcr_brand_id", "brand_change_requests", ["brand_id"])
    op.create_index("ix_bcr_status", "brand_change_requests", ["status"])

    # 3. Employee Availability Requests table
    op.create_table(
        "employee_availability_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason_type", sa.String(40), nullable=False),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), server_default="PENDING", nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_roster_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["implemented_roster_id"], ["rosters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ear_employee_id", "employee_availability_requests", ["employee_id"])
    op.create_index("ix_ear_status", "employee_availability_requests", ["status"])

    # 4. In-App Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("employee_availability_requests")
    op.drop_table("brand_change_requests")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("fk_users_pod_id", type_="foreignkey")
        batch_op.drop_constraint("fk_users_employee_id", type_="foreignkey")
        batch_op.drop_constraint("fk_users_brand_id", type_="foreignkey")
        batch_op.drop_index("ix_users_pod_id")
        batch_op.drop_index("ix_users_employee_id")
        batch_op.drop_index("ix_users_brand_id")
        batch_op.drop_column("pod_id")
        batch_op.drop_column("employee_id")
        batch_op.drop_column("brand_id")

