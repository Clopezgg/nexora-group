import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.accounting import AccountingDocument, JournalLine
from app.schemas.accounting import (
    JournalEntryCreateRequest,
    JournalEntryReverseRequest,
    JournalEntryResponse,
    JournalLineResponse,
)
from app.schemas.reconciliation import (
    ReconciliationLineResponse,
    SubledgerGlReconciliationResponse,
)
from app.services import audit_service, posting_service, subledger_reconciliation_service
from app.services.permission_service import (
    accessible_project_ids,
    assert_company_access,
    assert_project_access,
    require_permission,
)

router = APIRouter(prefix="/accounting", tags=["accounting"])


def _to_response(document: AccountingDocument, lines: list[JournalLine]) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=document.id,
        document_number=document.document_number,
        document_type_code=document.document_type_code,
        company_id=document.company_id,
        scope=document.scope,
        project_id=document.project_id,
        currency_code=document.currency_code,
        fx_rate=document.fx_rate,
        status=document.status,
        description=document.description,
        effective_date=document.effective_date,
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


def _assert_document_project_access(
    db: Session,
    *,
    user_id: uuid.UUID,
    resource: str,
    action: str,
    document: AccountingDocument,
    lines: list[JournalLine] | None = None,
) -> None:
    project_ids = {document.project_id} if document.project_id is not None else set()
    for line in lines if lines is not None else _get_lines(db, document.id):
        if line.project_id is not None:
            project_ids.add(line.project_id)
    for project_id in project_ids:
        assert_project_access(
            db,
            user_id=user_id,
            resource=resource,
            action=action,
            project_id=project_id,
        )


def _project_scoped_document_query(
    db: Session,
    *,
    user_id: uuid.UUID,
    resource: str,
    action: str,
):
    allowed = accessible_project_ids(
        db,
        user_id=user_id,
        resource=resource,
        action=action,
    )
    if allowed is None:
        return None

    unauthorized_line = exists(
        select(JournalLine.id).where(
            JournalLine.accounting_document_id == AccountingDocument.id,
            JournalLine.project_id.is_not(None),
            JournalLine.project_id.not_in(allowed),
        )
    )
    return and_(
        or_(
            AccountingDocument.project_id.is_(None),
            AccountingDocument.project_id.in_(allowed),
        ),
        ~unauthorized_line,
    )


@router.get("/journal-entries", response_model=list[JournalEntryResponse])
def list_journal_entries(
    company_id: uuid.UUID = Query(alias="companyId"),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "read")),
) -> list[JournalEntryResponse]:
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="read",
        company_id=company_id,
    )
    stmt = select(AccountingDocument).where(AccountingDocument.company_id == company_id)
    project_filter = _project_scoped_document_query(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="read",
    )
    if project_filter is not None:
        stmt = stmt.where(project_filter)
    if status_filter:
        stmt = stmt.where(AccountingDocument.status == status_filter.upper())
    stmt = stmt.order_by(
        AccountingDocument.posted_at.desc(), AccountingDocument.created_at.desc()
    ).limit(limit)
    documents = list(db.execute(stmt).scalars())
    return [_to_response(document, _get_lines(db, document.id)) for document in documents]


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=201)
def create_journal_entry(
    payload: JournalEntryCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "create")),
    correlation_id: str = Depends(get_correlation_id),
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
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="accounting.journal_entry.create",
        entity_type="accounting.journal_entry",
        entity_id=document.id,
        company_id=document.company_id,
        project_id=document.project_id,
        before=None,
        after={"status": document.status, "documentNumber": document.document_number},
        correlation_id=correlation_id,
    )
    db.commit()
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
    lines = _get_lines(db, document.id)
    _assert_document_project_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="read",
        document=document,
        lines=lines,
    )
    return _to_response(document, lines)


@router.post("/journal-entries/{document_id}/reverse", response_model=JournalEntryResponse)
def reverse_journal_entry(
    document_id: uuid.UUID,
    payload: JournalEntryReverseRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "reverse")),
    correlation_id: str = Depends(get_correlation_id),
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
    _assert_document_project_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="reverse",
        document=document,
    )
    before_status = document.status
    reversal = posting_service.reverse_document(
        db,
        document_id=document_id,
        reason=payload.reason,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="accounting.journal_entry.reverse",
        entity_type="accounting.journal_entry",
        entity_id=document.id,
        company_id=document.company_id,
        project_id=document.project_id,
        before={"status": before_status},
        after={"status": document.status, "reversalDocumentId": str(reversal.id)},
        correlation_id=correlation_id,
    )
    db.commit()
    return _to_response(reversal, _get_lines(db, reversal.id))


@router.get(
    "/reconciliation/subledger-gl",
    response_model=SubledgerGlReconciliationResponse,
)
def subledger_gl_reconciliation(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.reconciliation", "read")),
) -> SubledgerGlReconciliationResponse:
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.reconciliation",
        action="read",
        company_id=company_id,
    )
    lines = subledger_reconciliation_service.reconcile(db, company_id=company_id)
    return SubledgerGlReconciliationResponse(
        all_reconciled=all(line.reconciled for line in lines),
        lines=[
            ReconciliationLineResponse(
                subledger=line.subledger,
                subledger_total=line.subledger_total,
                gl_total=line.gl_total,
                difference=line.difference,
                reconciled=line.reconciled,
                detail=line.detail,
            )
            for line in lines
        ],
    )


@router.get(
    "/journal-entries/{document_id}/inspect",
    response_model=None,
)
def inspect_journal_entry(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "read")),
):
    from app.schemas.transaction_inspector import (
        InspectedLineResponse,
        InspectionResponse,
        SourceEventResponse,
    )
    from app.services import transaction_inspector_service

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
    _assert_document_project_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="read",
        document=document,
    )
    result = transaction_inspector_service.inspect(db, document_id=document_id)
    assert result is not None
    return InspectionResponse(
        document_id=uuid.UUID(result.document_id),
        document_number=result.document_number,
        document_type_code=result.document_type_code,
        scope=result.scope,
        status=result.status,
        currency_code=result.currency_code,
        description=result.description,
        project_name=result.project_name,
        posted_at=result.posted_at,
        total_debit=result.total_debit,
        total_credit=result.total_credit,
        balanced=result.balanced,
        source_event=SourceEventResponse(
            kind=result.source_event.kind,
            label=result.source_event.label,
            reference=result.source_event.reference,
            entity_id=result.source_event.entity_id,
        ),
        lines=[
            InspectedLineResponse(
                account_code=line.account_code,
                account_name=line.account_name,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
                project_name=line.project_name,
                cost_center_name=line.cost_center_name,
            )
            for line in result.lines
        ],
        reverses_document_id=(
            uuid.UUID(result.reverses_document_id) if result.reverses_document_id else None
        ),
        reversal_reason=result.reversal_reason,
        reversed_by_document_ids=[uuid.UUID(x) for x in result.reversed_by_document_ids],
        evidence=result.evidence,
        contract=result.contract,
    )
