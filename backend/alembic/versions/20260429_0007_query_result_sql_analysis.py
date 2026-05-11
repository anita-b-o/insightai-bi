"""query result sql analysis

Revision ID: 20260429_0007
Revises: 20260428_0006
Create Date: 2026-04-29 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260429_0007"
down_revision: str | None = "20260428_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_results", sa.Column("sql_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("query_results", "sql_analysis")
