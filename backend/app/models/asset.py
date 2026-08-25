import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Fixed Assets (orden maestra §62) + depreciación straight-line (§69). La
# depreciación es un cálculo real sobre cost/useful_life/salvage -- nunca un
# número inventado. Contabilización opcional vía posting_service, documentada
# en docs/ACCOUNTING.md (asiento tipo DEP, dueño Track D).
ASSET_STATUSES = ("ACTIVE", "UNDER_MAINTENANCE", "DISPOSED", "RETIRED")


class FixedAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fixed_assets"

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


class DepreciationEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Una fila por periodo depreciado. `period_start`/`period_end` no se
    solapan para el mismo asset (verificado por servicio, no constraint DB
    todavía -- documentado como deuda intencional si se necesita concurrencia
    real de generación de depreciación)."""

    __tablename__ = "depreciation_entries"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fixed_assets.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    accounting_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounting_documents.id", ondelete="SET NULL"), nullable=True
    )
