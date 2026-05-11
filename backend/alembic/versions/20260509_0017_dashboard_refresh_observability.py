"""dashboard refresh observability metadata

Revision ID: 20260509_0017
Revises: 20260430_0016
Create Date: 2026-05-09 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260509_0017"
down_revision: str | None = "20260430_0016"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dashboards", sa.Column("refresh_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dashboards", sa.Column("refresh_finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dashboards", sa.Column("refresh_lock_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dashboards", sa.Column("last_refresh_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dashboards", sa.Column("last_refresh_error", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("dashboards", "last_refresh_error")
    op.drop_column("dashboards", "last_refresh_attempt_at")
    op.drop_column("dashboards", "refresh_lock_expires_at")
    op.drop_column("dashboards", "refresh_finished_at")
    op.drop_column("dashboards", "refresh_started_at")
