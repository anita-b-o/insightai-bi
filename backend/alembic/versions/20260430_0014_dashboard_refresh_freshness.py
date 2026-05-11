"""dashboard refresh freshness

Revision ID: 20260430_0014
Revises: 20260430_0013
Create Date: 2026-04-30 23:35:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0014"
down_revision: str | None = "20260430_0013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboards",
        sa.Column("auto_refresh_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "dashboards",
        sa.Column("refresh_interval_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dashboards",
        sa.Column("last_successful_refresh_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dashboards",
        sa.Column("next_refresh_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dashboards",
        sa.Column("freshness_status", sa.String(length=20), nullable=False, server_default="never_refreshed"),
    )


def downgrade() -> None:
    op.drop_column("dashboards", "freshness_status")
    op.drop_column("dashboards", "next_refresh_at")
    op.drop_column("dashboards", "last_successful_refresh_at")
    op.drop_column("dashboards", "refresh_interval_minutes")
    op.drop_column("dashboards", "auto_refresh_enabled")
