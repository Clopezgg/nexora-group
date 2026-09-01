"""project lifecycle timestamps + archived

Revision ID: 3696ba8e621d
Revises: 72aed748da19
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3696ba8e621d"
down_revision: Union[str, None] = "72aed748da19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("completed_at", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("closed_at", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("reopened_at", sa.Date(), nullable=True))
    op.add_column("projects", sa.Column("archived_at", sa.Date(), nullable=True))
    op.add_column(
        "projects", sa.Column("status_before_archive", sa.String(length=32), nullable=True)
    )
    # Backfill: proyectos ya COMPLETED/CLOSED heredan actual_end como marca.
    op.execute(
        "UPDATE projects SET completed_at = actual_end "
        "WHERE status IN ('COMPLETED', 'CLOSED') AND completed_at IS NULL "
        "AND actual_end IS NOT NULL"
    )
    op.execute(
        "UPDATE projects SET closed_at = actual_end "
        "WHERE status = 'CLOSED' AND closed_at IS NULL AND actual_end IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("projects", "status_before_archive")
    op.drop_column("projects", "archived_at")
    op.drop_column("projects", "reopened_at")
    op.drop_column("projects", "closed_at")
    op.drop_column("projects", "completed_at")
