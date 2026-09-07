"""supplier payment method

Revision ID: a7c9e1f30b52
Revises: f1a4c2d8e9b0
Create Date: 2026-09-06

Persiste el método del pago en el evento original. Los pagos históricos se
backfillean como TRANSFER por compatibilidad; la aplicación exige evidencia
para nuevos TRANSFER/DEPOSIT/CHECK antes de contabilizar.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c9e1f30b52"
down_revision: Union[str, None] = "f1a4c2d8e9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "supplier_payments",
        sa.Column("payment_method", sa.String(length=16), nullable=True),
    )
    op.execute("UPDATE supplier_payments SET payment_method = 'TRANSFER' WHERE payment_method IS NULL")
    op.alter_column("supplier_payments", "payment_method", nullable=False)
    op.create_check_constraint(
        "ck_supplier_payments_method",
        "supplier_payments",
        "payment_method IN ('TRANSFER','DEPOSIT','CHECK','CASH','OTHER')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_supplier_payments_method", "supplier_payments", type_="check")
    op.drop_column("supplier_payments", "payment_method")
