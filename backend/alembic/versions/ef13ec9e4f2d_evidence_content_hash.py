"""evidence: content_hash (SHA-256 de integridad/auditoria)

Revision ID: ef13ec9e4f2d
Revises: f453d24d2120
Create Date: 2026-08-31

Se agrega `evidence.content_hash` (SHA-256 hex, 64 chars, nullable). No es una
firma digital: es un control de integridad/auditoria para contrastar que el
blob almacenado no cambio respecto a lo recibido en el upload. Nullable para
tolerar filas historicas anteriores a esta migracion sin backfill costoso.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ef13ec9e4f2d"
down_revision: Union[str, None] = "f453d24d2120"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evidence", "content_hash")
