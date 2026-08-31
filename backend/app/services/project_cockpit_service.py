"""Project Financial Cockpit — EAC/ETC/CPI/margen (orden maestra FINAL,
Phase 6).

Reglas (CLAUDE.md §8): Budget es control, el GL es la verdad del costo. El
costo real (AC) se lee del General Ledger — suma del neto deudor de las
líneas de cuentas de gasto imputadas al proyecto — no del subledger de AP,
para capturar TODO el costo (AP, mano de obra, combustible, depreciación…).

No se inventa política: si no hay presupuesto o no hay avance, los derivados
que dependen de ellos quedan en `None` (fail-closed), no en un número
inventado.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.accounting import JournalLine
from app.models.chart_of_accounts import Account
from app.models.crm import SalesContract
from app.models.progress import ProgressRecord
from app.models.project import Project
from app.services import budget_service


@dataclass(frozen=True)
class ProjectCockpit:
    project_id: str
    project_name: str
    currency_code: str
    # Presupuesto / compromiso
    budget_at_completion: Decimal  # BAC
    committed: Decimal
    actual_cost: Decimal  # AC (del GL)
    # Avance físico
    percent_complete: Decimal | None
    earned_value: Decimal | None  # EV = BAC * %
    cost_performance_index: Decimal | None  # CPI = EV / AC
    estimate_to_complete: Decimal | None  # ETC
    estimate_at_completion: Decimal | None  # EAC = AC + ETC
    variance_at_completion: Decimal | None  # VAC = BAC - EAC
    # Margen
    contract_revenue: Decimal
    projected_margin: Decimal | None  # revenue - EAC
    projected_margin_pct: Decimal | None


def _actual_cost_from_gl(db: Session, *, project_id) -> Decimal:
    total = db.execute(
        select(
            func.coalesce(
                func.sum(JournalLine.debit_amount - JournalLine.credit_amount), Decimal("0")
            )
        )
        .join(Account, Account.id == JournalLine.account_id)
        .where(JournalLine.project_id == project_id)
        .where(Account.account_type == "EXPENSE")
    ).scalar_one()
    return Decimal(total)


def _percent_complete(db: Session, *, project_id) -> Decimal | None:
    row = db.execute(
        select(ProgressRecord.actual_percent)
        .where(ProgressRecord.project_id == project_id)
        .where(ProgressRecord.wbs_node_id.is_(None))
        .order_by(ProgressRecord.record_date.desc(), ProgressRecord.created_at.desc())
    ).scalars().first()
    if row is None:
        # Sin avance a nivel proyecto: probar el máximo avance registrado en
        # cualquier WBS como aproximación conservadora.
        row = db.execute(
            select(func.max(ProgressRecord.actual_percent)).where(
                ProgressRecord.project_id == project_id
            )
        ).scalar_one()
    return Decimal(row) if row is not None else None


def _contract_revenue(db: Session, *, project_id) -> Decimal:
    total = db.execute(
        select(func.coalesce(func.sum(SalesContract.amount), Decimal("0")))
        .where(SalesContract.project_id == project_id)
        .where(SalesContract.status != "CANCELLED")
    ).scalar_one()
    return Decimal(total)


def build(db: Session, *, project_id) -> ProjectCockpit | None:
    project = db.get(Project, project_id)
    if project is None:
        return None

    summary = budget_service.compute_summary(db, project_id=project_id)
    bac = summary.authorized
    committed = summary.committed
    ac = _actual_cost_from_gl(db, project_id=project_id)
    pct = _percent_complete(db, project_id=project_id)
    revenue = _contract_revenue(db, project_id=project_id)

    ev: Decimal | None = None
    cpi: Decimal | None = None
    etc: Decimal | None = None
    eac: Decimal | None = None
    vac: Decimal | None = None

    if bac > 0 and pct is not None:
        ev = (bac * pct / Decimal("100")).quantize(Decimal("0.01"))
        if ac > 0:
            cpi = (ev / ac).quantize(Decimal("0.0001"))
        # ETC: si hay CPI usable, extrapola el desempeño; si no, resto simple.
        if cpi and cpi > 0:
            etc = ((bac - ev) / cpi).quantize(Decimal("0.01"))
        else:
            etc = max(bac - ac, Decimal("0"))
        eac = (ac + etc).quantize(Decimal("0.01"))
        vac = (bac - eac).quantize(Decimal("0.01"))

    margin: Decimal | None = None
    margin_pct: Decimal | None = None
    if revenue > 0 and eac is not None:
        margin = (revenue - eac).quantize(Decimal("0.01"))
        margin_pct = (margin / revenue * Decimal("100")).quantize(Decimal("0.01"))

    return ProjectCockpit(
        project_id=str(project.id),
        project_name=project.name,
        currency_code=project.currency_code or "HNL",
        budget_at_completion=bac,
        committed=committed,
        actual_cost=ac,
        percent_complete=pct,
        earned_value=ev,
        cost_performance_index=cpi,
        estimate_to_complete=etc,
        estimate_at_completion=eac,
        variance_at_completion=vac,
        contract_revenue=revenue,
        projected_margin=margin,
        projected_margin_pct=margin_pct,
    )
