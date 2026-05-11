"""dashboard widget execution status

Revision ID: 20260430_0013
Revises: 20260430_0012
Create Date: 2026-04-30 13:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0013"
down_revision: str | None = "20260430_0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("execution_status", sa.String(length=20), nullable=False, server_default="never_run"),
    )


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "execution_status")
