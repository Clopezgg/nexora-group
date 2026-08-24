import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# OperationScope (ver CLAUDE.md §7 y docs/ACCOUNTING.md INV-OPS-*): concepto
# de dominio compartido por TODO documento financiero/administrativo que
# construyan los demás tracks (Treasury, AP, AR, Procurement, ...). Vive aquí
# porque AccountingDocument es el punto único por el que pasa todo posting.
OPERATION_SCOPES = ("CENTRAL", "GENERAL", "PROJECT")

ACCOUNTING_DOCUMENT_STATUSES = ("DRAFT", "POSTED", "REVERSED")


class AccountingDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Cabecera de un asiento contable (journal entry). Ver PostingService en
    app/services/posting_service.py — es el único camino permitido para crear
    o revertir uno de estos documentos; nunca se construye a mano en un
    controller de otro módulo."""

    __tablename__ = "accounting_documents"
    __table_args__ = (
        CheckConstraint(
            "(scope IN ('CENTRAL','GENERAL') AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_accounting_documents_operation_scope",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    document_type_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("document_types.code"), nullable=False
    )
    document_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal("1"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id"), nullable=True
    )
    reversal_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class JournalLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "(debit_amount = 0 OR credit_amount = 0) AND (debit_amount >= 0 AND credit_amount >= 0)",
            name="ck_journal_lines_single_sided_non_negative",
        ),
    )

    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Dimensiones contables (ver CLAUDE.md §7 / orden maestra §23). project_id
    # y cost_center_id son FKs reales porque esas tablas ya existen. El resto
    # de dimensiones (supplier, customer, asset, warehouse) todavía no tienen
    # tabla propia -- viven en este JSONB abierto hasta que el track dueño
    # (C/D/E) cree la entidad real; en ese momento debe migrarse a FK real,
    # no quedarse en JSONB para siempre. Registrado como deuda intencional en
    # docs/ACCOUNTING.md.
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="RESTRICT"), nullable=True
    )
    extra_dimensions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PostingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Resuelve el par débito/crédito por defecto para un document_type. No
    reemplaza asientos multi-línea con desglose de impuestos -- para esos
    casos el caller de PostingService arma las líneas explícitamente y este
    motor solo valida el invariante de doble partida. Ver docs/ACCOUNTING.md
    "Posting Engine — contrato"."""

    __tablename__ = "posting_rules"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    document_type_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("document_types.code"), nullable=False
    )
    scope: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    debit_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    credit_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class TaxLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tax_lines"

    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="CASCADE"), nullable=False
    )
    tax_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_codes.id", ondelete="RESTRICT"), nullable=False
    )
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class AccountingSourceLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Enlace genérico documento contable -> documento de negocio origen
    (remesa, factura de proveedor, etc.). Permite la trazabilidad de
    documento fuente (orden maestra §98) sin que este track dependa de
    tablas que otros tracks todavía no han creado."""

    __tablename__ = "accounting_source_links"

    accounting_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
