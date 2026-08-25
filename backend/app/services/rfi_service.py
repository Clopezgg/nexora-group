import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.domain.errors import InvalidRfiStateError
from app.models.rfi import RequestForInformation
from app.repositories import rfi_repository
from app.services import numbering_service
from app.services.financial_validation_service import assert_project_belongs_to_company

"""RFI (Request For Information, bloque CONSTRUCTION CONTROL, orden maestra
§80, NXR-REQ-0085). El número se genera con el servicio de numeración
concurrency-safe ya existente (numbering_service.next_document_number,
document_type_code="RFI") -- company-scoped, nunca MAX()+1, nunca una
segunda estrategia de numeración inventada para este dominio."""


def create_rfi(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    subject: str,
    question: str,
    responsible: str | None,
    requested_by: uuid.UUID,
    due_date: date | None,
) -> RequestForInformation:
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)

    number = numbering_service.next_document_number(
        db, company_id=company_id, document_type_code="RFI"
    )
    rfi = rfi_repository.create_rfi(
        db,
        company_id=company_id,
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        number=number,
        subject=subject,
        question=question,
        responsible=responsible,
        requested_by=requested_by,
        due_date=due_date,
    )
    db.commit()
    db.refresh(rfi)
    return rfi


def get_rfi(db: Session, rfi_id: uuid.UUID) -> RequestForInformation | None:
    return rfi_repository.get_rfi(db, rfi_id)


def list_rfis(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[RequestForInformation]:
    return rfi_repository.list_rfis(db, company_id=company_id, project_id=project_id)


def respond_rfi(
    db: Session, *, rfi_id: uuid.UUID, response: str, responded_by: uuid.UUID
) -> RequestForInformation:
    rfi = rfi_repository.get_rfi(db, rfi_id)
    if rfi is None:
        raise ValueError(f"RFI {rfi_id} no existe")
    if rfi.status != "OPEN":
        raise InvalidRfiStateError(
            f"Solo se puede responder un RFI en estado OPEN (actual: {rfi.status})"
        )
    rfi.response = response
    rfi.responded_by = responded_by
    rfi.responded_at = datetime.now(timezone.utc)
    rfi.status = "ANSWERED"
    db.commit()
    db.refresh(rfi)
    return rfi


def close_rfi(db: Session, *, rfi_id: uuid.UUID) -> RequestForInformation:
    rfi = rfi_repository.get_rfi(db, rfi_id)
    if rfi is None:
        raise ValueError(f"RFI {rfi_id} no existe")
    if rfi.status == "CLOSED":
        raise InvalidRfiStateError("El RFI ya está CLOSED")
    rfi.status = "CLOSED"
    rfi.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rfi)
    return rfi
