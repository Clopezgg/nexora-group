"""voucher_issuances.company_website_snapshot (§27)

Revision ID: e6b8d0c41a77
Revises: d5a7c9e30f66
Create Date: 2026-09-01

ORDEN MAESTRA §27 — el comprobante premium imprime la identidad completa de
la empresa emisora, incluido el sitio web, desde el snapshot inmutable de
emisión.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6b8d0c41a77"
down_revision: Union[str, None] = "d5a7c9e30f66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voucher_issuances",
        sa.Column("company_website_snapshot", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voucher_issuances", "company_website_snapshot")
