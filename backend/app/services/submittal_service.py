import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.domain.errors import InvalidSubmittalStateError
from app.models.submittal import Submittal
from app.repositories import submittal_repository
from app.services import numbering_service
from app.services.financial_validation_service import (
    assert_evidence_belongs_to_company,
    assert_project_belongs_to_company,
    assert_supplier_belongs_to_company,
    assert_supplier_contract_belongs_to_company,
)

"""Submittal (bloque CONSTRUCTION CONTROL, orden maestra §80,
NXR-REQ-0086). Numeración vía numbering_service (document_type_code="SUB"),
mismo patrón company-scoped que RFI. Flujo de revisión de dos pasos: primero
`record_submittal_response` (respuesta del revisor), después `decide_submittal`
(APPROVED/REJECTED) -- decidir sin una respuesta ya registrada se rechaza
con InvalidSubmittalStateError (comportamiento de aceptación de este task,
ver tests/test_submittals.py::test_submittal_requires_response_before_approval)."""

SUBMITTAL_DECISIONS = ("APPROVED", "REJECTED")


def create_submittal(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    title: str,
    description: str | None,
    supplier_id: uuid.UUID | None,
    contract_id: uuid.UUID | None,
    submitted_by: uuid.UUID,
    submitted_at: date,
    due_date: date | None,
    evidence_id: uuid.UUID | None,
) -> Submittal:
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    if supplier_id is not None:
        assert_supplier_belongs_to_company(db, supplier_id=supplier_id, company_id=company_id)
    assert_supplier_contract_belongs_to_company(db, contract_id=contract_id, company_id=company_id)
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)

    number = numbering_service.next_document_number(
        db, company_id=company_id, document_type_code="SUB"
    )
    submittal = submittal_repository.create_submittal(
        db,
        company_id=company_id,
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        number=number,
        title=title,
        description=description,
        supplier_id=supplier_id,
        contract_id=contract_id,
        submitted_by=submitted_by,
        submitted_at=submitted_at,
        due_date=due_date,
        evidence_id=evidence_id,
    )
    db.commit()
    db.refresh(submittal)
    return submittal


def get_submittal(db: Session, submittal_id: uuid.UUID) -> Submittal | None:
    return submittal_repository.get_submittal(db, submittal_id)


def list_submittals(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[Submittal]:
    return submittal_repository.list_submittals(db, company_id=company_id, project_id=project_id)


def record_submittal_response(
    db: Session, *, submittal_id: uuid.UUID, response: str, reviewed_by: uuid.UUID
) -> Submittal:
    submittal = submittal_repository.get_submittal(db, submittal_id)
    if submittal is None:
        raise ValueError(f"Submittal {submittal_id} no existe")
    if submittal.status not in ("SUBMITTED", "UNDER_REVIEW"):
        raise InvalidSubmittalStateError(
            f"No se puede registrar respuesta sobre un Submittal {submittal.status} (decisión ya final)"
        )
    submittal.reviewer_response = response
    submittal.reviewed_by = reviewed_by
    submittal.response_recorded_at = datetime.now(timezone.utc)
    submittal.status = "UNDER_REVIEW"
    db.commit()
    db.refresh(submittal)
    return submittal


def decide_submittal(
    db: Session, *, submittal_id: uuid.UUID, decision: str, decided_by: uuid.UUID
) -> Submittal:
    if decision not in SUBMITTAL_DECISIONS:
        raise InvalidSubmittalStateError(f"decision inválida: {decision!r}")

    submittal = submittal_repository.get_submittal(db, submittal_id)
    if submittal is None:
        raise ValueError(f"Submittal {submittal_id} no existe")
    if submittal.status in ("APPROVED", "REJECTED"):
        raise InvalidSubmittalStateError(f"El Submittal ya tiene una decisión final ({submittal.status})")
    if submittal.reviewer_response is None:
        raise InvalidSubmittalStateError(
            "No se puede aprobar/rechazar un Submittal sin una respuesta de revisor registrada -- "
            "llama primero a POST /submittals/{id}/response"
        )

    submittal.status = decision
    submittal.decided_by = decided_by
    submittal.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submittal)
    return submittal


def apply_approval_decision(
    db: Session, *, submittal_id: uuid.UUID, decision: str, decided_by: uuid.UUID
) -> None:
    """Adaptador para Approval Inbox (Track G, `approval_service.decide()`)
    -- entry point nuevo, no toca la firma ni el comportamiento existente
    de `decide_submittal`. A diferencia del adaptador de AP,
    `decided_by` es un parámetro obligatorio aquí porque `decide_submittal`
    lo registra en la propia fila de Submittal (`Submittal.decided_by`);
    `approval_service.decide()` siempre lo pasa como el aprobador real de
    la ApprovalRequest. Si el Submittal todavía no tiene una respuesta de
    revisor registrada, `decide_submittal` rechaza con
    `InvalidSubmittalStateError` -- ese precondition es del dominio, no se
    relaja aquí solo porque la decisión llega vía Approval Inbox."""
    decide_submittal(db, submittal_id=submittal_id, decision=decision, decided_by=decided_by)
