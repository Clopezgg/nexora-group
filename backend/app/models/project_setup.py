import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProjectSetupRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted, retryable project-creation command.

    The command intentionally stores the requested configuration before any
    domain row is created.  The core Project/WBS/Budget/Contract/Plan and the
    Document rows are created in one database transaction by the executor; a
    failed attempt therefore never exposes a half-configured project.
    Evidence files are staged separately because Blob Storage is not part of
    PostgreSQL's transaction.  They remain explicitly staged until this run
    atomically turns them into project documents.
    """

    __tablename__ = "project_setup_runs"
    __table_args__ = (
        UniqueConstraint("company_id", "idempotency_key", name="uq_project_setup_runs_company_key"),
        UniqueConstraint("project_id", name="uq_project_setup_runs_project"),
        CheckConstraint(
            "status IN ('DRAFT', 'EXECUTING', 'COMPLETED', 'FAILED')",
            name="ck_project_setup_runs_valid_status",
        ),
        Index("ix_project_setup_runs_company_status", "company_id", "status"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    activate: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    failure_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
