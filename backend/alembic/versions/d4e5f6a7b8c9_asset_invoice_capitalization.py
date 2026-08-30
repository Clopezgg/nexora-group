"""link fixed assets to supplier invoices and capitalization GL

Revision ID: d4e5f6a7b8c9
Revises: c8a9e1f2b3d4
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c8a9e1f2b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO document_types (code, name, number_prefix)
        VALUES ('CAP', 'Capitalización de activo fijo', 'CAP')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.add_column(
        "fixed_assets",
        sa.Column("supplier_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "fixed_assets",
        sa.Column("capitalization_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "fixed_assets",
        sa.Column("capitalization_document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_fixed_assets_supplier_invoice",
        "fixed_assets",
        "supplier_invoices",
        ["supplier_invoice_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_fixed_assets_capitalization_account",
        "fixed_assets",
        "accounts",
        ["capitalization_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_fixed_assets_capitalization_document",
        "fixed_assets",
        "accounting_documents",
        ["capitalization_document_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_fixed_assets_supplier_invoice_id",
        "fixed_assets",
        ["supplier_invoice_id"],
    )
    op.create_unique_constraint(
        "uq_fixed_assets_capitalization_document_id",
        "fixed_assets",
        ["capitalization_document_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_fixed_assets_capitalization_document_id",
        "fixed_assets",
        type_="unique",
    )
    op.drop_constraint(
        "uq_fixed_assets_supplier_invoice_id",
        "fixed_assets",
        type_="unique",
    )
    op.drop_constraint(
        "fk_fixed_assets_capitalization_document",
        "fixed_assets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_fixed_assets_capitalization_account",
        "fixed_assets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_fixed_assets_supplier_invoice",
        "fixed_assets",
        type_="foreignkey",
    )
    op.drop_column("fixed_assets", "capitalization_document_id")
    op.drop_column("fixed_assets", "capitalization_account_id")
    op.drop_column("fixed_assets", "supplier_invoice_id")
    op.execute(
        """
        DELETE FROM document_types AS dt
        WHERE dt.code = 'CAP'
          AND NOT EXISTS (
              SELECT 1 FROM accounting_documents AS ad
              WHERE ad.document_type_code = dt.code
          )
          AND NOT EXISTS (
              SELECT 1 FROM number_sequences AS ns
              WHERE ns.document_type_code = dt.code
          )
        """
    )
