"""add configurable automatic resource posting

Revision ID: e84c6d20a9f1
Revises: d93f2a7c1b44
Create Date: 2026-08-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e84c6d20a9f1"
down_revision: Union[str, None] = "d93f2a7c1b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_posting_configs",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("expense_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offset_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("source_type IN ('FUEL','MAINTENANCE','LABOR')", name="ck_resource_posting_source_valid"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expense_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["offset_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "source_type", name="uq_resource_posting_company_source"),
    )
    op.create_index(op.f("ix_resource_posting_configs_company_id"), "resource_posting_configs", ["company_id"], unique=False)
    document_types = sa.table(
        "document_types",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("number_prefix", sa.String),
    )
    op.bulk_insert(
        document_types,
        [
            {"code": "FUE", "name": "Costo de combustible", "number_prefix": "FUE"},
            {"code": "MNT", "name": "Costo de mantenimiento", "number_prefix": "MNT"},
            {"code": "LAB", "name": "Costo de mano de obra aprobada", "number_prefix": "LAB"},
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE code IN ('FUE','MNT','LAB')")
    op.drop_index(op.f("ix_resource_posting_configs_company_id"), table_name="resource_posting_configs")
    op.drop_table("resource_posting_configs")
