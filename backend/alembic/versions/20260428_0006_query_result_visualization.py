"""query result visualization

Revision ID: 20260428_0006
Revises: 20260428_0005
Create Date: 2026-04-28 03:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260428_0006"
down_revision: str | None = "20260428_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_results", sa.Column("visualization_suggestion", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("query_results", sa.Column("visualization_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_results", "visualization_reason")
    op.drop_column("query_results", "visualization_suggestion")
