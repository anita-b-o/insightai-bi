"""query history management

Revision ID: 20260428_0005
Revises: 20260428_0004
Create Date: 2026-04-28 02:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_0005"
down_revision: str | None = "20260428_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_history", sa.Column("title", sa.String(length=120), nullable=True))
    op.add_column(
        "query_history",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "query_history",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("query_history", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("query_history", "deleted_at")
    op.drop_column("query_history", "updated_at")
    op.drop_column("query_history", "is_favorite")
    op.drop_column("query_history", "title")
