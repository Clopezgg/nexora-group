import logging
import time
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.accounting import AccountingDocument
from app.models.change_order import ChangeOrder
from app.models.evidence import Evidence
from app.models.procurement import GoodsReceipt, PurchaseOrder, ServiceEntry
from app.models.progress import ProgressRecord
from app.models.project import Project
from app.models.quality import CorrectiveAction, NonConformance, QualityInspection
from app.models.rfi import RequestForInformation
from app.models.safety import SafetyIncident, SafetyObservation
from app.models.site_report import DailySiteReport
from app.models.submittal import Submittal
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

logger = logging.getLogger("nexora.evidence")

"""Evidence upload/download API (CONSTRUCTION CONTROL).

Uploads are multipart bytes backed by private Azure Blob Storage. Downloads
are authenticated streams from the private container; the API never exposes a
public Blob URL and never persists payloads to local disk.
"""

EvidenceContext = tuple[uuid.UUID, uuid.UUID | None]


def _normalized_entity_type(value: str) -> str:
    return value.strip().upper().replace("-", "_").replace(" ", "_")


def _project_context(db: Session, project_id: uuid.UUID, *, label: str) -> EvidenceContext:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"{label} no encontrado")
    return project.company_id, project.id


def _resolve_evidence_context(
    db: Session,
    *,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
    strict: bool,
) -> EvidenceContext | None:
    """Resolve polymorphic evidence context to (company_id, project_id)."""
    if entity_type is None and entity_id is None:
        return None
    if not entity_type or entity_id is None:
        if strict:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="entityType y entityId deben enviarse juntos para vincular una evidencia",
            )
        return None

    normalized = _normalized_entity_type(entity_type)

    if normalized == "PROJECT":
        return _project_context(db, entity_id, label="Proyecto de evidencia")

    if normalized in {"WBS", "WBS_NODE"}:
        node = db.get(WBSNode, entity_id)
        if node is None:
            raise HTTPException(status_code=404, detail="WBS de evidencia no encontrado")
        return _project_context(db, node.project_id, label="Proyecto del WBS")

    direct_project_models = {
        "PROGRESS": (ProgressRecord, "Avance de evidencia"),
        "PROGRESS_RECORD": (ProgressRecord, "Avance de evidencia"),
        "DAILY_REPORT": (DailySiteReport, "Diario de obra de evidencia"),
        "DAILY_SITE_REPORT": (DailySiteReport, "Diario de obra de evidencia"),
        "SITE_REPORT": (DailySiteReport, "Diario de obra de evidencia"),
        "QUALITY_INSPECTION": (QualityInspection, "Inspección de calidad de evidencia"),
        "NON_CONFORMANCE": (NonConformance, "No conformidad de evidencia"),
        "SAFETY_OBSERVATION": (SafetyObservation, "Observación de seguridad de evidencia"),
        "SAFETY_INCIDENT": (SafetyIncident, "Incidente de seguridad de evidencia"),
        "RFI": (RequestForInformation, "RFI de evidencia"),
        "SUBMITTAL": (Submittal, "Submittal de evidencia"),
        "CHANGE_ORDER": (ChangeOrder, "Orden de cambio de evidencia"),
    }
    model_and_label = direct_project_models.get(normalized)
    if model_and_label is not None:
        model, label = model_and_label
        entity = db.get(model, entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail=f"{label} no encontrado")
        return _project_context(db, entity.project_id, label="Proyecto de evidencia")

    if normalized == "CORRECTIVE_ACTION":
        action = db.get(CorrectiveAction, entity_id)
        if action is None:
            raise HTTPException(status_code=404, detail="Acción correctiva de evidencia no encontrada")
        non_conformance = db.get(NonConformance, action.non_conformance_id)
        if non_conformance is None:
            raise HTTPException(status_code=404, detail="No conformidad de la acción correctiva no encontrada")
        return _project_context(db, non_conformance.project_id, label="Proyecto de evidencia")

    if normalized in {"ACCOUNTING_DOCUMENT", "PAYMENT_DOCUMENT", "VOUCHER"}:
        # Soporte de comprobante (orden maestra Phase 2): evidencia obligatoria
        # de transferencia / depósito / cheque adjunta al documento contable.
        acc_doc = db.get(AccountingDocument, entity_id)
        if acc_doc is None:
            raise HTTPException(
                status_code=404, detail="Documento contable de evidencia no encontrado"
            )
        return acc_doc.company_id, acc_doc.project_id

    if normalized in {"PURCHASE_ORDER", "PO"}:
        order = db.get(PurchaseOrder, entity_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Orden de compra de evidencia no encontrada")
        return order.company_id, order.project_id

    if normalized in {"GOODS_RECEIPT", "RECEIPT"}:
        receipt = db.get(GoodsReceipt, entity_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Recepción de evidencia no encontrada")
        order = db.get(PurchaseOrder, receipt.purchase_order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Orden de compra de la recepción no encontrada")
        return receipt.company_id, order.project_id

    if normalized == "SERVICE_ENTRY":
        entry = db.get(ServiceEntry, entity_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entrada de servicio de evidencia no encontrada")
        order = db.get(PurchaseOrder, entry.purchase_order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Orden de compra de la entrada de servicio no encontrada")
        return entry.company_id, order.project_id

    if strict:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo de entidad de evidencia no soportado: {entity_type}",
        )
    return None


def _evidence_visible_for_projects(db: Session, evidence: Evidence, allowed: set[uuid.UUID]) -> bool:
    if evidence.entity_type is None and evidence.entity_id is None:
        return True
    context = _resolve_evidence_context(
        db,
        entity_type=evidence.entity_type,
        entity_id=evidence.entity_id,
        strict=False,
    )
    if context is None:
        return False
    _company_id, project_id = context
    return project_id is None or project_id in allowed


def _authorize_evidence_read(db: Session, *, evidence_id: uuid.UUID, user) -> Evidence:
    evidence = evidence_service.get_evidence(db, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence no encontrada")

    assert_company_access(
        db,
        user_id=user.id,
        resource="document.evidence",
        action="read",
        company_id=evidence.company_id,
    )

    allowed = accessible_project_ids(
        db, user_id=user.id, resource="document.evidence", action="read"
    )
    if allowed is not None and not _evidence_visible_for_projects(db, evidence, set(allowed)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso al contexto de proyecto de esta evidencia",
        )

    context = _resolve_evidence_context(
        db,
        entity_type=evidence.entity_type,
        entity_id=evidence.entity_id,
        strict=False,
    )
    if context is not None:
        entity_company_id, project_id = context
        if entity_company_id != evidence.company_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El contexto persistido de evidencia no pertenece a su compañía",
            )
        if project_id is not None:
            assert_project_access(
                db,
                user_id=user.id,
                resource="document.evidence",
                action="read",
                project_id=project_id,
            )
    return evidence


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
    context = _resolve_evidence_context(
        db, entity_type=entity_type, entity_id=entity_id, strict=True
    )
    project_id: uuid.UUID | None = None
    if context is not None:
        entity_company_id, project_id = context
        if entity_company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El contexto de evidencia no pertenece a la compañía seleccionada",
            )
        if project_id is not None:
            assert_project_access(
                db,
                user_id=user.id,
                resource="document.evidence",
                action="create",
                project_id=project_id,
            )
    content = await evidence_service.read_bounded_upload(file)
    declared_mime = file.content_type or "application/octet-stream"
    started = time.monotonic()
    logger.info(
        "evidence.upload.started correlationId=%s companyId=%s entityType=%s entityId=%s mime=%s size=%s",
        correlation_id,
        company_id,
        entity_type,
        entity_id,
        declared_mime,
        len(content),
    )
    evidence = None
    try:
        evidence = evidence_service.upload_evidence(
            db,
            company_id=company_id,
            uploaded_by=user.id,
            filename=file.filename or "archivo",
            mime_type=declared_mime,
            content=content,
            category=category,
            entity_type=entity_type,
            entity_id=entity_id,
            commit=False,
            correlation_id=correlation_id,
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
        logger.info(
            "evidence.upload.completed correlationId=%s companyId=%s entityType=%s entityId=%s "
            "mime=%s size=%s duration_ms=%d",
            correlation_id,
            company_id,
            entity_type,
            entity_id,
            evidence.mime_type,
            evidence.size_bytes,
            int((time.monotonic() - started) * 1000),
        )
        return EvidenceResponse.model_validate(evidence, from_attributes=True)
    except Exception as exc:
        db.rollback()
        if evidence is not None:
            evidence_service.compensate_evidence_blob(evidence.blob_key)
        logger.warning(
            "evidence.upload.failed correlationId=%s companyId=%s entityType=%s entityId=%s "
            "mime=%s size=%s duration_ms=%d error=%s",
            correlation_id,
            company_id,
            entity_type,
            entity_id,
            declared_mime,
            len(content),
            int((time.monotonic() - started) * 1000),
            type(exc).__name__,
        )
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
    requested_context = _resolve_evidence_context(
        db, entity_type=entity_type, entity_id=entity_id, strict=True
    )
    if requested_context is not None:
        entity_company_id, requested_project_id = requested_context
        if entity_company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El contexto de evidencia no pertenece a la compañía seleccionada",
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


@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "read")),
) -> StreamingResponse:
    evidence = _authorize_evidence_read(db, evidence_id=evidence_id, user=user)
    stream = evidence_service.download_evidence(evidence)
    encoded_filename = quote(evidence.original_filename, safe="")
    return StreamingResponse(
        stream,
        media_type=evidence.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Length": str(evidence.size_bytes),
            "Content-Encoding": "identity",
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{evidence_id}/render")
def render_evidence(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "read")),
) -> StreamingResponse:
    """Render mostrable de una evidencia (§28): el JPEG derivado para un HEIC,
    o el original si ya es renderizable. Inline, no attachment."""
    evidence = _authorize_evidence_read(db, evidence_id=evidence_id, user=user)
    stream = evidence_service.download_render(evidence)
    return StreamingResponse(
        stream,
        media_type=evidence_service.render_mime_type(evidence),
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("document.evidence", "read")),
) -> EvidenceResponse:
    evidence = _authorize_evidence_read(db, evidence_id=evidence_id, user=user)
    return EvidenceResponse.model_validate(evidence, from_attributes=True)
