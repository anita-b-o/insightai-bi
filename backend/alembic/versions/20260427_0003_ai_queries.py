"""ai queries

Revision ID: 20260427_0003
Revises: 20260427_0002
Create Date: 2026-04-27 23:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260427_0003"
down_revision: str | None = "20260427_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_queries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_normalized", sa.String(length=4000), nullable=False),
        sa.Column("sql", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("chart_suggestion", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_queries_dataset_id"), "ai_queries", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_ai_queries_question_normalized"), "ai_queries", ["question_normalized"], unique=False)
    op.create_index(op.f("ix_ai_queries_user_id"), "ai_queries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_queries_user_id"), table_name="ai_queries")
    op.drop_index(op.f("ix_ai_queries_question_normalized"), table_name="ai_queries")
    op.drop_index(op.f("ix_ai_queries_dataset_id"), table_name="ai_queries")
    op.drop_table("ai_queries")
