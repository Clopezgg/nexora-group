"""company + project document profile (orden maestra final §29-§32)

Revision ID: 952f802ae816
Revises: 2640b82e65b8
Create Date: 2026-09-01

Campos documentales de la compañía (dirección, teléfono, correo, nombre
comercial, footer, logo/firma privados) y de localización del proyecto.
Todo nullable, sin backfill: se configuran desde
Configuración -> Perfil de empresa -> Documentos. No destructiva.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "952f802ae816"
down_revision: Union[str, None] = "2640b82e65b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COMPANY_COLS = [
    ("trade_name", sa.String(255)),
    ("address_line_1", sa.String(255)),
    ("address_line_2", sa.String(255)),
    ("city", sa.String(120)),
    ("state_department", sa.String(120)),
    ("phone", sa.String(64)),
    ("email", sa.String(255)),
    ("website", sa.String(255)),
    ("voucher_footer_text", sa.String(500)),
]
_PROJECT_COLS = [
    ("address_line_1", sa.String(255)),
    ("address_line_2", sa.String(255)),
    ("city", sa.String(120)),
    ("state_department", sa.String(120)),
    ("country", sa.String(2)),
    ("location_reference", sa.String(500)),
]


def upgrade() -> None:
    for name, coltype in _COMPANY_COLS:
        op.add_column("companies", sa.Column(name, coltype, nullable=True))
    op.add_column("companies", sa.Column("logo_evidence_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("companies", sa.Column("signature_evidence_id", postgresql.UUID(as_uuid=True), nullable=True))
    for name, coltype in _PROJECT_COLS:
        op.add_column("projects", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name, _ in _PROJECT_COLS:
        op.drop_column("projects", name)
    op.drop_column("companies", "signature_evidence_id")
    op.drop_column("companies", "logo_evidence_id")
    for name, _ in _COMPANY_COLS:
        op.drop_column("companies", name)
