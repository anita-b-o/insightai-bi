"""add worker statuses table

Revision ID: 20260511_0018
Revises: 20260509_0017
Create Date: 2026-05-11 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260511_0018"
down_revision: str | None = "20260509_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worker_statuses",
        sa.Column("worker_name", sa.String(length=100), nullable=False),
        sa.Column("last_worker_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_worker_cycle_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_worker_error", sa.String(length=500), nullable=True),
        sa.Column("last_worker_processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("worker_name"),
    )


def downgrade() -> None:
    op.drop_table("worker_statuses")
