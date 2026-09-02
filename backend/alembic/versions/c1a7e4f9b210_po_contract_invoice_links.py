"""purchase-order ↔ supplier-contract and supplier-invoice ↔ purchase-order links

Revision ID: c1a7e4f9b210
Revises: bad8f42b8f59
Create Date: 2026-09-02

ORDEN MAESTRA §19 — sin estos enlaces el motor de compromisos no puede saber
que una PO pertenece a un contrato (y por tanto es un desglose del compromiso
contractual, no un compromiso adicional) ni que una factura releva una PO.
Ambas columnas son nullable: una PO / factura puede no derivar de un contrato
ni de una PO.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a7e4f9b210"
down_revision: Union[str, None] = "bad8f42b8f59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column("supplier_contract_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_purchase_orders_supplier_contract",
        "purchase_orders",
        "supplier_contracts",
        ["supplier_contract_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_purchase_orders_supplier_contract_id",
        "purchase_orders",
        ["supplier_contract_id"],
    )

    op.add_column(
        "supplier_invoices",
        sa.Column("purchase_order_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_supplier_invoices_purchase_order",
        "supplier_invoices",
        "purchase_orders",
        ["purchase_order_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_supplier_invoices_purchase_order_id",
        "supplier_invoices",
        ["purchase_order_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_invoices_purchase_order_id", table_name="supplier_invoices")
    op.drop_constraint("fk_supplier_invoices_purchase_order", "supplier_invoices", type_="foreignkey")
    op.drop_column("supplier_invoices", "purchase_order_id")

    op.drop_index("ix_purchase_orders_supplier_contract_id", table_name="purchase_orders")
    op.drop_constraint("fk_purchase_orders_supplier_contract", "purchase_orders", type_="foreignkey")
    op.drop_column("purchase_orders", "supplier_contract_id")
