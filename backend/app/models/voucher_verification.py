import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class VoucherVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Token opaco de verificación pública de un comprobante (orden maestra
    correctiva §39-§42). NO es una firma PKI: es un identificador aleatorio
    persistido que el QR del PDF codifica y el endpoint público resuelve a un
    conjunto mínimo de datos. Uno por AccountingDocument."""

    __tablename__ = "voucher_verifications"

    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounting_documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    document_number: Mapped[str] = mapped_column(String(64), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    beneficiary: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[str] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), nullable=False)
    document_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_code: Mapped[str] = mapped_column(String(16), nullable=False)
