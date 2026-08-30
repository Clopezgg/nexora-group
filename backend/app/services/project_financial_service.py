import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import LEDGER_EFFECTIVE_STATUSES, AccountingDocument, JournalLine
from app.models.ar import CustomerInvoice
from app.models.chart_of_accounts import Account
from app.models.crm import SalesContract
from app.repositories import budget_repository, project_control_repository, project_repository
from app.services import budget_service, forecast_service


@dataclass
class ProjectFinancialSummary:
    project_id: uuid.UUID
    currency_code: str
    contract_value: Decimal | None
    baseline_budget: Decimal | None
    current_budget: Decimal | None
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal | None
    invoiced: Decimal
    collected: Decimal
    receivables_outstanding: Decimal
    recognized_revenue: Decimal
    actual_cost: Decimal
    expected_profit: Decimal | None
    expected_margin_percent: Decimal | None
    actual_profit: Decimal | None
    actual_margin_percent: Decimal | None
    progress_percent: Decimal | None
    bac: Decimal | None
    pv: Decimal | None
    ev: Decimal | None
    ac: Decimal | None
    cpi: Decimal | None
    spi: Decimal | None
    etc: Decimal | None
    eac: Decimal | None
    vac: Decimal | None


def _posted_gl_total(
    db: Session,
    *,
    project_id: uuid.UUID,
    account_type: str,
) -> Decimal:
    amount = (
        JournalLine.credit_amount - JournalLine.debit_amount
        if account_type == "REVENUE"
        else JournalLine.debit_amount - JournalLine.credit_amount
    )
    stmt = (
        select(func.coalesce(func.sum(amount), 0))
        .join(
            AccountingDocument,
            JournalLine.accounting_document_id == AccountingDocument.id,
        )
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            AccountingDocument.status.in_(LEDGER_EFFECTIVE_STATUSES),
            AccountingDocument.scope == "PROJECT",
            AccountingDocument.project_id == project_id,
            JournalLine.project_id == project_id,
            Account.account_type == account_type,
        )
    )
    return Decimal(db.execute(stmt).scalar_one())


def get_summary(db: Session, *, project_id: uuid.UUID) -> ProjectFinancialSummary:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} no existe")

    contract_stmt = select(func.coalesce(func.sum(SalesContract.amount), 0)).where(
        SalesContract.project_id == project_id,
        SalesContract.status.in_(("ACTIVE", "BILLED")),
    )
    contract_total = Decimal(db.execute(contract_stmt).scalar_one())
    contract_value = contract_total if contract_total > 0 else None

    invoice_stmt = select(
        func.coalesce(func.sum(CustomerInvoice.amount), 0),
        func.coalesce(func.sum(CustomerInvoice.amount_collected), 0),
    ).where(
        CustomerInvoice.project_id == project_id,
        CustomerInvoice.status.in_(("APPROVED", "PARTIALLY_COLLECTED", "COLLECTED")),
    )
    invoiced_raw, collected_raw = db.execute(invoice_stmt).one()
    invoiced = Decimal(invoiced_raw)
    collected = Decimal(collected_raw)

    baseline = budget_repository.get_baseline_budget(db, project_id)
    active_budget = budget_repository.get_active_budget(db, project_id)
    baseline_budget = (
        budget_repository.sum_authorized(db, baseline.id) if baseline is not None else None
    )
    current_budget = (
        budget_repository.sum_authorized(db, active_budget.id) if active_budget is not None else None
    )

    budget_summary = budget_service.compute_summary(db, project_id=project_id)
    forecast = forecast_service.compute_forecast(db, project_id=project_id)
    latest_progress = project_control_repository.latest_progress(db, project_id)

    recognized_revenue = _posted_gl_total(db, project_id=project_id, account_type="REVENUE")
    actual_cost = _posted_gl_total(db, project_id=project_id, account_type="EXPENSE")

    expected_profit = None
    expected_margin_percent = None
    if contract_value is not None and current_budget is not None:
        expected_profit = contract_value - current_budget
        if contract_value > 0:
            expected_margin_percent = (expected_profit / contract_value) * Decimal("100")

    actual_profit = None
    actual_margin_percent = None
    if recognized_revenue > 0 or actual_cost > 0:
        actual_profit = recognized_revenue - actual_cost
        if recognized_revenue > 0:
            actual_margin_percent = (actual_profit / recognized_revenue) * Decimal("100")

    currency_code = project.currency_code or "HNL"
    available = budget_summary.available if active_budget is not None else None

    return ProjectFinancialSummary(
        project_id=project.id,
        currency_code=currency_code,
        contract_value=contract_value,
        baseline_budget=baseline_budget,
        current_budget=current_budget,
        committed=budget_summary.committed,
        accrued=budget_summary.accrued,
        paid=budget_summary.paid,
        available=available,
        invoiced=invoiced,
        collected=collected,
        receivables_outstanding=invoiced - collected,
        recognized_revenue=recognized_revenue,
        actual_cost=actual_cost,
        expected_profit=expected_profit,
        expected_margin_percent=expected_margin_percent,
        actual_profit=actual_profit,
        actual_margin_percent=actual_margin_percent,
        progress_percent=latest_progress.actual_percent if latest_progress is not None else None,
        bac=forecast.bac if active_budget is not None else None,
        pv=forecast.pv,
        ev=forecast.ev,
        ac=forecast.ac,
        cpi=forecast.cpi,
        spi=forecast.spi,
        etc=forecast.etc,
        eac=forecast.eac,
        vac=forecast.vac,
    )
