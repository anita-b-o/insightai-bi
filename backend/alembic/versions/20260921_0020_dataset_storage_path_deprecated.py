"""deprecate persistent CSV storage paths

Revision ID: 20260921_0020
Revises: 20260921_0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260921_0020"
down_revision: str | None = "20260921_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("datasets", "storage_path", existing_type=sa.String(length=500), nullable=True)


def downgrade() -> None:
    # Existing NULLs deliberately prevent a safe rollback to NOT NULL.
    op.execute("UPDATE datasets SET storage_path = '' WHERE storage_path IS NULL")
    op.alter_column("datasets", "storage_path", existing_type=sa.String(length=500), nullable=False)
