import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Fixed Assets (orden maestra §62) + depreciación straight-line (§69). La
# depreciación es un cálculo real sobre cost/useful_life/salvage -- nunca un
# número inventado. Contabilización pasa por posting_service (nunca
# débitos/créditos hardcodeados en el controller), documentada en
# docs/ACCOUNTING.md (asiento tipo DEP, dueño Track D). `scope`/`project_id`/
# `cost_center_id` reusan el mismo patrón de atribución que AP (ver
# app/models/ap.py) -- Project nunca custodia dinero, solo recibe el costo de
# depreciación como atribución (CLAUDE.md §1/§7).
ASSET_STATUSES = ("ACTIVE", "UNDER_MAINTENANCE", "DISPOSED", "RETIRED")


class FixedAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fixed_assets"
    __table_args__ = (
        CheckConstraint("cost > 0", name="ck_fixed_assets_cost_positive"),
        CheckConstraint("salvage_value >= 0", name="ck_fixed_assets_salvage_non_negative"),
        CheckConstraint("salvage_value < cost", name="ck_fixed_assets_salvage_below_cost"),
        CheckConstraint("useful_life_months > 0", name="ck_fixed_assets_useful_life_positive"),
        CheckConstraint(
            "status IN ('ACTIVE','UNDER_MAINTENANCE','DISPOSED','RETIRED')",
            name="ck_fixed_assets_status_valid",
        ),
        CheckConstraint(
            "(scope IN ('CENTRAL','GENERAL') AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_fixed_assets_operation_scope",
        ),
        UniqueConstraint("supplier_invoice_id", name="uq_fixed_assets_supplier_invoice_id"),
        UniqueConstraint(
            "capitalization_document_id",
            name="uq_fixed_assets_capitalization_document_id",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), ForeignKey("currencies.code"), nullable=False)
    useful_life_months: Mapped[int] = mapped_column(Integer, nullable=False)
    salvage_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="GENERAL")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    cost_center_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="RESTRICT"), nullable=True
    )
    depreciation_expense_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    accumulated_depreciation_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("supplier_invoices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    capitalization_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True
    )
    capitalization_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounting_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )


class DepreciationEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Una fila por periodo depreciado. `period_start` es único por asset a
    nivel de constraint REAL de PostgreSQL (`uq_depreciation_entries_asset_period`)
    -- un mismo periodo nunca puede generar dos postings DEP para el mismo
    activo, ni siquiera bajo escritura concurrente."""

    __tablename__ = "depreciation_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_depreciation_entries_amount_positive"),
        CheckConstraint("period_end >= period_start", name="ck_depreciation_entries_period_valid"),
        UniqueConstraint("asset_id", "period_start", name="uq_depreciation_entries_asset_period"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fixed_assets.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    accounting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="SET NULL"), nullable=True
    )
