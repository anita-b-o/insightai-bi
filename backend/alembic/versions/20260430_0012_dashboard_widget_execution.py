"""dashboard widget execution

Revision ID: 20260430_0012
Revises: 20260430_0011
Create Date: 2026-04-30 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0012"
down_revision: str | None = "20260430_0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("execution_type", sa.String(length=20), nullable=False, server_default="snapshot"),
    )
    op.add_column("dashboard_widgets", sa.Column("query_sql", sa.Text(), nullable=True))
    op.add_column("dashboard_widgets", sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("dashboard_widgets", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "error_message")
    op.drop_column("dashboard_widgets", "last_run_at")
    op.drop_column("dashboard_widgets", "query_sql")
    op.drop_column("dashboard_widgets", "execution_type")
