"""add explicit user project access and normalize project scopes

Revision ID: a26d4f8b91c3
Revises: f17c9a4e2d81
Create Date: 2026-08-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a26d4f8b91c3"
down_revision: Union[str, None] = "f17c9a4e2d81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROJECT_RESOURCE_SQL = """
(
    p.resource LIKE 'project%'
    OR p.resource LIKE 'document.%'
    OR p.resource LIKE 'construction.%'
    OR p.resource LIKE 'site.%'
    OR p.resource LIKE 'quality.%'
    OR p.resource LIKE 'safety.%'
    OR p.resource LIKE 'equipment.%'
    OR p.resource LIKE 'workforce.%'
    OR p.resource LIKE 'procurement.%'
    OR p.resource LIKE 'inventory.%'
    OR p.resource LIKE 'ap.%'
    OR p.resource LIKE 'ar.%'
)
"""


def upgrade() -> None:
    op.create_table(
        "user_project_access",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "project_id", name="uq_user_project_access_user_project"),
    )
    op.create_index("ix_user_project_access_user_id", "user_project_access", ["user_id"], unique=False)
    op.create_index("ix_user_project_access_project_id", "user_project_access", ["project_id"], unique=False)

    # Preserve existing operational access while moving from company-only to
    # explicit project isolation. Admins can subsequently revoke individual
    # project grants without surprising existing users during deployment.
    op.execute(
        """
        INSERT INTO user_project_access (id, user_id, project_id, created_at, updated_at)
        SELECT md5(uca.user_id::text || ':' || pr.id::text)::uuid,
               uca.user_id,
               pr.id,
               now(),
               now()
        FROM user_company_access AS uca
        JOIN projects AS pr ON pr.company_id = uca.company_id
        ON CONFLICT (user_id, project_id) DO NOTHING
        """
    )

    # project_scope becomes meaningful for every resource that can carry a
    # project context. ANY roles remain global; OWN roles require an explicit
    # UserProjectAccess row whenever a concrete project is involved.
    op.execute(
        f"""
        UPDATE role_permissions AS rp
        SET project_scope = CASE
            WHEN rp.company_scope = 'ANY' THEN 'ANY'
            ELSE 'OWN'
        END
        FROM permissions AS p
        WHERE p.id = rp.permission_id
          AND {_PROJECT_RESOURCE_SQL}
        """
    )


def downgrade() -> None:
    # Restore the historical default semantics before removing assignments.
    op.execute(
        f"""
        UPDATE role_permissions AS rp
        SET project_scope = 'ANY'
        FROM permissions AS p
        WHERE p.id = rp.permission_id
          AND {_PROJECT_RESOURCE_SQL}
        """
    )
    op.drop_index("ix_user_project_access_project_id", table_name="user_project_access")
    op.drop_index("ix_user_project_access_user_id", table_name="user_project_access")
    op.drop_table("user_project_access")
