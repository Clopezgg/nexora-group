import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chart_of_accounts import Account, ChartOfAccount
from app.services import budget_service, treasury_service

"""Reporting (orden maestra, NXR-REQ-0093/0094). Este servicio SOLO arma
reportes de lectura reusando cálculos ya existentes y confiables
(treasury_service.account_balance, budget_service.compute_summary) --
nunca recalcula en paralelo lo que esos servicios ya calculan. Alcance
deliberado de esta fase: Trial Balance + Budget vs Actual únicamente.
Balance Sheet / P&L / Cash Flow / reportes de Treasury o Procurement /
Earned Value (CPI/SPI/EAC/VAC) quedan fuera de alcance -- ver
docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md."""


@dataclass
class TrialBalanceRow:
    account_code: str
    account_name: str
    debit_balance: Decimal
    credit_balance: Decimal


@dataclass
class TrialBalanceReport:
    rows: list[TrialBalanceRow] = field(default_factory=list)
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")


def trial_balance(db: Session, *, company_id: uuid.UUID) -> TrialBalanceReport:
    chart = db.execute(
        select(ChartOfAccount).where(ChartOfAccount.company_id == company_id)
    ).scalar_one_or_none()
    if chart is None:
        return TrialBalanceReport()

    accounts = db.execute(
        select(Account).where(Account.chart_of_account_id == chart.id).order_by(Account.code)
    ).scalars()

    report = TrialBalanceReport()
    for account in accounts:
        # account_balance() siempre devuelve débito - crédito, sin importar
        # account_type (ver treasury_service.account_balance). Un balance
        # positivo va a la columna débito, uno negativo a la columna
        # crédito -- así es como se arma un Trial Balance real (a
        # diferencia de un Balance Sheet, aquí NO se reclasifica por tipo
        # de cuenta).
        balance = treasury_service.account_balance(db, gl_account_id=account.id)
        if balance == Decimal("0"):
            continue
        debit = balance if balance > 0 else Decimal("0")
        credit = -balance if balance < 0 else Decimal("0")
        report.rows.append(
            TrialBalanceRow(
                account_code=account.code,
                account_name=account.name,
                debit_balance=debit,
                credit_balance=credit,
            )
        )
        report.total_debit += debit
        report.total_credit += credit
    return report


@dataclass
class BudgetVsActualReport:
    authorized: Decimal
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal


def budget_vs_actual(db: Session, *, project_id: uuid.UUID) -> BudgetVsActualReport:
    """Reshape puro de budget_service.compute_summary -- no recalcula
    nada, solo redistribuye los mismos campos ya confiables."""
    summary = budget_service.compute_summary(db, project_id=project_id)
    return BudgetVsActualReport(
        authorized=summary.authorized,
        committed=summary.committed,
        accrued=summary.accrued,
        paid=summary.paid,
        available=summary.available,
    )
