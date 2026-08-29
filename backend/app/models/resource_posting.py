import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

RESOURCE_POSTING_SOURCES = ("FUEL", "MAINTENANCE", "LABOR")


class ResourcePostingConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Company-owned GL mapping for automatic resource cost accruals.

    No account code is embedded in services. Each origin requires a postable
    EXPENSE debit account and a postable LIABILITY credit account from the same
    company before automatic posting is allowed.
    """

    __tablename__ = "resource_posting_configs"
    __table_args__ = (
        UniqueConstraint("company_id", "source_type", name="uq_resource_posting_company_source"),
        CheckConstraint(
            "source_type IN ('FUEL','MAINTENANCE','LABOR')",
            name="ck_resource_posting_source_valid",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    expense_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    offset_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
