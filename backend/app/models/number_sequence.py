import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Numeración concurrency-safe (nunca MAX()+1). El servicio de numeración
# (app/services/numbering_service.py) hace SELECT ... FOR UPDATE sobre la
# fila (company_id, document_type_code, year) antes de incrementar
# current_value, así que dos requests concurrentes nunca obtienen el mismo
# número.


class NumberSequence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "number_sequences"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "document_type_code", "year", name="uq_number_sequences_scope"
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    document_type_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("document_types.code"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
