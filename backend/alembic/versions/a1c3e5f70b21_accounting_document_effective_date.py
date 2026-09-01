"""accounting_documents.effective_date — fecha económica del asiento

Revision ID: a1c3e5f70b21
Revises: 4445cc3ebba5
Create Date: 2026-09-01

ORDEN MAESTRA §9/§26. `effective_date` es la fecha ECONÓMICA (la del
documento fuente de negocio); `posted_at` es el timestamp técnico. El flujo
de caja real agrupa por `effective_date` — importar remesas históricas hoy
ya no las concentra "hoy".

Backfill NO destructivo y sin inventar fechas:
1. baseline = date(posted_at) (una fecha real, aunque no la ideal);
2. donde EXISTE la fecha fuente real, se usa esa (remesas, pagos, cobros,
   transferencias, gastos, facturas AP/AR, cierres de caja).

No destructiva: la columna queda NOT NULL con server_default para filas
nuevas fuera del Posting Engine (defensivo), pero el Posting Engine siempre
la fija explícitamente.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e5f70b21"
down_revision: Union[str, None] = "4445cc3ebba5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SOURCE_UPDATES = [
    # (source table, date column, link column on source table)
    ("remittances", "remittance_date", "accounting_document_id"),
    ("supplier_payments", "payment_date", "accounting_document_id"),
    ("customer_receipts", "receipt_date", "accounting_document_id"),
    ("treasury_transfers", "transfer_date", "accounting_document_id"),
    ("general_expenses", "expense_date", "accounting_document_id"),
    ("customer_invoices", "invoice_date", "accounting_document_id"),
    ("cash_closings", "closing_date", "accounting_document_id"),
    ("supplier_invoices", "invoice_date", "accrual_document_id"),
]


def upgrade() -> None:
    op.add_column(
        "accounting_documents",
        sa.Column("effective_date", sa.Date(), nullable=True),
    )

    # 1. baseline: la fecha del posting (real, aunque no la económica ideal).
    op.execute(
        "UPDATE accounting_documents "
        "SET effective_date = (posted_at AT TIME ZONE 'America/Tegucigalpa')::date "
        "WHERE effective_date IS NULL AND posted_at IS NOT NULL"
    )
    op.execute(
        "UPDATE accounting_documents "
        "SET effective_date = created_at::date "
        "WHERE effective_date IS NULL"
    )

    # 2. donde exista la fecha fuente real de negocio, usarla.
    for table, date_col, link_col in _SOURCE_UPDATES:
        op.execute(
            f"UPDATE accounting_documents AS d "
            f"SET effective_date = s.{date_col} "
            f"FROM {table} AS s "
            f"WHERE s.{link_col} = d.id AND s.{date_col} IS NOT NULL"
        )

    op.alter_column(
        "accounting_documents",
        "effective_date",
        existing_type=sa.Date(),
        nullable=False,
        server_default=sa.text("CURRENT_DATE"),
    )


def downgrade() -> None:
    op.drop_column("accounting_documents", "effective_date")
