"""add semantic project update permission

Revision ID: d3e5f7a9b1c2
Revises: c2d4e6f8a0b1
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d3e5f7a9b1c2"
down_revision: Union[str, None] = "c2d4e6f8a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Copy the existing project/create grants so this semantic correction does
    # not broaden or unexpectedly remove access on an upgraded installation.
    op.execute("""
        INSERT INTO permissions (id, resource, action, description)
        SELECT gen_random_uuid(), 'project', 'update',
               'Actualizar datos maestros de proyectos'
        WHERE NOT EXISTS (
            SELECT 1 FROM permissions WHERE resource = 'project' AND action = 'update'
        )
    """)
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, company_scope, project_scope)
        SELECT gen_random_uuid(), create_grant.role_id, update_permission.id,
               create_grant.company_scope, create_grant.project_scope
        FROM role_permissions AS create_grant
        JOIN permissions AS create_permission
          ON create_permission.id = create_grant.permission_id
         AND create_permission.resource = 'project'
         AND create_permission.action = 'create'
        JOIN permissions AS update_permission
          ON update_permission.resource = 'project'
         AND update_permission.action = 'update'
        ON CONFLICT (role_id, permission_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'project' AND action = 'update'
        )
    """)
    op.execute("DELETE FROM permissions WHERE resource = 'project' AND action = 'update'")
