import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Suppliers/Contracts (orden maestra §57-60). `banking_details` es la
# información bancaria DEL PROVEEDOR para pagarle -- nunca confundir con
# `TreasuryAccount` (dinero propio de la company, ver CLAUDE.md §7).
SUPPLIER_STATUSES = ("ACTIVE", "INACTIVE", "BLOCKED")
SUPPLIER_CONTRACT_STATUSES = ("DRAFT", "ACTIVE", "COMPLETED", "TERMINATED")
# Naturaleza del costo del contrato de ejecución (orden maestra final §13).
# UX ES: Mano de obra / Subcontrato / Materiales / Equipo / Servicios
# profesionales / Otro.
SUPPLIER_CONTRACT_CATEGORIES = (
    "LABOR",
    "SUBCONTRACT",
    "MATERIALS",
    "EQUIPMENT",
    "PROFESSIONAL_SERVICES",
    "OTHER",
)
SUPPLIER_CONTRACT_CATEGORY_LABELS_ES = {
    "LABOR": "Mano de obra",
    "SUBCONTRACT": "Subcontrato",
    "MATERIALS": "Materiales",
    "EQUIPMENT": "Equipo",
    "PROFESSIONAL_SERVICES": "Servicios profesionales",
    "OTHER": "Otro",
}


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # `address` (texto libre) se conserva por compatibilidad. La dirección
    # estructurada es la arquitectura canónica (orden maestra final §26) y la
    # que consume el comprobante — mismo modelo que `projects`.
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state_department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    classification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banking_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SupplierContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Contract / Subcontract (orden maestra §59-60)."""

    __tablename__ = "supplier_contracts"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "contract_number", name="uq_supplier_contracts_company_number"
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    contract_number: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="OTHER", server_default="OTHER"
    )
    scope_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    advance_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    retention_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    payment_terms: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
