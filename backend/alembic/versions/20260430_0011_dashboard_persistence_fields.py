"""dashboard persistence fields

Revision ID: 20260430_0011
Revises: 20260429_0010
Create Date: 2026-04-30 11:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260430_0011"
down_revision: str | None = "20260429_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dashboards", sa.Column("dataset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_dashboards_dataset_id"), "dashboards", ["dataset_id"], unique=False)
    op.create_foreign_key(
        "fk_dashboards_dataset_id_datasets",
        "dashboards",
        "datasets",
        ["dataset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("dashboard_widgets", "source_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("dashboard_widgets", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("dashboard_widgets", sa.Column("chart_type", sa.String(length=20), nullable=True))
    op.add_column(
        "dashboard_widgets",
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "dashboard_widgets",
        sa.Column("data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dashboard_widgets", "data_json")
    op.drop_column("dashboard_widgets", "config_json")
    op.drop_column("dashboard_widgets", "chart_type")
    op.drop_column("dashboard_widgets", "title")
    op.alter_column("dashboard_widgets", "source_id", existing_type=sa.Integer(), nullable=False)

    op.drop_constraint("fk_dashboards_dataset_id_datasets", "dashboards", type_="foreignkey")
    op.drop_index(op.f("ix_dashboards_dataset_id"), table_name="dashboards")
    op.drop_column("dashboards", "dataset_id")
