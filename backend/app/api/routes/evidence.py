import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import EvidenceResponse
from app.services import evidence_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/evidence", tags=["evidence"])

"""Evidence upload API (bloque CONSTRUCTION CONTROL, docs/DOCUMENTS_EVIDENCE.md).
multipart/form-data (no JSON): el archivo va como bytes reales, no como
base64 en un payload JSON. `evidence_service.upload_evidence` valida MIME
type y tamaño ANTES de tocar Azure Blob; si el storage no está configurado
(`EVIDENCE_BACKEND` vacío en el entorno), get_evidence_container_client
lanza EvidenceStorageNotConfigured, registrado en error_handlers.py como un
503 real (NXR-EVIDENCE-001) -- nunca un 200 con una URL fabricada."""


@router.post("", response_model=EvidenceResponse, status_code=201)
async def upload_evidence(
    company_id: uuid.UUID = Form(alias="companyId"),
    category: str | None = Form(default=None),
    entity_type: str | None = Form(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Form(default=None, alias="entityId"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "create")),
) -> EvidenceResponse:
    assert_company_access(
        db, user_id=user.id, resource="document.evidence", action="create", company_id=company_id
    )
    content = await file.read()
    evidence = evidence_service.upload_evidence(
        db,
        company_id=company_id,
        uploaded_by=user.id,
        filename=file.filename or "archivo",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
        category=category,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return EvidenceResponse.model_validate(evidence, from_attributes=True)


@router.get("", response_model=list[EvidenceResponse])
def list_evidence(
    company_id: uuid.UUID = Query(alias="companyId"),
    entity_type: str | None = Query(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(default=None, alias="entityId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "read")),
) -> list[EvidenceResponse]:
    assert_company_access(
        db, user_id=user.id, resource="document.evidence", action="read", company_id=company_id
    )
    return [
        EvidenceResponse.model_validate(e, from_attributes=True)
        for e in evidence_service.list_evidence(
            db, company_id=company_id, entity_type=entity_type, entity_id=entity_id
        )
    ]


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "read")),
) -> EvidenceResponse:
    evidence = evidence_service.get_evidence(db, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence no encontrada")
    assert_company_access(
        db, user_id=user.id, resource="document.evidence", action="read", company_id=evidence.company_id
    )
    return EvidenceResponse.model_validate(evidence, from_attributes=True)
