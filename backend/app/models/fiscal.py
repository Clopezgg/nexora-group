import uuid
from datetime import date

from sqlalchemy import (
    DDL,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

FISCAL_PERIOD_STATUSES = ("OPEN", "SOFT_CLOSED", "CLOSED")


class FiscalYear(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fiscal_years"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_fiscal_years_company_code"),
        UniqueConstraint("id", "company_id", name="uq_fiscal_years_id_company"),
        ExcludeConstraint(
            ("company_id", "="),
            (text("daterange(start_date, end_date, '[]')"), "&&"),
            name="ex_fiscal_years_company_dates",
            using="gist",
        ),
        CheckConstraint(
            "start_date <= end_date", name="ck_fiscal_years_valid_date_range"
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class FiscalPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fiscal_periods"
    __table_args__ = (
        UniqueConstraint(
            "fiscal_year_id", "period_number", name="uq_fiscal_periods_year_number"
        ),
        ForeignKeyConstraint(
            ["fiscal_year_id", "company_id"],
            ["fiscal_years.id", "fiscal_years.company_id"],
            name="fk_fiscal_periods_year_company",
            ondelete="CASCADE",
        ),
        ExcludeConstraint(
            ("company_id", "="),
            (text("daterange(start_date, end_date, '[]')"), "&&"),
            name="ex_fiscal_periods_company_dates",
            using="gist",
        ),
        CheckConstraint(
            "start_date <= end_date", name="ck_fiscal_periods_valid_date_range"
        ),
        CheckConstraint(
            "period_number >= 1", name="ck_fiscal_periods_positive_period_number"
        ),
        CheckConstraint(
            "status IN ('OPEN', 'SOFT_CLOSED', 'CLOSED')",
            name="ck_fiscal_periods_valid_status",
        ),
    )

    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fiscal_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")


# Metadata-created isolated test schemas need the same GiST UUID operator class
# as Alembic-managed databases. The extension is database-wide and retained.
event.listen(
    FiscalYear.__table__,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS btree_gist").execute_if(dialect="postgresql"),
)
