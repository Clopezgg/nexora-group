"""index the company audit feed

Revision ID: 9c6d4b2a1e70
Revises: 8f5d2c7e1a44
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9c6d4b2a1e70"
down_revision: Union[str, None] = "8f5d2c7e1a44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_logs_company_created_id",
        "audit_logs",
        ["company_id", sa.text("created_at DESC"), "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_company_created_id", table_name="audit_logs")
