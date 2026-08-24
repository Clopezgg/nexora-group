import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(8), nullable=False)


class ExchangeRate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "from_currency_code", "to_currency_code", "as_of_date", name="uq_exchange_rate_pair_date"
        ),
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    from_currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code"), nullable=False
    )
    to_currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code"), nullable=False
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
