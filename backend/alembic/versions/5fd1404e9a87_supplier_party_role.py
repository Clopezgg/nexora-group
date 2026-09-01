"""supplier party_role

Revision ID: 5fd1404e9a87
Revises: 3696ba8e621d
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5fd1404e9a87"
down_revision: Union[str, None] = "3696ba8e621d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column(
            "party_role",
            sa.String(length=16),
            nullable=False,
            server_default="SUPPLIER",
        ),
    )
    op.create_check_constraint(
        "ck_suppliers_party_role",
        "suppliers",
        "party_role IN ('SUPPLIER', 'CONTRACTOR', 'BOTH')",
    )
    op.create_check_constraint(
        "ck_suppliers_status",
        "suppliers",
        "status IN ('ACTIVE', 'INACTIVE', 'BLOCKED', 'ARCHIVED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_suppliers_status", "suppliers", type_="check")
    op.drop_constraint("ck_suppliers_party_role", "suppliers", type_="check")
    op.drop_column("suppliers", "party_role")
