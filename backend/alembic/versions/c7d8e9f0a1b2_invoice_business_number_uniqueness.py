"""Prevent duplicate AP/AR invoice numbers within a company and party."""

import sqlalchemy as sa

from alembic import op

revision = "c7d8e9f0a1b2"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def _add_normalized(table: str) -> None:
    op.add_column(table, sa.Column("invoice_number_normalized", sa.String(64), nullable=True))
    op.execute(
        sa.text(
            f"UPDATE {table} SET invoice_number_normalized = upper(regexp_replace(trim(invoice_number), '\\s+', '', 'g'))"
        )
    )
    duplicate = op.get_bind().execute(
        sa.text(
            f"SELECT 1 FROM {table} WHERE status <> 'CANCELLED' GROUP BY company_id, "
            f"{'supplier_id' if table == 'supplier_invoices' else 'customer_id'}, invoice_number_normalized HAVING count(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate:
        raise RuntimeError(f"{table}: existen números de factura duplicados; resolver antes de cerrar la migración")
    op.alter_column(table, "invoice_number_normalized", nullable=False)


def upgrade() -> None:
    _add_normalized("supplier_invoices")
    _add_normalized("customer_invoices")
    op.create_index(
        "uq_supplier_invoice_business_number", "supplier_invoices",
        ["company_id", "supplier_id", "invoice_number_normalized"], unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )
    op.create_index(
        "uq_customer_invoice_business_number", "customer_invoices",
        ["company_id", "customer_id", "invoice_number_normalized"], unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_customer_invoice_business_number", table_name="customer_invoices")
    op.drop_index("uq_supplier_invoice_business_number", table_name="supplier_invoices")
    op.drop_column("customer_invoices", "invoice_number_normalized")
    op.drop_column("supplier_invoices", "invoice_number_normalized")
