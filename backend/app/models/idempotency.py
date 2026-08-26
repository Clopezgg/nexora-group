import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

IDEMPOTENCY_STATUSES = ("PENDING", "COMPLETED")


class IdempotencyRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    command: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
