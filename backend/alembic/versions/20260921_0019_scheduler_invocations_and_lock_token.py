"""add scheduler invocations and refresh lock ownership

Revision ID: 20260921_0019
Revises: 20260511_0018
Create Date: 2026-09-21 11:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_0019"
down_revision: str | None = "20260511_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dashboards", sa.Column("refresh_lock_token", sa.String(length=128), nullable=True))
    op.create_table(
        "scheduler_invocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invocation_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invocation_id"),
    )
    op.create_index("ix_scheduler_invocations_invocation_id", "scheduler_invocations", ["invocation_id"])


def downgrade() -> None:
    op.drop_index("ix_scheduler_invocations_invocation_id", table_name="scheduler_invocations")
    op.drop_table("scheduler_invocations")
    op.drop_column("dashboards", "refresh_lock_token")
