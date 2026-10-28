import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import (
    BudgetBaselineExistsError,
    BudgetCurrencyMismatchError,
    InvalidChangeOrderStateError,
)
from app.models.budget import Budget, BudgetLine
from app.models.company import Company
from app.models.cost_center import CostCenter, EconomicCategory
from app.models.fiscal import FiscalPeriod
from app.models.wbs import WBSNode
from app.repositories import (
    ap_repository,
    budget_repository,
    project_control_repository,
    project_repository,
)
from app.services import commitment_service

"""Budget / Controlling (orden maestra §40-41, docs/BUDGET_CONTROLLING.md).

Contrato de versionado: BASELINE se crea una sola vez y sus BudgetLine nunca
se editan ni eliminan. Una ChangeOrder aprobada genera un nuevo Budget
version=REVISED (el anterior ACTIVE pasa a SUPERSEDED, nunca se borra).

Todo BASELINE usa `Company.functional_currency_code`; no se acepta otra
moneda hasta que exista una política FX fechada y autoritativa.
"""


@dataclass
class BudgetLineInput:
    authorized_amount: Decimal
    wbs_node_id: uuid.UUID | None = None
    economic_category_id: uuid.UUID | None = None
    cost_center_id: uuid.UUID | None = None
    fiscal_period_id: uuid.UUID | None = None


@dataclass
class BudgetSummary:
    authorized: Decimal
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal
    advances: Decimal = Decimal("0")
    contract_commitment: Decimal = Decimal("0")
    standalone_po_commitment: Decimal = Decimal("0")
    po_under_contract: Decimal = Decimal("0")
    open_commitment: Decimal = Decimal("0")


def _validate_line_references(
    db: Session,
    *,
    project_id: uuid.UUID,
    company_id: uuid.UUID,
    line: BudgetLineInput,
) -> None:
    """Reject references from another project/company before persistence."""
    if line.authorized_amount <= 0:
        raise ValueError("authorized_amount debe ser mayor que cero")
    if line.wbs_node_id is not None:
        node = db.get(WBSNode, line.wbs_node_id)
        if node is None:
            raise ValueError(f"WBSNode {line.wbs_node_id} no existe")
        if node.project_id != project_id:
            raise ValueError("El WBS de una BudgetLine debe pertenecer al mismo proyecto")
    if line.economic_category_id is not None:
        category = db.get(EconomicCategory, line.economic_category_id)
        if category is None or category.company_id != company_id:
            raise ValueError("La categoría económica debe pertenecer a la compañía del proyecto")
    if line.cost_center_id is not None:
        cost_center = db.get(CostCenter, line.cost_center_id)
        if cost_center is None or cost_center.company_id != company_id:
            raise ValueError("El centro de costo debe pertenecer a la compañía del proyecto")
    if line.fiscal_period_id is not None:
        period = db.get(FiscalPeriod, line.fiscal_period_id)
        if period is None or period.company_id != company_id:
            raise ValueError("El período fiscal debe pertenecer a la compañía del proyecto")


def create_baseline(
    db: Session,
    *,
    project_id: uuid.UUID,
    currency_code: str,
    lines: list[BudgetLineInput],
    notes: str | None = None,
    commit: bool = True,
) -> Budget:
    project = project_repository.get_by_id_for_update(db, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} no existe")
    if budget_repository.get_baseline_budget(db, project_id) is not None:
        raise BudgetBaselineExistsError(
            f"El proyecto {project_id} ya tiene un BASELINE; no se puede sobrescribir"
        )
    company = db.get(Company, project.company_id)
    if company is None:
        raise ValueError(f"Company {project.company_id} no existe")
    if company.functional_currency_code is None:
        raise BudgetCurrencyMismatchError(
            f"La company {company.id} no tiene moneda funcional; no se puede crear un Budget"
        )
    if currency_code != company.functional_currency_code:
        raise BudgetCurrencyMismatchError(
            f"El Budget usa {currency_code}, pero la moneda funcional de la company es "
            f"{company.functional_currency_code}; no existe una política FX autoritativa"
        )
    for line in lines:
        _validate_line_references(
            db, project_id=project_id, company_id=project.company_id, line=line
        )

    budget = Budget(
        project_id=project_id,
        version="BASELINE",
        status="ACTIVE",
        currency_code=currency_code,
        notes=notes,
    )
    db.add(budget)
    db.flush()
    for line in lines:
        db.add(
            BudgetLine(
                budget_id=budget.id,
                wbs_node_id=line.wbs_node_id,
                economic_category_id=line.economic_category_id,
                cost_center_id=line.cost_center_id,
                fiscal_period_id=line.fiscal_period_id,
                authorized_amount=line.authorized_amount,
            )
        )
    if commit:
        db.commit()
        db.refresh(budget)
    else:
        db.flush()
    return budget


def _apply_change_order_delta(
    db: Session,
    *,
    revised_budget_id: uuid.UUID,
    wbs_node_id: uuid.UUID | None,
    delta: Decimal,
) -> None:
    """Apply a change without ever persisting a negative/zero BudgetLine."""
    if delta == 0:
        return
    if delta > 0:
        db.add(
            BudgetLine(
                budget_id=revised_budget_id,
                wbs_node_id=wbs_node_id,
                authorized_amount=delta,
            )
        )
        return

    remaining = -delta
    candidates = [
        line
        for line in budget_repository.list_lines(db, revised_budget_id)
        if line.wbs_node_id == wbs_node_id
    ]
    for line in candidates:
        reduction = min(line.authorized_amount, remaining)
        line.authorized_amount -= reduction
        remaining -= reduction
        if line.authorized_amount == 0:
            db.delete(line)
        if remaining == 0:
            break
    if remaining > 0:
        raise ValueError(
            "La reducción de presupuesto de la ChangeOrder excede el autorizado "
            "del WBS seleccionado"
        )


def approve_change_order(
    db: Session,
    *,
    change_order_id: uuid.UUID,
    approved_by: uuid.UUID,
    commit: bool = True,
) -> Budget:
    """Approve a submitted ChangeOrder and create an immutable budget revision."""
    change_order = project_control_repository.get_change_order(db, change_order_id)
    if change_order is None:
        raise ValueError(f"ChangeOrder {change_order_id} no existe")
    if change_order.status != "SUBMITTED":
        raise InvalidChangeOrderStateError(
            f"Solo se puede aprobar una ChangeOrder en estado SUBMITTED (actual: {change_order.status})"
        )

    project = project_repository.get_by_id_for_update(db, change_order.project_id)
    if project is None:
        raise ValueError(f"Project {change_order.project_id} no existe")
    if change_order.wbs_node_id is not None:
        node = db.get(WBSNode, change_order.wbs_node_id)
        if node is None or node.project_id != project.id:
            raise ValueError("El WBS de la ChangeOrder debe pertenecer al mismo proyecto")

    previous = budget_repository.get_active_budget(db, project.id)
    if previous is None:
        raise ValueError(
            f"El proyecto {project.id} no tiene un budget activo -- crea el BASELINE primero"
        )

    revised = Budget(
        project_id=project.id,
        version="REVISED",
        status="ACTIVE",
        currency_code=previous.currency_code,
        previous_budget_id=previous.id,
        change_order_id=change_order.id,
        notes=f"Generado por ChangeOrder aprobada: {change_order.reason}",
    )
    db.add(revised)
    db.flush()

    for line in budget_repository.list_lines(db, previous.id):
        db.add(
            BudgetLine(
                budget_id=revised.id,
                wbs_node_id=line.wbs_node_id,
                economic_category_id=line.economic_category_id,
                cost_center_id=line.cost_center_id,
                fiscal_period_id=line.fiscal_period_id,
                authorized_amount=line.authorized_amount,
            )
        )
    db.flush()

    _apply_change_order_delta(
        db,
        revised_budget_id=revised.id,
        wbs_node_id=change_order.wbs_node_id,
        delta=change_order.budget_change_amount,
    )

    previous.status = "SUPERSEDED"
    change_order.status = "APPROVED"
    change_order.approved_by = approved_by
    if commit:
        db.commit()
        db.refresh(revised)
    else:
        db.flush()
    return revised


def compute_summary(db: Session, *, project_id: uuid.UUID) -> BudgetSummary:
    active = budget_repository.get_active_budget(db, project_id)
    authorized = budget_repository.sum_authorized(db, active.id) if active is not None else Decimal("0")
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} no existe")
    commitment = commitment_service.compute_breakdown(
        db, company_id=project.company_id, project_id=project_id
    )
    accrued = ap_repository.project_accrued_total(
        db, company_id=project.company_id, project_id=project_id
    )
    advances = ap_repository.project_advance_total(
        db, company_id=project.company_id, project_id=project_id
    )
    paid = ap_repository.project_paid_total(
        db, company_id=project.company_id, project_id=project_id
    )
    available = authorized - commitment.open_commitment - accrued
    return BudgetSummary(
        authorized=authorized,
        committed=commitment.total_commitment,
        accrued=accrued,
        paid=paid,
        available=available,
        advances=advances,
        contract_commitment=commitment.contract_commitment,
        standalone_po_commitment=commitment.standalone_po_commitment,
        po_under_contract=commitment.po_under_contract,
        open_commitment=commitment.open_commitment,
    )
