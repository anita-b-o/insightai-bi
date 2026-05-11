"""dashboard share links

Revision ID: 20260430_0016
Revises: 20260430_0015
Create Date: 2026-05-01 00:25:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260430_0016"
down_revision: str | None = "20260430_0015"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_share_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dashboard_share_links_created_by_user_id"), "dashboard_share_links", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_dashboard_share_links_dashboard_id"), "dashboard_share_links", ["dashboard_id"], unique=False)
    op.create_index(op.f("ix_dashboard_share_links_token_hash"), "dashboard_share_links", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_dashboard_share_links_token_hash"), table_name="dashboard_share_links")
    op.drop_index(op.f("ix_dashboard_share_links_dashboard_id"), table_name="dashboard_share_links")
    op.drop_index(op.f("ix_dashboard_share_links_created_by_user_id"), table_name="dashboard_share_links")
    op.drop_table("dashboard_share_links")
