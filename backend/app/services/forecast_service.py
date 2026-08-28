import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import AccountingDocument, JournalLine
from app.models.chart_of_accounts import Account
from app.repositories import (
    budget_repository,
    inventory_repository,
    project_control_repository,
    project_repository,
)

"""Forecast / Earned Value.

BAC is the active project COST budget. PV/EV use the latest progress record
against BAC. AC combines authoritative posted General Ledger expense with
posted project inventory consumption, which is not yet mirrored into the GL.
It never treats cash paid or accrued invoice amounts as cost. When progress or
a cost budget is missing, dependent metrics remain None so the UI can show an
honest em dash instead of a fabricated zero.
"""


@dataclass
class ForecastSnapshot:
    bac: Decimal
    pv: Decimal | None
    ev: Decimal | None
    ac: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    etc: Decimal | None
    eac: Decimal | None
    vac: Decimal | None


def _project_gl_actual_cost(db: Session, *, project_id: uuid.UUID) -> Decimal:
    stmt = (
        select(func.coalesce(func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0))
        .join(
            AccountingDocument,
            JournalLine.accounting_document_id == AccountingDocument.id,
        )
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            AccountingDocument.status == "POSTED",
            AccountingDocument.scope == "PROJECT",
            AccountingDocument.project_id == project_id,
            JournalLine.project_id == project_id,
            Account.account_type == "EXPENSE",
        )
    )
    return Decimal(db.execute(stmt).scalar_one())


def compute_forecast(db: Session, *, project_id: uuid.UUID) -> ForecastSnapshot:
    active_budget = budget_repository.get_active_budget(db, project_id)
    bac = budget_repository.sum_authorized(db, active_budget.id) if active_budget is not None else Decimal("0")

    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} no existe")
    inventory_actuals = inventory_repository.project_actuals_by_project(
        db, company_id=project.company_id
    )
    ac = _project_gl_actual_cost(db, project_id=project_id) + inventory_actuals.get(
        project_id, Decimal("0")
    )

    latest_progress = project_control_repository.latest_progress(db, project_id)
    if latest_progress is None or active_budget is None:
        return ForecastSnapshot(
            bac=bac, pv=None, ev=None, ac=ac, cpi=None, spi=None, etc=None, eac=None, vac=None
        )

    pv = bac * (latest_progress.planned_percent / Decimal("100"))
    ev = bac * (latest_progress.actual_percent / Decimal("100"))

    cpi = (ev / ac) if ac > 0 else None
    spi = (ev / pv) if pv > 0 else None
    etc = ((bac - ev) / cpi) if cpi is not None and cpi > 0 else None
    eac = (ac + etc) if etc is not None else None
    vac = (bac - eac) if eac is not None else None

    return ForecastSnapshot(bac=bac, pv=pv, ev=ev, ac=ac, cpi=cpi, spi=spi, etc=etc, eac=eac, vac=vac)
