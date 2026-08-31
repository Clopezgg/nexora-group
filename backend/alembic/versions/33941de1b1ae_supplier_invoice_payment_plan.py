"""supplier invoice payment plan (installments)

Revision ID: 33941de1b1ae
Revises: 251d08ffc0df
Create Date: 2026-08-31

Orden maestra FINAL, Phase 2 (Comprobantes): planes/cuotas de pago para
facturas de proveedor. La suma de cuotas = total de la factura (validado en
el servicio, el plan se reemplaza de forma atómica).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "33941de1b1ae"
down_revision: Union[str, None] = "251d08ffc0df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplier_invoice_payment_plan_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "supplier_invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("supplier_invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_supplier_invoice_plan_amount_positive"),
        sa.CheckConstraint("sequence >= 1", name="ck_supplier_invoice_plan_sequence_positive"),
        sa.UniqueConstraint("supplier_invoice_id", "sequence", name="uq_supplier_invoice_plan_sequence"),
    )
    op.create_index(
        "ix_supplier_invoice_plan_invoice",
        "supplier_invoice_payment_plan_items",
        ["supplier_invoice_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_invoice_plan_invoice", table_name="supplier_invoice_payment_plan_items")
    op.drop_table("supplier_invoice_payment_plan_items")
