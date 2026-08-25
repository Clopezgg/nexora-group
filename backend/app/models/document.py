import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Document Management (bloque CONSTRUCTION CONTROL, orden maestra §77-79,
# docs/DOCUMENTS_EVIDENCE.md). Un `Document` es el objeto de negocio
# versionado (p.ej. "Plano estructural nivel 3"); cada subida real de
# archivo vive en `Evidence` (app/models/evidence.py) -- Document nunca
# apunta directo a Azure Blob, siempre a través de una fila de Evidence.
#
# Historial inmutable: NUNCA se hace UPDATE/DELETE sobre una DocumentVersion
# ya creada. Subir una nueva versión crea una fila nueva y marca la anterior
# SUPERSEDED -- nunca se sobrescribe ni se borra (mismo principio que
# INV-ACC-002 para AccountingDocument, aplicado aquí a nivel de documento
# administrativo, no contable). El "current version pointer" del Document se
# deriva -- no se guarda como columna con FK circular -- de la única
# DocumentVersion en estado ACTIVE por documento, garantizado por el índice
# único parcial `uq_document_versions_one_active_per_document`.
DOCUMENT_STATUSES = ("ACTIVE", "ARCHIVED")
DOCUMENT_VERSION_STATUSES = ("ACTIVE", "SUPERSEDED")
DOCUMENT_CATEGORIES = (
    "CONTRACT",
    "DRAWING",
    "PERMIT",
    "REPORT",
    "SAFETY",
    "QUALITY",
    "PHOTO",
    "OTHER",
)


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "category IN ('CONTRACT','DRAWING','PERMIT','REPORT','SAFETY','QUALITY','PHOTO','OTHER')",
            name="ck_documents_category_valid",
        ),
        CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_documents_status_valid"),
        CheckConstraint(
            "(scope IN ('CENTRAL','GENERAL') AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_documents_operation_scope",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="GENERAL")
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")

    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number"
    )

    @property
    def current_version(self) -> "DocumentVersion | None":
        for version in self.versions:
            if version.status == "ACTIVE":
                return version
        return None


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Una fila por versión subida, nunca mutada tras crearse. El índice
    único parcial garantiza -- a nivel de constraint real de PostgreSQL, no
    solo de invariante de servicio -- que jamás existan dos versiones ACTIVE
    simultáneas para el mismo Document, ni bajo escritura concurrente."""

    __tablename__ = "document_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_document_versions_number_positive"),
        CheckConstraint("status IN ('ACTIVE','SUPERSEDED')", name="ck_document_versions_status_valid"),
        UniqueConstraint(
            "document_id", "version_number", name="uq_document_versions_document_number"
        ),
        Index(
            "uq_document_versions_one_active_per_document",
            "document_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="versions")
