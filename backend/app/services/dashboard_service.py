import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine
from app.models.ap import SupplierInvoice
from app.models.approval_request import ApprovalRequest
from app.models.ar import CustomerInvoice
from app.models.chart_of_accounts import Account
from app.models.treasury import TreasuryAccount
from app.repositories import project_repository
from app.schemas.dashboard import CashFlowPointResponse, DashboardSummaryResponse, ScopeAmountResponse
from app.services import fiscal_service, permission_service

BUSINESS_TZ = ZoneInfo("America/Tegucigalpa")


def _visible_companies(db: Session, *, user_id: uuid.UUID, resource: str) -> list[uuid.UUID] | None:
    if permission_service.user_has_any_company_scope(
        db, user_id=user_id, resource=resource, action="read"
    ):
        return None
    return permission_service.list_user_company_ids(db, user_id=user_id)


def _scope_for_company(
    db: Session,
    *,
    user_id: uuid.UUID,
    resource: str,
    company_id: uuid.UUID | None,
) -> list[uuid.UUID] | None:
    visible = _visible_companies(db, user_id=user_id, resource=resource)
    if company_id is None:
        return visible
    if visible is None or company_id in visible:
        return [company_id]
    return []


def _month_starts(today: date, count: int = 6) -> list[date]:
    starts: list[date] = []
    year, month = today.year, today.month
    for _ in range(count):
        starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(starts))


def _apply_company_scope(statement, column, company_ids: list[uuid.UUID] | None):
    if company_ids is None:
        return statement
    if not company_ids:
        return statement.where(False)
    return statement.where(column.in_(company_ids))


def get_summary(
    db: Session,
    *,
    user_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
) -> DashboardSummaryResponse:
    today = datetime.now(BUSINESS_TZ).date()
    month_start = date(today.year, today.month, 1)
    month_starts = _month_starts(today)

    fiscal_year = None
    fiscal_period = None
    if company_id is not None:
        fiscal_year, fiscal_period = fiscal_service.get_current_period(
            db, company_id=company_id, on_date=today
        )
    metric_start = fiscal_period.start_date if fiscal_period else month_start
    metric_end = fiscal_period.end_date if fiscal_period else today
    metric_end_exclusive = metric_end + timedelta(days=1)

    project_company_ids = _scope_for_company(
        db, user_id=user_id, resource="project", company_id=company_id
    )
    if project_company_ids is None:
        active_projects = project_repository.count_active_projects(db)
    else:
        active_projects = project_repository.count_active_projects_for_companies(
            db, company_ids=project_company_ids
        )

    can_view_financials = permission_service.user_has_permission(
        db, user_id=user_id, resource="treasury.account", action="read"
    )
    treasury_balance = Decimal("0")
    period_income = Decimal("0")
    period_expense = Decimal("0")
    cash_flow: list[CashFlowPointResponse] = []
    expenses_by_scope: list[ScopeAmountResponse] = []
    overdue_payables = 0
    overdue_payables_amount = Decimal("0")
    receivables_outstanding = Decimal("0")

    if can_view_financials:
        company_ids = _scope_for_company(
            db, user_id=user_id, resource="treasury.account", company_id=company_id
        )

        balance_stmt = (
            select(func.coalesce(func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0))
            .join(
                AccountingDocument,
                JournalLine.accounting_document_id == AccountingDocument.id,
            )
            .join(TreasuryAccount, TreasuryAccount.gl_account_id == JournalLine.account_id)
            .where(
                AccountingDocument.status == "POSTED",
                TreasuryAccount.currency_code == "HNL",
            )
        )
        balance_stmt = _apply_company_scope(balance_stmt, TreasuryAccount.company_id, company_ids)
        treasury_balance = Decimal(db.execute(balance_stmt).scalar_one())

        movement_amount = case(
            (
                Account.account_type == "REVENUE",
                JournalLine.credit_amount - JournalLine.debit_amount,
            ),
            else_=JournalLine.debit_amount - JournalLine.credit_amount,
        )

        period_stmt = (
            select(
                AccountingDocument.scope,
                Account.account_type,
                func.coalesce(func.sum(movement_amount), 0).label("amount"),
            )
            .join(
                AccountingDocument,
                JournalLine.accounting_document_id == AccountingDocument.id,
            )
            .join(Account, Account.id == JournalLine.account_id)
            .where(
                AccountingDocument.status == "POSTED",
                AccountingDocument.currency_code == "HNL",
                AccountingDocument.posted_at.is_not(None),
                AccountingDocument.posted_at >= metric_start,
                AccountingDocument.posted_at < metric_end_exclusive,
                Account.account_type.in_(("REVENUE", "EXPENSE")),
            )
            .group_by(AccountingDocument.scope, Account.account_type)
        )
        period_stmt = _apply_company_scope(period_stmt, AccountingDocument.company_id, company_ids)
        scope_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for scope, account_type, raw_amount in db.execute(period_stmt):
            amount = Decimal(raw_amount)
            if account_type == "REVENUE":
                period_income += amount
            else:
                period_expense += amount
                scope_totals[scope] += amount
        expenses_by_scope = [
            ScopeAmountResponse(scope=scope, amount=float(scope_totals.get(scope, 0)))
            for scope in ("CENTRAL", "GENERAL", "PROJECT")
            if scope_totals.get(scope, 0) != 0
        ]

        year_expr = extract("year", AccountingDocument.posted_at)
        month_expr = extract("month", AccountingDocument.posted_at)
        chart_stmt = (
            select(
                year_expr.label("year"),
                month_expr.label("month"),
                Account.account_type,
                func.coalesce(func.sum(movement_amount), 0).label("amount"),
            )
            .join(
                AccountingDocument,
                JournalLine.accounting_document_id == AccountingDocument.id,
            )
            .join(Account, Account.id == JournalLine.account_id)
            .where(
                AccountingDocument.status == "POSTED",
                AccountingDocument.currency_code == "HNL",
                AccountingDocument.posted_at.is_not(None),
                AccountingDocument.posted_at >= month_starts[0],
                Account.account_type.in_(("REVENUE", "EXPENSE")),
            )
            .group_by(year_expr, month_expr, Account.account_type)
        )
        chart_stmt = _apply_company_scope(chart_stmt, AccountingDocument.company_id, company_ids)
        monthly: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"income": Decimal("0"), "expense": Decimal("0")}
        )
        for year, month, account_type, raw_amount in db.execute(chart_stmt):
            key = f"{int(year):04d}-{int(month):02d}"
            amount = Decimal(raw_amount)
            if account_type == "REVENUE":
                monthly[key]["income"] += amount
            else:
                monthly[key]["expense"] += amount
        cash_flow = [
            CashFlowPointResponse(
                period=start.strftime("%Y-%m"),
                income=float(monthly[start.strftime("%Y-%m")]["income"]),
                expense=float(monthly[start.strftime("%Y-%m")]["expense"]),
            )
            for start in month_starts
        ]

        payable_stmt = select(
            func.count(SupplierInvoice.id),
            func.coalesce(
                func.sum(
                    SupplierInvoice.amount
                    + SupplierInvoice.tax_amount
                    - SupplierInvoice.amount_paid
                ),
                0,
            ),
        ).where(
            SupplierInvoice.currency_code == "HNL",
            SupplierInvoice.due_date < today,
            SupplierInvoice.status.in_(("REVIEW", "APPROVED", "SCHEDULED", "PARTIALLY_PAID")),
        )
        payable_stmt = _apply_company_scope(payable_stmt, SupplierInvoice.company_id, company_ids)
        overdue_payables, payable_amount = db.execute(payable_stmt).one()
        overdue_payables_amount = Decimal(payable_amount)

        receivable_stmt = select(
            func.coalesce(func.sum(CustomerInvoice.amount - CustomerInvoice.amount_collected), 0)
        ).where(
            CustomerInvoice.currency_code == "HNL",
            CustomerInvoice.status.in_(("APPROVED", "PARTIALLY_COLLECTED")),
        )
        receivable_stmt = _apply_company_scope(receivable_stmt, CustomerInvoice.company_id, company_ids)
        receivables_outstanding = Decimal(db.execute(receivable_stmt).scalar_one())

    pending_approvals = 0
    if permission_service.user_has_permission(
        db, user_id=user_id, resource="workflow.approval", action="read"
    ):
        approval_company_ids = _scope_for_company(
            db, user_id=user_id, resource="approval.request", company_id=company_id
        )
        approval_stmt = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.status == "PENDING",
            ApprovalRequest.assigned_to == user_id,
        )
        approval_stmt = _apply_company_scope(
            approval_stmt, ApprovalRequest.company_id, approval_company_ids
        )
        pending_approvals = db.execute(approval_stmt).scalar_one()

    period_label = None
    if fiscal_period is not None:
        year_code = fiscal_year.code if fiscal_year is not None else str(fiscal_period.start_date.year)
        period_label = f"{year_code} · P{fiscal_period.period_number:02d}"

    return DashboardSummaryResponse(
        treasury_balance=float(treasury_balance),
        period_income=float(period_income),
        period_expense=float(period_expense),
        active_projects=active_projects,
        pending_approvals=pending_approvals,
        overdue_payables=overdue_payables,
        overdue_payables_amount=float(overdue_payables_amount),
        receivables_outstanding=float(receivables_outstanding),
        cash_flow=cash_flow,
        expenses_by_scope=expenses_by_scope,
        fiscal_period_label=period_label,
        fiscal_period_status=fiscal_period.status if fiscal_period else None,
        fiscal_period_start=fiscal_period.start_date if fiscal_period else None,
        fiscal_period_end=fiscal_period.end_date if fiscal_period else None,
    )
