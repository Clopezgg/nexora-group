"""Phase 2 domain integration: ThreeWayMatch FK, asset disposal constraints, budget stale docs

Revision ID: a7b3c4d5e6f7
Revises: f5a7b9c1d3e4
Create Date: 2026-09-08
"""

import sqlalchemy as sa

from alembic import op

revision = "a7b3c4d5e6f7"
down_revision = "f5a7b9c1d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NX-AUD-025: ThreeWayMatchResult.supplier_invoice_id must be a real FK
    # to SupplierInvoice. Previously it was a free UUID because Track C and
    # Track A built documents in parallel; now both tracks are integrated.
    op.create_foreign_key(
        "fk_three_way_match_supplier_invoice",
        "three_way_match_results",
        "supplier_invoices",
        ["supplier_invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # INV-AST-002/003/004: disposal tracking columns
    op.add_column("fixed_assets", sa.Column("disposal_date", sa.Date(), nullable=True))
    op.add_column("fixed_assets", sa.Column("disposal_proceeds", sa.Numeric(18, 2), nullable=True))
    op.add_column("fixed_assets", sa.Column("disposal_account_id", sa.dialects.postgresql.UUID(), nullable=True))
    op.add_column("fixed_assets", sa.Column("disposal_document_id", sa.dialects.postgresql.UUID(), nullable=True))
    op.add_column("fixed_assets", sa.Column("accumulated_depreciation", sa.Numeric(18, 2), nullable=True))

    op.create_foreign_key(
        "fk_fixed_assets_disposal_account",
        "fixed_assets",
        "accounts",
        ["disposal_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_fixed_assets_disposal_document",
        "fixed_assets",
        "accounting_documents",
        ["disposal_document_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # INV-AST-002: disposal_date must be set when status is DISPOSED/RETIRED
    op.create_check_constraint(
        "ck_fixed_assets_disposal_date",
        "fixed_assets",
        "(status NOT IN ('DISPOSED', 'RETIRED')) OR disposal_date IS NOT NULL",
    )

    # INV-AST-003: accumulated depreciation must be non-negative
    op.create_check_constraint(
        "ck_fixed_assets_accumulated_depreciation_non_negative",
        "fixed_assets",
        "COALESCE(accumulated_depreciation, 0) >= 0",
    )

    # INV-AST-004: disposal proceeds must be non-negative
    op.create_check_constraint(
        "ck_fixed_assets_disposal_proceeds_non_negative",
        "fixed_assets",
        "COALESCE(disposal_proceeds, 0) >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_fixed_assets_disposal_proceeds_non_negative", "fixed_assets")
    op.drop_constraint("ck_fixed_assets_accumulated_depreciation_non_negative", "fixed_assets")
    op.drop_constraint("ck_fixed_assets_disposal_date", "fixed_assets")
    op.drop_constraint("fk_three_way_match_supplier_invoice", "three_way_match_results")
