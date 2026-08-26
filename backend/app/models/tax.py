import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TaxCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tax_codes"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_tax_codes_company_code"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
