import uuid

from sqlalchemy.orm import Session

from app.domain.errors import InvalidDocumentStateError
from app.models.document import Document, DocumentVersion
from app.repositories import document_repository
from app.services.financial_validation_service import (
    assert_evidence_belongs_to_company,
    assert_operation_scope,
    assert_project_belongs_to_company,
)

"""Document Management (bloque CONSTRUCTION CONTROL, orden maestra §77-78,
docs/DOCUMENTS_EVIDENCE.md). `create_document` crea el Document y su
primera DocumentVersion (v1, ACTIVE) en la misma transacción --  un
Document nunca existe sin al menos una versión. `add_document_version`
implementa el versionado inmutable: la versión anterior se marca
SUPERSEDED (nunca se borra/edita) y la nueva queda ACTIVE; el índice único
parcial `uq_document_versions_one_active_per_document` es la garantía real
de PostgreSQL bajo escritura concurrente, esta función es defensa en
profundidad con un mensaje de dominio claro."""


def create_document(
    db: Session,
    *,
    company_id: uuid.UUID,
    scope: str,
    project_id: uuid.UUID | None,
    category: str,
    title: str,
    description: str | None,
    evidence_id: uuid.UUID,
    uploaded_by: uuid.UUID,
) -> Document:
    assert_operation_scope(scope, project_id)
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)

    document = document_repository.create_document(
        db,
        company_id=company_id,
        scope=scope,
        project_id=project_id,
        category=category,
        title=title,
        description=description,
    )
    document_repository.create_document_version(
        db,
        document_id=document.id,
        version_number=1,
        evidence_id=evidence_id,
        uploaded_by=uploaded_by,
    )
    db.commit()
    return document_repository.get_document(db, document.id)


def get_document(db: Session, document_id: uuid.UUID) -> Document | None:
    return document_repository.get_document(db, document_id)


def list_documents(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[Document]:
    return document_repository.list_documents(db, company_id=company_id, project_id=project_id)


def list_document_versions(db: Session, *, document_id: uuid.UUID) -> list[DocumentVersion]:
    return document_repository.list_document_versions(db, document_id=document_id)


def add_document_version(
    db: Session,
    *,
    document_id: uuid.UUID,
    evidence_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    notes: str | None = None,
) -> DocumentVersion:
    document = document_repository.get_document(db, document_id)
    if document is None:
        raise ValueError(f"Document {document_id} no existe")
    if document.status != "ACTIVE":
        raise InvalidDocumentStateError(
            f"El documento {document.id} está {document.status}; no admite nuevas versiones"
        )
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=document.company_id)

    current = document_repository.get_active_version(db, document_id=document_id)
    if current is None:
        raise InvalidDocumentStateError(
            f"El documento {document.id} no tiene una versión ACTIVE -- estado inconsistente"
        )

    # Historial inmutable: la versión anterior NUNCA se borra/edita, solo se
    # marca SUPERSEDED. La nueva fila queda ACTIVE y se convierte en el
    # "current version" del documento (Document.current_version se deriva de
    # esta transición, ver app/models/document.py).
    current.status = "SUPERSEDED"
    new_version = document_repository.create_document_version(
        db,
        document_id=document_id,
        version_number=current.version_number + 1,
        evidence_id=evidence_id,
        uploaded_by=uploaded_by,
        notes=notes,
    )
    db.commit()
    db.refresh(new_version)
    return new_version
