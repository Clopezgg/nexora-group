"""evidence.derived_blob_key / derived_mime_type — render derivado HEIC->JPEG (§28)

Revision ID: d5a7c9e30f66
Revises: c4f6a8b20d55
Create Date: 2026-09-01

ORDEN MAESTRA DEFINITIVA DE INTEGRACIÓN §28. Una foto HEIC de iPhone se
guarda tal cual (privada) y además se genera un JPEG derivado para poder
mostrarla en el visor y embeberla en el PDF del comprobante. Ambos campos
son nullable: sólo se llenan cuando el original no es directamente
renderizable.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5a7c9e30f66"
down_revision: Union[str, None] = "c4f6a8b20d55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("derived_blob_key", sa.String(length=500), nullable=True))
    op.add_column("evidence", sa.Column("derived_mime_type", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "derived_mime_type")
    op.drop_column("evidence", "derived_blob_key")
