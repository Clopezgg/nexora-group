"""suppliers: dirección estructurada (§26)

Revision ID: c4f6a8b20d55
Revises: b2d4f6a80c33
Create Date: 2026-09-01

ORDEN MAESTRA DEFINITIVA DE INTEGRACIÓN §26.

`voucher_service._resolve_beneficiary_details` leía `supplier.address_line_1`
/ `city` / `country`, campos que no existían — el bloque de dirección del
beneficiario en el comprobante salía siempre vacío. Se adopta la dirección
ESTRUCTURADA como arquitectura canónica (mismo modelo que `projects`),
conservando el texto libre `address`.

Backfill no destructivo: donde `address_line_1` queda vacío se copia el
texto libre `address` (una migración de dato real, sin inventar nada).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4f6a8b20d55"
down_revision: Union[str, None] = "b2d4f6a80c33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = [
    ("address_line_1", sa.String(length=255)),
    ("address_line_2", sa.String(length=255)),
    ("city", sa.String(length=120)),
    ("state_department", sa.String(length=120)),
    ("country", sa.String(length=2)),
]


def upgrade() -> None:
    for name, type_ in _COLUMNS:
        op.add_column("suppliers", sa.Column(name, type_, nullable=True))
    op.execute(
        """
        UPDATE suppliers
        SET address_line_1 = left(btrim(address), 255)
        WHERE address IS NOT NULL
          AND btrim(address) <> ''
          AND address_line_1 IS NULL
        """
    )


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("suppliers", name)
