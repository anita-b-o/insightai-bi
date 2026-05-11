"""dashboard widget snapshots

Revision ID: 20260429_0010
Revises: 20260429_0009
Create Date: 2026-04-29 20:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260429_0010"
down_revision: str | None = "20260429_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("snapshot_created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "snapshot_created_at")
    op.drop_column("dashboard_widgets", "snapshot_json")
