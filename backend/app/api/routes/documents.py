import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import (
    DocumentCreateRequest,
    DocumentResponse,
    DocumentVersionCreateRequest,
    DocumentVersionResponse,
)
from app.services import document_service
from app.services.permission_service import assert_company_access, require_permission

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
    )
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
    return [
        DocumentResponse.model_validate(d, from_attributes=True)
        for d in document_service.list_documents(db, company_id=company_id, project_id=project_id)
    ]


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
) -> DocumentVersionResponse:
    document = _resolve_document(db, document_id)
    assert_company_access(
        db, user_id=user.id, resource="document.document", action="version", company_id=document.company_id
    )
    version = document_service.add_document_version(
        db,
        document_id=document_id,
        evidence_id=payload.evidence_id,
        uploaded_by=user.id,
        notes=payload.notes,
    )
    return DocumentVersionResponse.model_validate(version, from_attributes=True)
