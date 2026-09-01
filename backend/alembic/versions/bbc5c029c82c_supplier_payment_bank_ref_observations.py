"""supplier_payments: bank_transaction_reference + payment_observations

Revision ID: bbc5c029c82c
Revises: 952f802ae816
Create Date: 2026-09-01

Orden maestra final §24-§25. Referencia del movimiento bancario (distinta del
número de nuestra cuenta) y observaciones persistidas del pago. Ambas
nullable, sin backfill. No destructiva.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "bbc5c029c82c"
down_revision: Union[str, None] = "952f802ae816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "supplier_payments",
        sa.Column("bank_transaction_reference", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "supplier_payments",
        sa.Column("payment_observations", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supplier_payments", "payment_observations")
    op.drop_column("supplier_payments", "bank_transaction_reference")
