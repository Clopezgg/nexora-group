import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine
from app.models.chart_of_accounts import Account, ChartOfAccount
from app.models.treasury import TreasuryAccount
from app.services import budget_service, treasury_service

"""Reporting (orden maestra, NXR-REQ-0093/0094). Este servicio SOLO arma
reportes de lectura reusando cálculos ya existentes y confiables
(treasury_service.account_balance, budget_service.compute_summary) --
nunca recalcula en paralelo lo que esos servicios ya calculan, salvo el
General Ledger / Balance Sheet / Income Statement / Cash Flow de más
abajo, que agregan directamente sobre AccountingDocument/JournalLine (el
General Ledger es la verdad contable, CLAUDE.md §8) porque
account_balance() no acepta rango de fechas y consultarlo cuenta por
cuenta sería O(n) queries. Reportes de Treasury o Procurement / Earned
Value (CPI/SPI/EAC/VAC) quedan fuera de alcance -- ver
docs/superpowers/specs/2026-08-25-financial-statements-design.md (Cash
Flow salió de "fuera de alcance" el 2026-08-25, ver cash_flow_statement
más abajo)."""

_LEDGER_STATUSES = ("POSTED", "REVERSED")


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


@dataclass
class StatementRow:
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    balance: Decimal


@dataclass
class BalanceSheetReport:
    assets: list[StatementRow] = field(default_factory=list)
    liabilities: list[StatementRow] = field(default_factory=list)
    equity: list[StatementRow] = field(default_factory=list)
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    current_earnings: Decimal = Decimal("0")
    total_equity_including_earnings: Decimal = Decimal("0")
    total_liabilities_and_equity: Decimal = Decimal("0")
    equation_delta: Decimal = Decimal("0")


@dataclass
class IncomeStatementReport:
    revenue: list[StatementRow] = field(default_factory=list)
    expenses: list[StatementRow] = field(default_factory=list)
    total_revenue: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")


@dataclass
class GeneralLedgerRow:
    line_id: uuid.UUID
    document_id: uuid.UUID
    document_number: str
    posted_at: datetime | None
    document_status: str
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    scope: str
    project_id: uuid.UUID | None
    description: str | None
    debit_amount: Decimal
    credit_amount: Decimal


@dataclass
class GeneralLedgerReport:
    rows: list[GeneralLedgerRow] = field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 50
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")


def resolve_account_for_company(
    db: Session, *, account_id: uuid.UUID, company_id: uuid.UUID
) -> Account | None:
    """Devuelve la cuenta solo si pertenece a `company_id`; None en
    cualquier otro caso (no existe o pertenece a otra compañía) -- el
    caller siempre debe responder 404 genérico, nunca distinguir entre
    ambos casos (ver diseño Financial Statements)."""
    return db.execute(
        select(Account)
        .join(ChartOfAccount, ChartOfAccount.id == Account.chart_of_account_id)
        .where(Account.id == account_id, ChartOfAccount.company_id == company_id)
    ).scalar_one_or_none()


def _activity_query(
    db: Session,
    *,
    company_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
    account_id: uuid.UUID | None = None,
):
    """Un asiento reversado y su reversal (ambos POSTED/REVERSED, nunca
    DRAFT) deben quedar incluidos para que sus saldos se cancelen -- ver
    INV-ACC-002 y el diseño Financial Statements."""
    query = (
        select(
            Account.id,
            Account.code,
            Account.name,
            Account.account_type,
            Account.cash_flow_activity,
            func.coalesce(func.sum(JournalLine.debit_amount), Decimal("0")),
            func.coalesce(func.sum(JournalLine.credit_amount), Decimal("0")),
        )
        .select_from(JournalLine)
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .join(Account, Account.id == JournalLine.account_id)
        .join(ChartOfAccount, ChartOfAccount.id == Account.chart_of_account_id)
        .where(
            ChartOfAccount.company_id == company_id,
            AccountingDocument.company_id == company_id,
            AccountingDocument.status.in_(_LEDGER_STATUSES),
        )
        .group_by(
            Account.id, Account.code, Account.name, Account.account_type, Account.cash_flow_activity
        )
        .order_by(Account.code)
    )
    if date_from is not None:
        query = query.where(func.date(AccountingDocument.posted_at) >= date_from)
    if date_to is not None:
        query = query.where(func.date(AccountingDocument.posted_at) <= date_to)
    if account_id is not None:
        query = query.where(Account.id == account_id)
    return query


def balance_sheet(
    db: Session, *, company_id: uuid.UUID, as_of: date | None = None
) -> BalanceSheetReport:
    report = BalanceSheetReport()
    total_revenue = Decimal("0")
    total_expenses = Decimal("0")
    for account_id, code, name, account_type, _cfa, debit, credit in db.execute(
        _activity_query(db, company_id=company_id, date_from=None, date_to=as_of)
    ):
        if account_type == "ASSET":
            balance = debit - credit
            if balance == Decimal("0"):
                continue
            report.assets.append(StatementRow(account_id, code, name, account_type, balance))
            report.total_assets += balance
        elif account_type == "LIABILITY":
            balance = credit - debit
            if balance == Decimal("0"):
                continue
            report.liabilities.append(StatementRow(account_id, code, name, account_type, balance))
            report.total_liabilities += balance
        elif account_type == "EQUITY":
            balance = credit - debit
            if balance == Decimal("0"):
                continue
            report.equity.append(StatementRow(account_id, code, name, account_type, balance))
            report.total_equity += balance
        elif account_type == "REVENUE":
            total_revenue += credit - debit
        elif account_type == "EXPENSE":
            total_expenses += debit - credit

    report.current_earnings = total_revenue - total_expenses
    report.total_equity_including_earnings = report.total_equity + report.current_earnings
    report.total_liabilities_and_equity = (
        report.total_liabilities + report.total_equity_including_earnings
    )
    report.equation_delta = report.total_assets - report.total_liabilities_and_equity
    if report.equation_delta != Decimal("0"):
        raise RuntimeError("Balance Sheet no cuadra con el General Ledger")
    return report


def income_statement(
    db: Session,
    *,
    company_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> IncomeStatementReport:
    report = IncomeStatementReport()
    for account_id, code, name, account_type, _cfa, debit, credit in db.execute(
        _activity_query(db, company_id=company_id, date_from=date_from, date_to=date_to)
    ):
        if account_type == "REVENUE":
            balance = credit - debit
            if balance == Decimal("0"):
                continue
            report.revenue.append(StatementRow(account_id, code, name, account_type, balance))
            report.total_revenue += balance
        elif account_type == "EXPENSE":
            balance = debit - credit
            if balance == Decimal("0"):
                continue
            report.expenses.append(StatementRow(account_id, code, name, account_type, balance))
            report.total_expenses += balance

    report.net_income = report.total_revenue - report.total_expenses
    return report


def general_ledger(
    db: Session,
    *,
    company_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> GeneralLedgerReport:
    filters = [
        ChartOfAccount.company_id == company_id,
        AccountingDocument.company_id == company_id,
        AccountingDocument.status.in_(_LEDGER_STATUSES),
    ]
    if date_from is not None:
        filters.append(func.date(AccountingDocument.posted_at) >= date_from)
    if date_to is not None:
        filters.append(func.date(AccountingDocument.posted_at) <= date_to)
    if account_id is not None:
        filters.append(Account.id == account_id)

    base = (
        select(JournalLine, AccountingDocument, Account)
        .select_from(JournalLine)
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .join(Account, Account.id == JournalLine.account_id)
        .join(ChartOfAccount, ChartOfAccount.id == Account.chart_of_account_id)
        .where(*filters)
    )

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    totals_row = db.execute(
        select(
            func.coalesce(func.sum(JournalLine.debit_amount), Decimal("0")),
            func.coalesce(func.sum(JournalLine.credit_amount), Decimal("0")),
        )
        .select_from(JournalLine)
        .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
        .join(Account, Account.id == JournalLine.account_id)
        .join(ChartOfAccount, ChartOfAccount.id == Account.chart_of_account_id)
        .where(*filters)
    ).one()

    detail = db.execute(
        base.order_by(
            AccountingDocument.posted_at, AccountingDocument.document_number, JournalLine.id
        )
        .offset(offset)
        .limit(limit)
    ).all()

    rows = [
        GeneralLedgerRow(
            line_id=line.id,
            document_id=document.id,
            document_number=document.document_number,
            posted_at=document.posted_at,
            document_status=document.status,
            account_id=account.id,
            account_code=account.code,
            account_name=account.name,
            account_type=account.account_type,
            scope=document.scope,
            project_id=document.project_id,
            description=line.description,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
        )
        for line, document, account in detail
    ]

    return GeneralLedgerReport(
        rows=rows,
        total=total,
        offset=offset,
        limit=limit,
        total_debit=totals_row[0],
        total_credit=totals_row[1],
    )


@dataclass
class CashFlowReport:
    operating: list[StatementRow] = field(default_factory=list)
    investing: list[StatementRow] = field(default_factory=list)
    financing: list[StatementRow] = field(default_factory=list)
    unclassified: list[StatementRow] = field(default_factory=list)
    total_operating: Decimal = Decimal("0")
    total_investing: Decimal = Decimal("0")
    total_financing: Decimal = Decimal("0")
    total_unclassified: Decimal = Decimal("0")
    net_change_in_cash: Decimal = Decimal("0")


def cash_flow_statement(
    db: Session,
    *,
    company_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CashFlowReport:
    """Método directo (orden maestra, NXR-REQ-0016/0093): el efectivo son
    las cuentas GL 1:1 con un TreasuryAccount de esta company
    (CLAUDE.md §7 -- Treasury es dueño del dinero). Por partida doble, el
    cambio neto en esas cuentas en el período es exactamente el negativo
    de la suma de (credit - debit) de TODAS las demás cuentas tocadas en
    el mismo período -- no hace falta correlacionar documento por
    documento ni excluir explícitamente las transferencias Treasury<->
    Treasury (ambos lados son "cash", así que se cancelan solos en la
    resta). Cada cuenta no-cash se clasifica en Operating/Investing/
    Financing vía `Account.cash_flow_activity` (ver
    `PATCH /api/master-data/accounts/{id}`); una cuenta sin clasificar
    cae en `unclassified`, mostrado explícitamente en vez de ocultado o
    forzado a un valor (CLAUDE.md: no fabricar datos, no ocultar bugs)."""
    cash_account_ids = set(
        db.execute(
            select(TreasuryAccount.gl_account_id).where(TreasuryAccount.company_id == company_id)
        ).scalars()
    )

    report = CashFlowReport()
    for account_id, code, name, _account_type, activity, debit, credit in db.execute(
        _activity_query(db, company_id=company_id, date_from=date_from, date_to=date_to)
    ):
        net = credit - debit
        if net == Decimal("0"):
            continue
        if account_id in cash_account_ids:
            report.net_change_in_cash += debit - credit
            continue
        row = StatementRow(account_id, code, name, activity or "UNCLASSIFIED", net)
        if activity == "OPERATING":
            report.operating.append(row)
            report.total_operating += net
        elif activity == "INVESTING":
            report.investing.append(row)
            report.total_investing += net
        elif activity == "FINANCING":
            report.financing.append(row)
            report.total_financing += net
        else:
            report.unclassified.append(row)
            report.total_unclassified += net
    return report
