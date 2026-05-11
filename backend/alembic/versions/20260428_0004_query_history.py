"""query history

Revision ID: 20260428_0004
Revises: 20260427_0003
Create Date: 2026-04-28 00:45:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260428_0004"
down_revision: str | None = "20260427_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "query_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_query_history_dataset_id"), "query_history", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_query_history_user_id"), "query_history", ["user_id"], unique=False)

    op.create_table(
        "query_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("query_id", sa.Integer(), nullable=False),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["query_id"], ["query_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_query_results_query_id"), "query_results", ["query_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_query_results_query_id"), table_name="query_results")
    op.drop_table("query_results")
    op.drop_index(op.f("ix_query_history_user_id"), table_name="query_history")
    op.drop_index(op.f("ix_query_history_dataset_id"), table_name="query_history")
    op.drop_table("query_history")
