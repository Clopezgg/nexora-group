import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import project_repository
from app.schemas.reporting import (
    BalanceSheetReportResponse,
    BudgetVsActualReportResponse,
    CashFlowReportResponse,
    GeneralLedgerReportResponse,
    GeneralLedgerRowResponse,
    IncomeStatementReportResponse,
    StatementRowResponse,
    SupplierPerformanceRowResponse,
    TrialBalanceReportResponse,
    TrialBalanceRowResponse,
)
from app.services import reporting_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/reports", tags=["reports"])


def _assert_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="dateFrom no puede ser posterior a dateTo")


def _statement_row(row) -> StatementRowResponse:
    return StatementRowResponse(
        account_id=row.account_id,
        account_code=row.account_code,
        account_name=row.account_name,
        account_type=row.account_type,
        balance=row.balance,
    )


@router.get("/trial-balance", response_model=TrialBalanceReportResponse)
def get_trial_balance(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.trial_balance", "read")),
) -> TrialBalanceReportResponse:
    assert_company_access(
        db, user_id=user.id, resource="reports.trial_balance", action="read", company_id=company_id
    )
    report = reporting_service.trial_balance(db, company_id=company_id)
    return TrialBalanceReportResponse(
        rows=[
            TrialBalanceRowResponse(
                account_code=row.account_code,
                account_name=row.account_name,
                debit_balance=row.debit_balance,
                credit_balance=row.credit_balance,
            )
            for row in report.rows
        ],
        total_debit=report.total_debit,
        total_credit=report.total_credit,
    )


@router.get("/budget-vs-actual", response_model=BudgetVsActualReportResponse)
def get_budget_vs_actual(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.budget_vs_actual", "read")),
) -> BudgetVsActualReportResponse:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    assert_company_access(
        db,
        user_id=user.id,
        resource="reports.budget_vs_actual",
        action="read",
        company_id=project.company_id,
    )
    report = reporting_service.budget_vs_actual(db, project_id=project_id)
    return BudgetVsActualReportResponse(
        authorized=report.authorized,
        committed=report.committed,
        accrued=report.accrued,
        paid=report.paid,
        available=report.available,
    )


@router.get("/balance-sheet", response_model=BalanceSheetReportResponse)
def get_balance_sheet(
    company_id: uuid.UUID = Query(alias="companyId"),
    as_of: date | None = Query(default=None, alias="asOf"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.balance_sheet", "read")),
) -> BalanceSheetReportResponse:
    assert_company_access(
        db, user_id=user.id, resource="reports.balance_sheet", action="read", company_id=company_id
    )
    report = reporting_service.balance_sheet(db, company_id=company_id, as_of=as_of)
    return BalanceSheetReportResponse(
        assets=[_statement_row(row) for row in report.assets],
        liabilities=[_statement_row(row) for row in report.liabilities],
        equity=[_statement_row(row) for row in report.equity],
        total_assets=report.total_assets,
        total_liabilities=report.total_liabilities,
        total_equity=report.total_equity,
        current_earnings=report.current_earnings,
        total_equity_including_earnings=report.total_equity_including_earnings,
        total_liabilities_and_equity=report.total_liabilities_and_equity,
        equation_delta=report.equation_delta,
    )


@router.get("/income-statement", response_model=IncomeStatementReportResponse)
def get_income_statement(
    company_id: uuid.UUID = Query(alias="companyId"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.income_statement", "read")),
) -> IncomeStatementReportResponse:
    assert_company_access(
        db,
        user_id=user.id,
        resource="reports.income_statement",
        action="read",
        company_id=company_id,
    )
    _assert_date_range(date_from, date_to)
    report = reporting_service.income_statement(
        db, company_id=company_id, date_from=date_from, date_to=date_to
    )
    return IncomeStatementReportResponse(
        revenue=[_statement_row(row) for row in report.revenue],
        expenses=[_statement_row(row) for row in report.expenses],
        total_revenue=report.total_revenue,
        total_expenses=report.total_expenses,
        net_income=report.net_income,
    )


@router.get("/cash-flow", response_model=CashFlowReportResponse)
def get_cash_flow(
    company_id: uuid.UUID = Query(alias="companyId"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.cash_flow", "read")),
) -> CashFlowReportResponse:
    assert_company_access(
        db, user_id=user.id, resource="reports.cash_flow", action="read", company_id=company_id
    )
    _assert_date_range(date_from, date_to)
    report = reporting_service.cash_flow_statement(
        db, company_id=company_id, date_from=date_from, date_to=date_to
    )
    return CashFlowReportResponse(
        operating=[_statement_row(row) for row in report.operating],
        investing=[_statement_row(row) for row in report.investing],
        financing=[_statement_row(row) for row in report.financing],
        unclassified=[_statement_row(row) for row in report.unclassified],
        total_operating=report.total_operating,
        total_investing=report.total_investing,
        total_financing=report.total_financing,
        total_unclassified=report.total_unclassified,
        net_change_in_cash=report.net_change_in_cash,
    )


@router.get("/general-ledger", response_model=GeneralLedgerReportResponse)
def get_general_ledger(
    company_id: uuid.UUID = Query(alias="companyId"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    account_id: uuid.UUID | None = Query(default=None, alias="accountId"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.general_ledger", "read")),
) -> GeneralLedgerReportResponse:
    assert_company_access(
        db, user_id=user.id, resource="reports.general_ledger", action="read", company_id=company_id
    )
    _assert_date_range(date_from, date_to)
    if account_id is not None:
        account = reporting_service.resolve_account_for_company(
            db, account_id=account_id, company_id=company_id
        )
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    report = reporting_service.general_ledger(
        db,
        company_id=company_id,
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        offset=offset,
        limit=limit,
    )
    return GeneralLedgerReportResponse(
        rows=[
            GeneralLedgerRowResponse(
                line_id=row.line_id,
                document_id=row.document_id,
                document_number=row.document_number,
                posted_at=row.posted_at,
                document_status=row.document_status,
                account_id=row.account_id,
                account_code=row.account_code,
                account_name=row.account_name,
                account_type=row.account_type,
                scope=row.scope,
                project_id=row.project_id,
                description=row.description,
                debit_amount=row.debit_amount,
                credit_amount=row.credit_amount,
            )
            for row in report.rows
        ],
        total=report.total,
        offset=report.offset,
        limit=report.limit,
        total_debit=report.total_debit,
        total_credit=report.total_credit,
    )


@router.get("/supplier-performance", response_model=list[SupplierPerformanceRowResponse])
def get_supplier_performance(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.supplier_performance", "read")),
) -> list[SupplierPerformanceRowResponse]:
    assert_company_access(
        db, user_id=user.id, resource="reports.supplier_performance", action="read", company_id=company_id
    )
    rows = reporting_service.supplier_performance(db, company_id=company_id)
    return [
        SupplierPerformanceRowResponse(
            supplier_id=row.supplier_id,
            supplier_legal_name=row.supplier_legal_name,
            purchase_order_count=row.purchase_order_count,
            on_time_delivery_rate=row.on_time_delivery_rate,
            on_time_delivery_sample_size=row.on_time_delivery_sample_size,
            three_way_match_clean_rate=row.three_way_match_clean_rate,
            three_way_match_sample_size=row.three_way_match_sample_size,
            price_variance_pct=row.price_variance_pct,
            price_variance_sample_size=row.price_variance_sample_size,
        )
        for row in rows
    ]
