"""scope global search by explicit project access

Revision ID: c8a9e1f2b3d4
Revises: a26d4f8b91c3
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c8a9e1f2b3d4"
down_revision: str | None = "a26d4f8b91c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE role_permissions AS rp
        SET project_scope = CASE
            WHEN rp.company_scope = 'ANY' THEN 'ANY'
            ELSE 'OWN'
        END
        FROM permissions AS p
        WHERE p.id = rp.permission_id
          AND p.resource = 'search.global'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE role_permissions AS rp
        SET project_scope = 'NONE'
        FROM permissions AS p
        WHERE p.id = rp.permission_id
          AND p.resource = 'search.global'
        """
    )
