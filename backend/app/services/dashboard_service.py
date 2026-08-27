import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

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
from app.services import permission_service


def _visible_companies(db: Session, *, user_id: uuid.UUID, resource: str) -> list[uuid.UUID] | None:
    if permission_service.user_has_any_company_scope(
        db, user_id=user_id, resource=resource, action="read"
    ):
        return None
    return permission_service.list_user_company_ids(db, user_id=user_id)


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


def get_summary(db: Session, *, user_id: uuid.UUID) -> DashboardSummaryResponse:
    today = datetime.now(timezone.utc).date()
    month_start = date(today.year, today.month, 1)
    month_starts = _month_starts(today)

    # The executive project count is a dashboard aggregate. It remains
    # company-scoped even for finance roles that do not have project-detail
    # permission, without granting access to project records themselves.
    project_company_ids = _visible_companies(db, user_id=user_id, resource="project")
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
        company_ids = _visible_companies(db, user_id=user_id, resource="treasury.account")

        balance_stmt = (
            select(
                func.coalesce(
                    func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0
                )
            )
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

        year_expr = extract("year", AccountingDocument.posted_at)
        month_expr = extract("month", AccountingDocument.posted_at)
        movement_amount = case(
            (
                Account.account_type == "REVENUE",
                JournalLine.credit_amount - JournalLine.debit_amount,
            ),
            else_=JournalLine.debit_amount - JournalLine.credit_amount,
        )
        movement_stmt = (
            select(
                year_expr.label("year"),
                month_expr.label("month"),
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
                AccountingDocument.posted_at >= month_starts[0],
                Account.account_type.in_(("REVENUE", "EXPENSE")),
            )
            .group_by(
                year_expr,
                month_expr,
                AccountingDocument.scope,
                Account.account_type,
            )
        )
        movement_stmt = _apply_company_scope(
            movement_stmt, AccountingDocument.company_id, company_ids
        )

        # PostgreSQL now performs the heavy aggregation. Python only receives
        # a bounded set of monthly/scope/account-type rows instead of every
        # journal line from the last six months.
        monthly: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"income": Decimal("0"), "expense": Decimal("0")}
        )
        scope_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for year, month, scope, account_type, raw_amount in db.execute(movement_stmt):
            year_value = int(year)
            month_value = int(month)
            amount = Decimal(raw_amount)
            key = f"{year_value:04d}-{month_value:02d}"
            current_month = year_value == month_start.year and month_value == month_start.month

            if account_type == "REVENUE":
                monthly[key]["income"] += amount
                if current_month:
                    period_income += amount
            else:
                monthly[key]["expense"] += amount
                if current_month:
                    period_expense += amount
                    scope_totals[scope] += amount

        cash_flow = [
            CashFlowPointResponse(
                period=start.strftime("%Y-%m"),
                income=float(monthly[start.strftime("%Y-%m")]["income"]),
                expense=float(monthly[start.strftime("%Y-%m")]["expense"]),
            )
            for start in month_starts
        ]
        expenses_by_scope = [
            ScopeAmountResponse(scope=scope, amount=float(scope_totals.get(scope, 0)))
            for scope in ("CENTRAL", "GENERAL", "PROJECT")
            if scope_totals.get(scope, 0) != 0
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
            SupplierInvoice.status.in_(
                ("REVIEW", "APPROVED", "SCHEDULED", "PARTIALLY_PAID")
            ),
        )
        payable_stmt = _apply_company_scope(payable_stmt, SupplierInvoice.company_id, company_ids)
        overdue_payables, payable_amount = db.execute(payable_stmt).one()
        overdue_payables_amount = Decimal(payable_amount)

        receivable_stmt = select(
            func.coalesce(
                func.sum(CustomerInvoice.amount - CustomerInvoice.amount_collected), 0
            )
        ).where(
            CustomerInvoice.currency_code == "HNL",
            CustomerInvoice.status.in_(("APPROVED", "PARTIALLY_COLLECTED")),
        )
        receivable_stmt = _apply_company_scope(
            receivable_stmt, CustomerInvoice.company_id, company_ids
        )
        receivables_outstanding = Decimal(db.execute(receivable_stmt).scalar_one())

    pending_approvals = 0
    if permission_service.user_has_permission(
        db, user_id=user_id, resource="workflow.approval", action="read"
    ):
        approval_company_ids = _visible_companies(
            db, user_id=user_id, resource="approval.request"
        )
        approval_stmt = select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.status == "PENDING",
            ApprovalRequest.assigned_to == user_id,
        )
        approval_stmt = _apply_company_scope(
            approval_stmt, ApprovalRequest.company_id, approval_company_ids
        )
        pending_approvals = db.execute(approval_stmt).scalar_one()

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
    )
