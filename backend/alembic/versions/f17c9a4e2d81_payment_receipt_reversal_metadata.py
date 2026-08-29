"""persist AP/AR payment and receipt reversal metadata

Revision ID: f17c9a4e2d81
Revises: e84c6d20a9f1
Create Date: 2026-08-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f17c9a4e2d81"
down_revision: Union[str, None] = "e84c6d20a9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_reversal_columns(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column("reversal_accounting_document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(table_name, sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        table_name,
        sa.Column("reversed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(table_name, sa.Column("reversal_reason", sa.String(length=500), nullable=True))
    op.create_foreign_key(
        f"fk_{table_name}_reversal_accounting_document_id_accounting_documents",
        table_name,
        "accounting_documents",
        ["reversal_accounting_document_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        f"fk_{table_name}_reversed_by_user_id_users",
        table_name,
        "users",
        ["reversed_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def _drop_reversal_columns(table_name: str) -> None:
    op.drop_constraint(
        f"fk_{table_name}_reversed_by_user_id_users",
        table_name,
        type_="foreignkey",
    )
    op.drop_constraint(
        f"fk_{table_name}_reversal_accounting_document_id_accounting_documents",
        table_name,
        type_="foreignkey",
    )
    op.drop_column(table_name, "reversal_reason")
    op.drop_column(table_name, "reversed_by_user_id")
    op.drop_column(table_name, "reversed_at")
    op.drop_column(table_name, "reversal_accounting_document_id")


def upgrade() -> None:
    _add_reversal_columns("supplier_payments")
    _add_reversal_columns("customer_receipts")


def downgrade() -> None:
    _drop_reversal_columns("customer_receipts")
    _drop_reversal_columns("supplier_payments")
