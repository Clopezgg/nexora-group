"""company voucher identity: fixed payer + configurable approver

Revision ID: 251d08ffc0df
Revises: d4e5f6a7b8c9
Create Date: 2026-08-31

Orden maestra FINAL, Phase 2 (Comprobantes): el pagador del comprobante es un
dato de la compañía que se asigna una sola vez (read-only una vez fijado,
mismo patrón que companies.code); el aprobador es configurable. Nada se
hardcodea en el generador de PDF.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "251d08ffc0df"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("voucher_payer_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("voucher_approver_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "voucher_approver_name")
    op.drop_column("companies", "voucher_payer_name")
