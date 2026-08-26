import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Evidence (bloque CONSTRUCTION CONTROL, orden maestra §79,
# docs/DOCUMENTS_EVIDENCE.md). Metadata REAL de un archivo subido a Azure
# Blob Storage vía app/integrations/azure_blob.py -- nunca se persiste el
# archivo en filesystem local (CLAUDE.md "No filesystem persistente").
# `blob_key` es la única prueba de que el archivo existe en Blob Storage; si
# `EVIDENCE_BACKEND` no está configurado, evidence_service nunca crea esta
# fila (no hay "mocks presentados como funcionalidad real": sin blob real no
# hay fila Evidence).
#
# `entity_type`/`entity_id` son un enlace polimórfico INFORMATIVO -- una
# etiqueta de conveniencia sobre "para qué se subió este archivo", sin FK de
# PostgreSQL (la tabla destino varía por caso de uso y no se puede declarar
# una FK real contra múltiples tablas). NO es el contrato de adjunto
# autoritativo: cualquier entidad de dominio que necesite un adjunto real
# declara su propia columna `evidence_id: UUID FK -> evidence.id` (ver
# docs/DOCUMENTS_EVIDENCE.md, mismo patrón que `ProgressRecord.evidence_id`
# en este mismo track).
EVIDENCE_ALLOWED_MIME_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
)


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (CheckConstraint("size_bytes > 0", name="ck_evidence_size_positive"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    blob_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
