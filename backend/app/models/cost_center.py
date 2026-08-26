import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CostCenter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cost_centers"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_cost_centers_company_code"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class EconomicCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "economic_categories"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_economic_categories_company_code"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
