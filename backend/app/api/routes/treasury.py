import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.api.deps_correlation import get_correlation_id
from app.domain.errors import InvalidFinancialReferenceError
from app.models.accounting import AccountingDocument
from app.models.treasury import (
    BankStatementLine,
    FundRestriction,
    Remittance,
    TreasuryAccount,
)
from app.schemas.treasury import (
    BankStatementCreateRequest,
    BankStatementLineCreateRequest,
    BankStatementLineResponse,
    CashClosingApproveRequest,
    CashClosingCreateRequest,
    CashClosingResponse,
    FundRestrictionCreateRequest,
    FundRestrictionResponse,
    GeneralExpenseCreateRequest,
    GeneralExpenseResponse,
    ReconciliationMatchRequest,
    RemittanceCreateRequest,
    RemittanceResponse,
    TreasuryAccountCreateRequest,
    TreasuryAccountResponse,
    TreasuryTransferCreateRequest,
    TreasuryTransferResponse,
)
from app.services import audit_service, idempotency_service, treasury_service, voucher_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/treasury", tags=["treasury"])


def _resolve_treasury_account(db: Session, account_id: uuid.UUID) -> TreasuryAccount:
    account = treasury_service.get_treasury_account(db, treasury_account_id=account_id)
    if account is None:
        raise InvalidFinancialReferenceError(f"TreasuryAccount {account_id} no existe")
    return account


def _resolve_statement(db: Session, statement_id: uuid.UUID):
    statement = treasury_service.get_bank_statement(db, bank_statement_id=statement_id)
    if statement is None:
        raise InvalidFinancialReferenceError(f"BankStatement {statement_id} no existe")
    return statement


def _resolve_statement_line(db: Session, line_id: uuid.UUID) -> BankStatementLine:
    line = treasury_service.get_bank_statement_line(db, bank_statement_line_id=line_id)
    if line is None:
        raise InvalidFinancialReferenceError(f"BankStatementLine {line_id} no existe")
    return line


def _account_to_response(db: Session, account: TreasuryAccount) -> TreasuryAccountResponse:
    balance = treasury_service.treasury_account_balance(db, account)
    return TreasuryAccountResponse(
        id=account.id,
        company_id=account.company_id,
        name=account.name,
        kind=account.kind,
        institution=account.institution,
        account_reference=account.account_reference,
        currency_code=account.currency_code,
        gl_account_id=account.gl_account_id,
        status=account.status,
        balance=balance,
    )


@router.post("/accounts", response_model=TreasuryAccountResponse, status_code=201)
def create_account(
    payload: TreasuryAccountCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.account", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> TreasuryAccountResponse:
    assert_company_access(
        db, user_id=user.id, resource="treasury.account", action="create", company_id=payload.company_id
    )
    account = treasury_service.create_treasury_account(
        db,
        company_id=payload.company_id,
        name=payload.name,
        kind=payload.kind,
        institution=payload.institution,
        account_reference=payload.account_reference,
        currency_code=payload.currency_code,
        gl_account_id=payload.gl_account_id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="treasury.account.create",
        entity_type="treasury.account",
        entity_id=account.id,
        company_id=account.company_id,
        before=None,
        after={
            "name": account.name,
            "kind": account.kind,
            "currencyCode": account.currency_code,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return _account_to_response(db, account)


@router.get("/accounts", response_model=list[TreasuryAccountResponse])
def list_accounts(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.account", "read")),
) -> list[TreasuryAccountResponse]:
    assert_company_access(
        db, user_id=user.id, resource="treasury.account", action="read", company_id=company_id
    )
    accounts = (
        db.query(TreasuryAccount).filter(TreasuryAccount.company_id == company_id).all()
    )
    return [_account_to_response(db, account) for account in accounts]


@router.get("/remittances", response_model=list[RemittanceResponse])
def list_remittances(
    company_id: uuid.UUID = Query(alias="companyId"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.remittance", "read")),
) -> list[RemittanceResponse]:
    assert_company_access(
        db, user_id=user.id, resource="treasury.remittance", action="read", company_id=company_id
    )
    rows = (
        db.query(Remittance)
        .filter(Remittance.company_id == company_id)
        .order_by(Remittance.remittance_date.desc(), Remittance.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [RemittanceResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/remittances", response_model=RemittanceResponse, status_code=201)
def create_remittance(
    payload: RemittanceCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.remittance", "create")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str = Depends(get_correlation_id),
) -> RemittanceResponse:
    assert_company_access(
        db, user_id=user.id, resource="treasury.remittance", action="create", company_id=payload.company_id
    )
    request_payload = payload.model_dump(mode="json")

    outcome = None
    if idempotency_key:
        outcome = idempotency_service.begin(
            db, key=idempotency_key, command="treasury.remittance.create", payload=request_payload
        )
        if outcome.is_replay:
            return RemittanceResponse.model_validate(outcome.record.result)

    try:
        remittance = treasury_service.register_remittance(
            db,
            company_id=payload.company_id,
            treasury_account_id=payload.treasury_account_id,
            counter_account_id=payload.counter_account_id,
            origin_type=payload.origin_type,
            sender=payload.sender,
            provider=payload.provider,
            channel=payload.channel,
            currency_code=payload.currency_code,
            original_amount=payload.original_amount,
            fx_rate=payload.fx_rate,
            reference=payload.reference,
            remittance_date=payload.remittance_date,
            notes=payload.notes,
            commit=outcome is None,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.remittance.create",
            entity_type="treasury.remittance",
            entity_id=remittance.id,
            company_id=remittance.company_id,
            before=None,
            after={
                "baseAmount": str(remittance.base_amount),
                "sender": remittance.sender,
                "originType": payload.origin_type,
            },
            correlation_id=correlation_id,
        )
        response = RemittanceResponse.model_validate(remittance, from_attributes=True)
        if outcome is not None:
            idempotency_service.complete(
                db,
                outcome.record,
                result=response.model_dump(mode="json"),
                entity_type="Remittance",
                entity_id=remittance.id,
            )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.post("/general-expenses", response_model=GeneralExpenseResponse, status_code=201)
def create_general_expense(
    payload: GeneralExpenseCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.general_expense", "create")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str = Depends(get_correlation_id),
) -> GeneralExpenseResponse:
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.general_expense",
        action="create",
        company_id=payload.company_id,
    )
    outcome = None
    try:
        if idempotency_key:
            outcome = idempotency_service.begin(
                db,
                key=idempotency_key,
                command="treasury.general_expense.create",
                payload=payload.model_dump(mode="json"),
            )
            if outcome.is_replay:
                return GeneralExpenseResponse.model_validate(outcome.record.result)
        expense = treasury_service.register_general_expense(
            db,
            company_id=payload.company_id,
            treasury_account_id=payload.treasury_account_id,
            expense_account_id=payload.expense_account_id,
            scope=payload.scope,
            project_id=payload.project_id,
            category=payload.category,
            amount=payload.amount,
            currency_code=payload.currency_code,
            expense_date=payload.expense_date,
            description=payload.description,
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.general_expense.create",
            entity_type="treasury.general_expense",
            entity_id=expense.id,
            company_id=expense.company_id,
            before=None,
            after={
                "amount": str(expense.amount),
                "category": expense.category,
                "scope": payload.scope,
                "projectId": str(payload.project_id) if payload.project_id else None,
            },
            correlation_id=correlation_id,
        )
        response = GeneralExpenseResponse.model_validate(expense, from_attributes=True)
        if outcome is not None:
            idempotency_service.complete(
                db,
                outcome.record,
                result=response.model_dump(mode="json"),
                entity_type="GeneralExpense",
                entity_id=expense.id,
            )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.post("/transfers", response_model=TreasuryTransferResponse, status_code=201)
def create_transfer(
    payload: TreasuryTransferCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.transfer", "create")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str = Depends(get_correlation_id),
) -> TreasuryTransferResponse:
    assert_company_access(
        db, user_id=user.id, resource="treasury.transfer", action="create", company_id=payload.company_id
    )
    request_payload = payload.model_dump(mode="json")

    outcome = None
    if idempotency_key:
        outcome = idempotency_service.begin(
            db, key=idempotency_key, command="treasury.transfer.create", payload=request_payload
        )
        if outcome.is_replay:
            return TreasuryTransferResponse.model_validate(outcome.record.result)

    try:
        transfer = treasury_service.register_transfer(
            db,
            company_id=payload.company_id,
            source_treasury_account_id=payload.source_treasury_account_id,
            destination_treasury_account_id=payload.destination_treasury_account_id,
            amount=payload.amount,
            currency_code=payload.currency_code,
            transfer_date=payload.transfer_date,
            notes=payload.notes,
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.transfer.create",
            entity_type="treasury.transfer",
            entity_id=transfer.id,
            company_id=transfer.company_id,
            before=None,
            after={
                "amount": str(transfer.amount),
                "sourceTreasuryAccountId": str(transfer.source_treasury_account_id),
                "destinationTreasuryAccountId": str(transfer.destination_treasury_account_id),
            },
            correlation_id=correlation_id,
        )
        response = TreasuryTransferResponse.model_validate(transfer, from_attributes=True)
        if outcome is not None:
            idempotency_service.complete(
                db,
                outcome.record,
                result=response.model_dump(mode="json"),
                entity_type="TreasuryTransfer",
                entity_id=transfer.id,
            )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.post("/cash-closings", response_model=CashClosingResponse, status_code=201)
def create_cash_closing(
    payload: CashClosingCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.cash_closing", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> CashClosingResponse:
    account = _resolve_treasury_account(db, payload.treasury_account_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.cash_closing",
        action="create",
        company_id=account.company_id,
    )
    closing = treasury_service.create_cash_closing(
        db,
        treasury_account_id=payload.treasury_account_id,
        closing_date=payload.closing_date,
        opening_amount=payload.opening_amount,
        expected_amount=payload.expected_amount,
        counted_amount=payload.counted_amount,
        responsible_user_id=user.id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="treasury.cash_closing.create",
        entity_type="treasury.cash_closing",
        entity_id=closing.id,
        company_id=account.company_id,
        before=None,
        after={
            "closingDate": str(closing.closing_date),
            "openingAmount": str(closing.opening_amount),
            "expectedAmount": str(closing.expected_amount),
            "countedAmount": str(closing.counted_amount),
            "differenceAmount": str(closing.difference_amount),
            "status": closing.status,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return CashClosingResponse.model_validate(closing, from_attributes=True)


@router.post("/cash-closings/{cash_closing_id}/approve", response_model=CashClosingResponse)
def approve_cash_closing(
    cash_closing_id: uuid.UUID,
    payload: CashClosingApproveRequest,
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.cash_closing", "approve")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str = Depends(get_correlation_id),
) -> CashClosingResponse:
    existing_closing = treasury_service.get_cash_closing(
        db, cash_closing_id=cash_closing_id
    )
    if existing_closing is None:
        raise InvalidFinancialReferenceError(f"CashClosing {cash_closing_id} no existe")
    account = _resolve_treasury_account(db, existing_closing.treasury_account_id)
    if account.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "companyId no coincide con la compañía propietaria del cierre"
        )
    assert_company_access(
        db, user_id=user.id, resource="treasury.cash_closing", action="approve", company_id=company_id
    )
    before_status = existing_closing.status
    outcome = None
    request_payload = {
        "cashClosingId": str(cash_closing_id),
        "companyId": str(company_id),
        **payload.model_dump(mode="json"),
    }
    try:
        if idempotency_key:
            outcome = idempotency_service.begin(
                db,
                key=idempotency_key,
                command="treasury.cash_closing.approve",
                payload=request_payload,
            )
            if outcome.is_replay:
                return CashClosingResponse.model_validate(outcome.record.result)
        closing = treasury_service.approve_cash_closing(
            db,
            cash_closing_id=cash_closing_id,
            approved_by_user_id=user.id,
            difference_account_id=payload.difference_account_id,
            company_id=company_id,
            commit=outcome is None,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.cash_closing.approve",
            entity_type="treasury.cash_closing",
            entity_id=closing.id,
            company_id=company_id,
            before={"status": before_status},
            after={"status": closing.status},
            correlation_id=correlation_id,
        )
        response = CashClosingResponse.model_validate(closing, from_attributes=True)
        if outcome is not None:
            idempotency_service.complete(
                db,
                outcome.record,
                result=response.model_dump(mode="json"),
                entity_type="CashClosing",
                entity_id=closing.id,
            )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.post("/bank-statements", status_code=201)
def create_bank_statement(
    payload: BankStatementCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> dict:
    account = _resolve_treasury_account(db, payload.treasury_account_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="create",
        company_id=account.company_id,
    )
    statement = treasury_service.create_bank_statement(
        db,
        treasury_account_id=payload.treasury_account_id,
        statement_date=payload.statement_date,
        opening_balance=payload.opening_balance,
        closing_balance=payload.closing_balance,
        reference=payload.reference,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="treasury.bank_statement.create",
        entity_type="treasury.bank_statement",
        entity_id=statement.id,
        company_id=account.company_id,
        before=None,
        after={
            "statementDate": str(statement.statement_date),
            "openingBalance": str(statement.opening_balance),
            "closingBalance": str(statement.closing_balance),
            "reference": statement.reference,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return {"id": str(statement.id)}


@router.post(
    "/bank-statements/{bank_statement_id}/lines",
    response_model=BankStatementLineResponse,
    status_code=201,
)
def add_bank_statement_line(
    bank_statement_id: uuid.UUID,
    payload: BankStatementLineCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> BankStatementLineResponse:
    statement = _resolve_statement(db, bank_statement_id)
    company_id = treasury_service.company_id_for_bank_statement(db, statement)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="create",
        company_id=company_id,
    )
    line = treasury_service.add_bank_statement_line(
        db,
        bank_statement_id=bank_statement_id,
        line_date=payload.line_date,
        description=payload.description,
        amount=payload.amount,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="treasury.bank_statement_line.create",
        entity_type="treasury.bank_statement_line",
        entity_id=line.id,
        company_id=company_id,
        before=None,
        after={
            "lineDate": str(line.line_date),
            "description": line.description,
            "amount": str(line.amount),
            "status": line.status,
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return BankStatementLineResponse.model_validate(line, from_attributes=True)


@router.post("/bank-statement-lines/{line_id}/match", response_model=BankStatementLineResponse)
def match_line(
    line_id: uuid.UUID,
    payload: ReconciliationMatchRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "match")),
    correlation_id: str = Depends(get_correlation_id),
) -> BankStatementLineResponse:
    line = _resolve_statement_line(db, line_id)
    company_id = treasury_service.company_id_for_bank_statement_line(db, line)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="match",
        company_id=company_id,
    )
    before_status = line.status
    try:
        match = treasury_service.match_reconciliation_line(
            db,
            bank_statement_line_id=line_id,
            accounting_document_id=payload.accounting_document_id,
            matched_amount=payload.matched_amount,
            matched_by_user_id=user.id,
            commit=False,
        )
        line = _resolve_statement_line(db, line_id)
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.bank_reconciliation.match",
            entity_type="treasury.bank_statement_line",
            entity_id=line.id,
            company_id=company_id,
            before={"status": before_status},
            after={
                "status": line.status,
                "matchedAmount": str(payload.matched_amount),
                "accountingDocumentId": str(match.accounting_document_id),
                "reconciliationMatchId": str(match.id),
            },
            correlation_id=correlation_id,
        )
        db.commit()
        return BankStatementLineResponse.model_validate(line, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.post("/bank-statement-lines/{line_id}/exclude", response_model=BankStatementLineResponse)
def exclude_line(
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "match")),
    correlation_id: str = Depends(get_correlation_id),
) -> BankStatementLineResponse:
    line = _resolve_statement_line(db, line_id)
    company_id = treasury_service.company_id_for_bank_statement_line(db, line)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="match",
        company_id=company_id,
    )
    before_status = line.status
    try:
        line = treasury_service.exclude_reconciliation_line(
            db, bank_statement_line_id=line_id, commit=False
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.bank_reconciliation.exclude",
            entity_type="treasury.bank_statement_line",
            entity_id=line.id,
            company_id=company_id,
            before={"status": before_status},
            after={"status": line.status},
            correlation_id=correlation_id,
        )
        db.commit()
        return BankStatementLineResponse.model_validate(line, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.post("/fund-restrictions", response_model=FundRestrictionResponse, status_code=201)
def create_fund_restriction(
    payload: FundRestrictionCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.fund_restriction", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> FundRestrictionResponse:
    account = _resolve_treasury_account(db, payload.treasury_account_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.fund_restriction",
        action="create",
        company_id=account.company_id,
    )
    try:
        restriction = treasury_service.create_fund_restriction(
            db,
            treasury_account_id=payload.treasury_account_id,
            restricted_for_project_id=payload.restricted_for_project_id,
            amount=payload.amount,
            description=payload.description,
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.fund_restriction.create",
            entity_type="treasury.fund_restriction",
            entity_id=restriction.id,
            company_id=account.company_id,
            project_id=restriction.restricted_for_project_id,
            before=None,
            after={"amount": str(restriction.amount)},
            correlation_id=correlation_id,
        )
        db.commit()
        return FundRestrictionResponse.model_validate(restriction, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.get("/fund-restrictions", response_model=list[FundRestrictionResponse])
def list_fund_restrictions(
    treasury_account_id: uuid.UUID = Query(alias="treasuryAccountId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.fund_restriction", "read")),
) -> list[FundRestrictionResponse]:
    account = _resolve_treasury_account(db, treasury_account_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.fund_restriction",
        action="read",
        company_id=account.company_id,
    )
    restrictions = (
        db.query(FundRestriction)
        .filter(FundRestriction.treasury_account_id == treasury_account_id)
        .all()
    )
    return [FundRestrictionResponse.model_validate(r, from_attributes=True) for r in restrictions]


@router.get("/vouchers/{accounting_document_id}")
def download_voucher(
    accounting_document_id: uuid.UUID,
    beneficiary: str,
    payer: str,
    payment_method: str = Query(alias="paymentMethod"),
    approved_by: str | None = Query(default=None, alias="approvedBy"),
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    user=Depends(require_permission("treasury.voucher", "read")),
) -> Response:
    document = db.get(AccountingDocument, accounting_document_id)
    if document is None:
        raise InvalidFinancialReferenceError(
            f"AccountingDocument {accounting_document_id} no existe"
        )
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.voucher",
        action="read",
        company_id=document.company_id,
    )
    try:
        pdf_bytes = voucher_service.generate_voucher_pdf(
            db,
            accounting_document_id=accounting_document_id,
            prepared_by=str(user_id),
            approved_by=approved_by,
            beneficiary=beneficiary,
            payer=payer,
            payment_method=payment_method,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return Response(content=pdf_bytes, media_type="application/pdf")
