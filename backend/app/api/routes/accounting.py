import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.accounting import AccountingDocument, JournalLine
from app.schemas.accounting import (
    JournalEntryCreateRequest,
    JournalEntryReverseRequest,
    JournalEntryResponse,
    JournalLineResponse,
)
from app.services import posting_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/accounting", tags=["accounting"])


def _to_response(document: AccountingDocument, lines: list[JournalLine]) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=document.id,
        document_number=document.document_number,
        company_id=document.company_id,
        scope=document.scope,
        project_id=document.project_id,
        currency_code=document.currency_code,
        fx_rate=document.fx_rate,
        status=document.status,
        description=document.description,
        lines=[
            JournalLineResponse(
                id=line.id,
                account_id=line.account_id,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                description=line.description,
                project_id=line.project_id,
                cost_center_id=line.cost_center_id,
            )
            for line in lines
        ],
    )


def _get_lines(db: Session, document_id: uuid.UUID) -> list[JournalLine]:
    stmt = select(JournalLine).where(JournalLine.accounting_document_id == document_id)
    return list(db.execute(stmt).scalars())


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=201)
def create_journal_entry(
    payload: JournalEntryCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "create")),
) -> JournalEntryResponse:
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="create",
        company_id=payload.company_id,
    )
    lines = [
        posting_service.JournalLineInput(
            account_id=line.account_id,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            description=line.description,
            project_id=line.project_id,
            cost_center_id=line.cost_center_id,
        )
        for line in payload.lines
    ]
    document = posting_service.post_manual(
        db,
        company_id=payload.company_id,
        document_type_code="JRN",
        scope=payload.scope,
        project_id=payload.project_id,
        currency_code=payload.currency_code,
        fx_rate=payload.fx_rate,
        lines=lines,
        description=payload.description,
    )
    return _to_response(document, _get_lines(db, document.id))


@router.get("/journal-entries/{document_id}", response_model=JournalEntryResponse)
def get_journal_entry(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "read")),
) -> JournalEntryResponse:
    document = db.get(AccountingDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="read",
        company_id=document.company_id,
    )
    return _to_response(document, _get_lines(db, document.id))


@router.post("/journal-entries/{document_id}/reverse", response_model=JournalEntryResponse)
def reverse_journal_entry(
    document_id: uuid.UUID,
    payload: JournalEntryReverseRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "reverse")),
) -> JournalEntryResponse:
    document = db.get(AccountingDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="reverse",
        company_id=document.company_id,
    )
    reversal = posting_service.reverse_document(db, document_id=document_id, reason=payload.reason)
    return _to_response(reversal, _get_lines(db, reversal.id))
