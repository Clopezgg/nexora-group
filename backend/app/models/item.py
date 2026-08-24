import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Inventory master data (orden maestra §52). SKU único por company, no global
# -- dos companies del mismo grupo pueden usar el mismo SKU para cosas
# distintas.
ITEM_TYPES = ("MATERIAL", "CONSUMABLE", "TOOL", "SERVICE")
VALUATION_METHODS = ("MOVING_AVERAGE",)


class Item(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("company_id", "sku", name="uq_items_company_sku"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, default="MATERIAL")
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    uom: Mapped[str] = mapped_column(String(16), nullable=False, default="UND")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    valuation_method: Mapped[str] = mapped_column(String(32), nullable=False, default="MOVING_AVERAGE")
    track_inventory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
