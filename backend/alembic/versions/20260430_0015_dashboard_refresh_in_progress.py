"""dashboard refresh in progress

Revision ID: 20260430_0015
Revises: 20260430_0014
Create Date: 2026-04-30 23:58:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0015"
down_revision: str | None = "20260430_0014"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboards",
        sa.Column("refresh_in_progress", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("dashboards", "refresh_in_progress")
