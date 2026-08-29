import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentResponse,
    DocumentVersionCreateRequest,
    DocumentVersionResponse,
)
from app.services import audit_service, document_service
from app.services.permission_service import accessible_project_ids, assert_company_access, require_permission

router = APIRouter(prefix="/documents", tags=["documents"])


def _resolve_document(db: Session, document_id: uuid.UUID):
    document = document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document no encontrado")
    return document


@router.post("", response_model=DocumentResponse, status_code=201)
def create_document(
    payload: DocumentCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.document", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> DocumentResponse:
    assert_company_access(
        db, user_id=user.id, resource="document.document", action="create", company_id=payload.company_id
    )
    document = document_service.create_document(
        db,
        company_id=payload.company_id,
        scope=payload.scope,
        project_id=payload.project_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        evidence_id=payload.evidence_id,
        uploaded_by=user.id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="document.document.create",
        entity_type="document.document",
        entity_id=document.id,
        company_id=payload.company_id,
        project_id=payload.project_id,
        before=None,
        after={"title": document.title, "category": document.category},
        correlation_id=correlation_id,
    )
    db.commit()
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    company_id: uuid.UUID = Query(alias="companyId"),
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.document", "read")),
) -> list[DocumentResponse]:
    assert_company_access(
        db, user_id=user.id, resource="document.document", action="read", company_id=company_id
    )
    allowed = accessible_project_ids(
        db, user_id=user.id, resource="document.document", action="read"
    )
    documents = document_service.list_documents(db, company_id=company_id, project_id=project_id)
    if allowed is not None:
        allowed_set = set(allowed)
        documents = [
            document
            for document in documents
            if document.project_id is None or document.project_id in allowed_set
        ]
    return [DocumentResponse.model_validate(document, from_attributes=True) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.document", "read")),
) -> DocumentResponse:
    document = _resolve_document(db, document_id)
    assert_company_access(
        db, user_id=user.id, resource="document.document", action="read", company_id=document.company_id
    )
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionResponse])
def list_document_versions(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.document", "read")),
) -> list[DocumentVersionResponse]:
    document = _resolve_document(db, document_id)
    assert_company_access(
        db, user_id=user.id, resource="document.document", action="read", company_id=document.company_id
    )
    return [
        DocumentVersionResponse.model_validate(v, from_attributes=True)
        for v in document_service.list_document_versions(db, document_id=document_id)
    ]


@router.post("/{document_id}/versions", response_model=DocumentVersionResponse, status_code=201)
def add_document_version(
    document_id: uuid.UUID,
    payload: DocumentVersionCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.document", "version")),
    correlation_id: str = Depends(get_correlation_id),
) -> DocumentVersionResponse:
    document = _resolve_document(db, document_id)
    assert_company_access(
        db, user_id=user.id, resource="document.document", action="version", company_id=document.company_id
    )
    current_version_number = document.current_version.version_number if document.current_version else None
    version = document_service.add_document_version(
        db,
        document_id=document_id,
        evidence_id=payload.evidence_id,
        uploaded_by=user.id,
        notes=payload.notes,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="document.document.version_add",
        entity_type="document.document_version",
        entity_id=version.id,
        company_id=document.company_id,
        project_id=document.project_id,
        before={"currentVersion": current_version_number},
        after={"versionNumber": version.version_number},
        correlation_id=correlation_id,
    )
    db.commit()
    return DocumentVersionResponse.model_validate(version, from_attributes=True)
