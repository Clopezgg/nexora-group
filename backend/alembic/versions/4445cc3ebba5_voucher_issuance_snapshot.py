"""voucher_issuances: snapshot inmutable del comprobante emitido

Revision ID: 4445cc3ebba5
Revises: bbc5c029c82c
Create Date: 2026-09-01

Orden maestra final §27/§28. Una fila por AccountingDocument con todo lo que
se imprime congelado en el momento de la primera emisión. Sin backfill.
No destructiva.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4445cc3ebba5"
down_revision: Union[str, None] = "bbc5c029c82c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STR = sa.String


def upgrade() -> None:
    op.create_table(
        "voucher_issuances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("accounting_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("document_number", _STR(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("company_name_snapshot", _STR(255), nullable=False),
        sa.Column("company_legal_name_snapshot", _STR(255), nullable=True),
        sa.Column("company_trade_name_snapshot", _STR(255), nullable=True),
        sa.Column("company_fiscal_id_snapshot", _STR(64), nullable=True),
        sa.Column("company_address_snapshot", _STR(600), nullable=True),
        sa.Column("company_phone_snapshot", _STR(64), nullable=True),
        sa.Column("company_email_snapshot", _STR(255), nullable=True),
        sa.Column("company_footer_snapshot", _STR(500), nullable=True),
        sa.Column("project_name_snapshot", _STR(255), nullable=True),
        sa.Column("project_address_snapshot", _STR(600), nullable=True),
        sa.Column("contract_number_snapshot", _STR(64), nullable=True),
        sa.Column("contract_period_snapshot", _STR(40), nullable=True),
        sa.Column("beneficiary_name_snapshot", _STR(255), nullable=False),
        sa.Column("beneficiary_address_snapshot", _STR(600), nullable=True),
        sa.Column("beneficiary_tax_id_snapshot", _STR(64), nullable=True),
        sa.Column("payer_name_snapshot", _STR(255), nullable=False),
        sa.Column("approver_name_snapshot", _STR(255), nullable=True),
        sa.Column("payment_method_snapshot", _STR(40), nullable=False),
        sa.Column("bank_name_snapshot", _STR(255), nullable=True),
        sa.Column("bank_account_mask_snapshot", _STR(40), nullable=True),
        sa.Column("bank_transaction_reference_snapshot", _STR(120), nullable=True),
        sa.Column("payment_observations_snapshot", _STR(500), nullable=True),
        sa.Column("amount_snapshot", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency_code_snapshot", _STR(8), nullable=False),
        sa.Column("contract_value_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("paid_before_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("paid_accumulated_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("contract_balance_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("verification_token", _STR(64), nullable=False),
        sa.Column("verification_code", _STR(16), nullable=False),
        sa.Column("status", _STR(16), nullable=False, server_default="ISSUED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("voucher_issuances")
