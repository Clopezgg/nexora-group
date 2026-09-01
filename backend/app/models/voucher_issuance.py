"""VoucherIssuance — snapshot INMUTABLE de un comprobante emitido (orden
maestra final §27/§28/§62).

Al emitir el PDF por primera vez para un AccountingDocument se congela aquí
todo lo que se imprime: datos de empresa, beneficiario, contrato, banco,
importes y el corte del período contractual. Si después cambia la dirección
de NEXORA, el nombre comercial, el aprobador, etc., el comprobante de agosto
sigue mostrando los datos de agosto — se lee de esta fila, nunca de master
data en vivo.

Una fila por AccountingDocument (el mismo documento contabilizado nunca
cambia). Correcciones = void/reissue del pago (reversal), no mutación.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class VoucherIssuance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "voucher_issuances"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounting_documents.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    document_number: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)

    # --- Snapshots de empresa ---
    company_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    company_legal_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_trade_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_fiscal_id_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_address_snapshot: Mapped[str | None] = mapped_column(String(600), nullable=True)
    company_phone_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_email_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_footer_snapshot: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- Snapshots de proyecto / contrato ---
    project_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_address_snapshot: Mapped[str | None] = mapped_column(String(600), nullable=True)
    contract_number_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contract_period_snapshot: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # --- Snapshots de beneficiario / pagador / aprobador ---
    beneficiary_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    beneficiary_address_snapshot: Mapped[str | None] = mapped_column(String(600), nullable=True)
    beneficiary_tax_id_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payer_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Snapshots de banco / pago ---
    payment_method_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    bank_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_account_mask_snapshot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bank_transaction_reference_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_observations_snapshot: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- Snapshots de importes ---
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code_snapshot: Mapped[str] = mapped_column(String(8), nullable=False)
    contract_value_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    paid_before_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    paid_accumulated_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    contract_balance_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    verification_token: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ISSUED")
