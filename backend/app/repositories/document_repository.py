import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentVersion


def create_document(
    db: Session,
    *,
    company_id: uuid.UUID,
    scope: str,
    project_id: uuid.UUID | None,
    category: str,
    title: str,
    description: str | None,
) -> Document:
    document = Document(
        company_id=company_id,
        scope=scope,
        project_id=project_id,
        category=category,
        title=title,
        description=description,
    )
    db.add(document)
    db.flush()
    return document


def get_document(db: Session, document_id: uuid.UUID) -> Document | None:
    stmt = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.versions))
    )
    return db.execute(stmt).scalar_one_or_none()


def list_documents(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.company_id == company_id)
        .options(selectinload(Document.versions))
        .order_by(Document.created_at.desc())
    )
    if project_id is not None:
        stmt = stmt.where(Document.project_id == project_id)
    return list(db.execute(stmt).scalars())


def list_document_versions(db: Session, *, document_id: uuid.UUID) -> list[DocumentVersion]:
    stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    return list(db.execute(stmt).scalars())


def get_active_version(db: Session, *, document_id: uuid.UUID) -> DocumentVersion | None:
    stmt = select(DocumentVersion).where(
        DocumentVersion.document_id == document_id, DocumentVersion.status == "ACTIVE"
    )
    return db.execute(stmt).scalar_one_or_none()


def create_document_version(
    db: Session,
    *,
    document_id: uuid.UUID,
    version_number: int,
    evidence_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    notes: str | None = None,
) -> DocumentVersion:
    version = DocumentVersion(
        document_id=document_id,
        version_number=version_number,
        evidence_id=evidence_id,
        uploaded_by=uploaded_by,
        notes=notes,
        status="ACTIVE",
    )
    db.add(version)
    db.flush()
    return version
