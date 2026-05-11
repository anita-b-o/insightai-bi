"""dataset sql storage

Revision ID: 20260427_0002
Revises: 20260427_0001
Create Date: 2026-04-27 22:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260427_0002"
down_revision: str | None = "20260427_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("table_name", sa.String(length=255), nullable=True))
    op.add_column("dataset_columns", sa.Column("sql_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("dataset_columns", "sql_name")
    op.drop_column("datasets", "table_name")
