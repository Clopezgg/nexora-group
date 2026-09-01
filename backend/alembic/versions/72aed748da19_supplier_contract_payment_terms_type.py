"""supplier_contract payment_terms_type

Revision ID: 72aed748da19
Revises: e6b8d0c41a77
Create Date: 2026-09-01 15:11:17.883928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72aed748da19'
down_revision: Union[str, None] = 'e6b8d0c41a77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "supplier_contracts",
        sa.Column(
            "payment_terms_type",
            sa.String(length=16),
            nullable=False,
            server_default="LUMP_SUM",
        ),
    )
    # Backfill: contratos que ya tienen un plan de pagos heredan el tipo del plan.
    op.execute(
        """
        UPDATE supplier_contracts sc
        SET payment_terms_type = s.schedule_type
        FROM contract_payment_schedules s
        WHERE s.supplier_contract_id = sc.id
          AND s.schedule_type IN ('MONTHLY', 'CUSTOM')
        """
    )
    op.create_check_constraint(
        "ck_supplier_contracts_payment_terms_type",
        "supplier_contracts",
        "payment_terms_type IN ('LUMP_SUM', 'MONTHLY', 'CUSTOM')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_supplier_contracts_payment_terms_type", "supplier_contracts", type_="check"
    )
    op.drop_column("supplier_contracts", "payment_terms_type")
