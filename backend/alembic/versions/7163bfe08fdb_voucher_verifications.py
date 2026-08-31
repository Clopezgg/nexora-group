"""voucher_verifications: token opaco de verificacion publica de comprobantes

Revision ID: 7163bfe08fdb
Revises: ef13ec9e4f2d
Create Date: 2026-08-31

Orden maestra correctiva §39-§42. Tabla que respalda el QR del comprobante:
un token aleatorio opaco por AccountingDocument, resuelto por el endpoint
publico /api/verificar/comprobante/{token} a un conjunto minimo de datos.
No hay backfill: los comprobantes existentes obtienen su token la proxima
vez que se generan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7163bfe08fdb"
down_revision: Union[str, None] = "ef13ec9e4f2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voucher_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "accounting_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounting_documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("document_number", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("beneficiary", sa.String(length=255), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False),
        sa.Column("document_status", sa.String(length=32), nullable=False),
        sa.Column("verification_code", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_voucher_verifications_token", "voucher_verifications", ["token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_voucher_verifications_token", table_name="voucher_verifications")
    op.drop_table("voucher_verifications")
