import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

ACCOUNT_TYPES = ("ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE")

# NXR-REQ-0016/0093, Cash Flow. Clasificación opcional de una cuenta NO
# ligada a Treasury (ver docs/superpowers/specs/2026-08-25-financial-
# statements-design.md, "Explícitamente fuera de alcance" -- ahora sí en
# alcance). None = sin clasificar todavía (el reporte lo muestra como
# "Sin clasificar", nunca lo oculta ni lo fuerza a un valor).
CASH_FLOW_ACTIVITIES = ("OPERATING", "INVESTING", "FINANCING")


class ChartOfAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chart_of_accounts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("chart_of_account_id", "code", name="uq_accounts_chart_code"),)

    chart_of_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    is_postable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cash_flow_activity: Mapped[str | None] = mapped_column(String(16), nullable=True)
