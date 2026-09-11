"""bind supplier invoices to an explicit contract installment

Revision ID: a8b9c0d1e2f3
Revises: c7d8e9f0a1b2
"""

from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supplier_invoices",
        sa.Column("contract_installment_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_supplier_invoices_contract_installment",
        "supplier_invoices",
        "contract_payment_installments",
        ["contract_installment_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_supplier_invoices_contract_installment",
        "supplier_invoices",
        type_="foreignkey",
    )
    op.drop_column("supplier_invoices", "contract_installment_id")
