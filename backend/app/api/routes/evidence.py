import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.project import Project
from app.models.wbs import WBSNode
from app.schemas.document import EvidenceResponse
from app.services import audit_service, evidence_service
from app.services.permission_service import (
    accessible_project_ids,
    assert_company_access,
    assert_project_access,
    require_permission,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])

"""Evidence upload API (bloque CONSTRUCTION CONTROL, docs/DOCUMENTS_EVIDENCE.md).
multipart/form-data (no JSON): el archivo va como bytes reales, no como
base64 en un payload JSON. `evidence_service.upload_evidence` valida MIME
type y tamaño ANTES de tocar Azure Blob; si el storage no está configurado
(`EVIDENCE_BACKEND` vacío en el entorno), get_evidence_container_client
lanza EvidenceStorageNotConfigured, registrado en error_handlers.py como un
503 real (NXR-EVIDENCE-001) -- nunca un 200 con una URL fabricada."""


def _project_id_for_entity(
    db: Session, *, entity_type: str | None, entity_id: uuid.UUID | None
) -> uuid.UUID | None:
    if entity_id is None or not entity_type:
        return None
    normalized = entity_type.upper()
    if normalized == "PROJECT":
        project = db.get(Project, entity_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto de evidencia no encontrado")
        return project.id
    if normalized == "WBS":
        node = db.get(WBSNode, entity_id)
        if node is None:
            raise HTTPException(status_code=404, detail="WBS de evidencia no encontrado")
        return node.project_id
    return None


def _evidence_visible_for_projects(db: Session, evidence, allowed: set[uuid.UUID]) -> bool:
    project_id = _project_id_for_entity(
        db, entity_type=evidence.entity_type, entity_id=evidence.entity_id
    )
    return project_id is None or project_id in allowed


@router.post("", response_model=EvidenceResponse, status_code=201)
async def upload_evidence(
    company_id: uuid.UUID = Form(alias="companyId"),
    category: str | None = Form(default=None),
    entity_type: str | None = Form(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Form(default=None, alias="entityId"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> EvidenceResponse:
    assert_company_access(
        db, user_id=user.id, resource="document.evidence", action="create", company_id=company_id
    )
    project_id = _project_id_for_entity(db, entity_type=entity_type, entity_id=entity_id)
    if project_id is not None:
        project = db.get(Project, project_id)
        if project is None or project.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El contexto de evidencia no pertenece a la compañía seleccionada",
            )
        assert_project_access(
            db,
            user_id=user.id,
            resource="document.evidence",
            action="create",
            project_id=project_id,
        )
    content = await evidence_service.read_bounded_upload(file)
    evidence = None
    try:
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
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="document.evidence.upload",
            entity_type="document.evidence",
            entity_id=evidence.id,
            company_id=company_id,
            project_id=project_id,
            before=None,
            after={"originalFilename": evidence.original_filename, "sizeBytes": evidence.size_bytes},
            correlation_id=correlation_id,
        )
        db.commit()
        return EvidenceResponse.model_validate(evidence, from_attributes=True)
    except Exception:
        db.rollback()
        if evidence is not None:
            evidence_service.compensate_evidence_blob(evidence.blob_key)
        raise


@router.get("", response_model=list[EvidenceResponse])
def list_evidence(
    company_id: uuid.UUID = Query(alias="companyId"),
    entity_type: str | None = Query(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(default=None, alias="entityId"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "read")),
) -> list[EvidenceResponse]:
    assert_company_access(
        db, user_id=user.id, resource="document.evidence", action="read", company_id=company_id
    )
    requested_project_id = _project_id_for_entity(
        db, entity_type=entity_type, entity_id=entity_id
    )
    if requested_project_id is not None:
        assert_project_access(
            db,
            user_id=user.id,
            resource="document.evidence",
            action="read",
            project_id=requested_project_id,
        )
    rows = evidence_service.list_evidence(
        db,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        offset=offset,
        limit=limit,
    )
    allowed = accessible_project_ids(
        db, user_id=user.id, resource="document.evidence", action="read"
    )
    if allowed is not None:
        allowed_set = set(allowed)
        rows = [row for row in rows if _evidence_visible_for_projects(db, row, allowed_set)]
    return [EvidenceResponse.model_validate(row, from_attributes=True) for row in rows]


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
    project_id = _project_id_for_entity(
        db, entity_type=evidence.entity_type, entity_id=evidence.entity_id
    )
    if project_id is not None:
        assert_project_access(
            db,
            user_id=user.id,
            resource="document.evidence",
            action="read",
            project_id=project_id,
        )
    return EvidenceResponse.model_validate(evidence, from_attributes=True)
