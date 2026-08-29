import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.domain.errors import InvalidFinancialReferenceError
from app.schemas.treasury import BankStatementLineResponse, CashClosingResponse, FundRestrictionResponse
from app.schemas.treasury_advanced import (
    BankStatementResponse,
    ReconciliationCandidateResponse,
    ReconciliationMatchResponse,
    TreasuryAvailabilityResponse,
)
from app.services import audit_service, treasury_advanced_service, treasury_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/treasury", tags=["treasury-advanced"])


def _statement_company(db: Session, statement_id: uuid.UUID) -> uuid.UUID:
    statement = treasury_service.get_bank_statement(db, bank_statement_id=statement_id)
    if statement is None:
        raise InvalidFinancialReferenceError("El estado bancario no existe")
    return treasury_service.company_id_for_bank_statement(db, statement)


def _line_company(db: Session, line_id: uuid.UUID) -> uuid.UUID:
    line = treasury_service.get_bank_statement_line(db, bank_statement_line_id=line_id)
    if line is None:
        raise InvalidFinancialReferenceError("La línea bancaria no existe")
    return treasury_service.company_id_for_bank_statement_line(db, line)


@router.get("/cash-closings", response_model=list[CashClosingResponse])
def list_cash_closings(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.cash_closing", "read")),
) -> list[CashClosingResponse]:
    assert_company_access(
        db, user_id=user.id, resource="treasury.cash_closing", action="read", company_id=company_id
    )
    return [
        CashClosingResponse.model_validate(row, from_attributes=True)
        for row in treasury_advanced_service.list_cash_closings(db, company_id=company_id)
    ]


@router.get("/bank-statements", response_model=list[BankStatementResponse])
def list_bank_statements(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "read")),
) -> list[BankStatementResponse]:
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="read",
        company_id=company_id,
    )
    return [
        BankStatementResponse.model_validate(row, from_attributes=True)
        for row in treasury_advanced_service.list_bank_statements(db, company_id=company_id)
    ]


@router.get("/bank-statements/{statement_id}/lines", response_model=list[BankStatementLineResponse])
def list_bank_statement_lines(
    statement_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "read")),
) -> list[BankStatementLineResponse]:
    company_id = _statement_company(db, statement_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="read",
        company_id=company_id,
    )
    return [
        BankStatementLineResponse.model_validate(row, from_attributes=True)
        for row in treasury_advanced_service.list_statement_lines(db, bank_statement_id=statement_id)
    ]


@router.get(
    "/bank-statement-lines/{line_id}/matches",
    response_model=list[ReconciliationMatchResponse],
)
def list_reconciliation_matches(
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "read")),
) -> list[ReconciliationMatchResponse]:
    company_id = _line_company(db, line_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="read",
        company_id=company_id,
    )
    return [
        ReconciliationMatchResponse.model_validate(row, from_attributes=True)
        for row in treasury_advanced_service.list_line_matches(db, bank_statement_line_id=line_id)
    ]


@router.get(
    "/bank-statement-lines/{line_id}/candidates",
    response_model=list[ReconciliationCandidateResponse],
)
def list_reconciliation_candidates(
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "read")),
) -> list[ReconciliationCandidateResponse]:
    company_id = _line_company(db, line_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="read",
        company_id=company_id,
    )
    line = treasury_service.get_bank_statement_line(db, bank_statement_line_id=line_id)
    if line is None:
        raise InvalidFinancialReferenceError("La línea bancaria no existe")
    return [
        ReconciliationCandidateResponse.model_validate(candidate)
        for candidate in treasury_advanced_service.reconciliation_candidates(db, line=line)
    ]


@router.post("/bank-statement-lines/{line_id}/unmatch", response_model=BankStatementLineResponse)
def unmatch_reconciliation_line(
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.bank_reconciliation", "match")),
    correlation_id: str = Depends(get_correlation_id),
) -> BankStatementLineResponse:
    company_id = _line_company(db, line_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.bank_reconciliation",
        action="match",
        company_id=company_id,
    )
    try:
        line, history = treasury_advanced_service.unmatch_line(db, line_id=line_id, commit=False)
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.bank_reconciliation.unmatch",
            entity_type="treasury.bank_statement_line",
            entity_id=line.id,
            company_id=company_id,
            before={"status": "MATCHED_OR_PARTIAL", "matches": history},
            after={"status": line.status},
            correlation_id=correlation_id,
        )
        db.commit()
        return BankStatementLineResponse.model_validate(line, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.post("/fund-restrictions/{restriction_id}/release", response_model=FundRestrictionResponse)
def release_fund_restriction(
    restriction_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.fund_restriction", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> FundRestrictionResponse:
    from app.models.treasury import FundRestriction, TreasuryAccount

    restriction = db.get(FundRestriction, restriction_id)
    if restriction is None:
        raise InvalidFinancialReferenceError("La restricción de fondos no existe")
    account = db.get(TreasuryAccount, restriction.treasury_account_id)
    if account is None:
        raise InvalidFinancialReferenceError("La cuenta de tesorería no existe")
    company_id = account.company_id
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.fund_restriction",
        action="create",
        company_id=company_id,
    )
    try:
        released = treasury_advanced_service.release_fund_restriction(
            db, restriction_id=restriction_id, commit=False
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="treasury.fund_restriction.release",
            entity_type="treasury.fund_restriction",
            entity_id=released.id,
            company_id=company_id,
            project_id=released.restricted_for_project_id,
            before={"active": True, "amount": str(released.amount)},
            after={"active": False},
            correlation_id=correlation_id,
        )
        db.commit()
        return FundRestrictionResponse.model_validate(released, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.get("/accounts/{treasury_account_id}/availability", response_model=TreasuryAvailabilityResponse)
def get_account_availability(
    treasury_account_id: uuid.UUID,
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("treasury.fund_restriction", "read")),
) -> TreasuryAvailabilityResponse:
    account = treasury_service.get_treasury_account(db, treasury_account_id=treasury_account_id)
    if account is None:
        raise InvalidFinancialReferenceError("La cuenta de tesorería no existe")
    assert_company_access(
        db,
        user_id=user.id,
        resource="treasury.fund_restriction",
        action="read",
        company_id=account.company_id,
    )
    balance, reserved, available = treasury_advanced_service.available_balance(
        db,
        treasury_account_id=treasury_account_id,
        allowed_project_id=project_id,
    )
    return TreasuryAvailabilityResponse(
        treasury_account_id=treasury_account_id,
        balance=balance,
        reserved_amount=reserved,
        available_amount=available,
    )
