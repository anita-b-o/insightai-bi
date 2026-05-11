"""dataset insight runs

Revision ID: 20260429_0008
Revises: 20260429_0007
Create Date: 2026-04-29 18:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260429_0008"
down_revision: str | None = "20260429_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "dataset_insight_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("insights_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("dataset_updated_at_snapshot", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dataset_insight_runs_dataset_id"), "dataset_insight_runs", ["dataset_id"], unique=False)
    op.create_index(op.f("ix_dataset_insight_runs_generated_at"), "dataset_insight_runs", ["generated_at"], unique=False)
    op.create_index(op.f("ix_dataset_insight_runs_user_id"), "dataset_insight_runs", ["user_id"], unique=False)
    op.execute(
        "CREATE INDEX ix_dataset_insight_runs_dataset_generated_at_desc "
        "ON dataset_insight_runs (dataset_id, generated_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_dataset_insight_runs_user_generated_at_desc "
        "ON dataset_insight_runs (user_id, generated_at DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_insight_runs_user_generated_at_desc", table_name="dataset_insight_runs")
    op.drop_index("ix_dataset_insight_runs_dataset_generated_at_desc", table_name="dataset_insight_runs")
    op.drop_index(op.f("ix_dataset_insight_runs_user_id"), table_name="dataset_insight_runs")
    op.drop_index(op.f("ix_dataset_insight_runs_generated_at"), table_name="dataset_insight_runs")
    op.drop_index(op.f("ix_dataset_insight_runs_dataset_id"), table_name="dataset_insight_runs")
    op.drop_table("dataset_insight_runs")
    op.drop_column("datasets", "updated_at")
