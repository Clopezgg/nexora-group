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
version=REVISED (el anterior ACTIVE pasa a SUPERSEDED, nunca se borra) que
copia las líneas del budget anterior y agrega una línea adicional con el
delta de la ChangeOrder (positivo o negativo) contra el WBS que indique la
propia ChangeOrder -- es una simplificación deliberada (no redistribuye
línea por línea el presupuesto completo) documentada aquí y en
docs/BUDGET_CONTROLLING.md.

Todo BASELINE usa `Company.functional_currency_code`; no se acepta otra
moneda hasta que exista una política FX fechada y autoritativa.

Métricas AUTHORIZED/COMMITTED/ACCRUED/PAID/AVAILABLE: COMMITTED consume
Purchase Orders aprobadas de Procurement/Track C. ACCRUED/PAID siguen sin
fuente AP/Track A y permanecen en 0 real por ausencia de datos, sin
reinterpretar movimientos de inventario como devengo o efectivo.
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
    # `committed` es el compromiso TOTAL canónico (contrato + PO independiente),
    # sin doble contar las PO que desglosan un contrato (§20).
    committed: Decimal
    accrued: Decimal
    paid: Decimal
    available: Decimal
    # ORDEN MAESTRA §15 — contractual advances / prepayments (ASSET debit).
    # Reported alongside, never folded into `accrued` nor deducted from
    # `available` as recognised cost.
    advances: Decimal = Decimal("0")
    # ORDEN MAESTRA §20-§21 — desglose del compromiso.
    contract_commitment: Decimal = Decimal("0")
    standalone_po_commitment: Decimal = Decimal("0")
    po_under_contract: Decimal = Decimal("0")
    open_commitment: Decimal = Decimal("0")


def create_baseline(
    db: Session,
    *,
    project_id: uuid.UUID,
    currency_code: str,
    lines: list[BudgetLineInput],
    notes: str | None = None,
    commit: bool = True,
) -> Budget:
    if budget_repository.get_baseline_budget(db, project_id) is not None:
        raise BudgetBaselineExistsError(
            f"El proyecto {project_id} ya tiene un BASELINE; no se puede sobrescribir"
        )
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} no existe")
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


def approve_change_order(db: Session, *, change_order_id: uuid.UUID, approved_by: uuid.UUID, commit: bool = True) -> Budget:
    """Aprueba la ChangeOrder y, si tiene impacto de presupuesto (monto
    distinto de 0), crea el Budget REVISED correspondiente. El BASELINE (y
    cualquier REVISED anterior) nunca se modifica -- queda en status
    SUPERSEDED, intacto."""
    change_order = project_control_repository.get_change_order(db, change_order_id)
    if change_order is None:
        raise ValueError(f"ChangeOrder {change_order_id} no existe")
    if change_order.status != "SUBMITTED":
        raise InvalidChangeOrderStateError(
            f"Solo se puede aprobar una ChangeOrder en estado SUBMITTED (actual: {change_order.status})"
        )

    previous = budget_repository.get_active_budget(db, change_order.project_id)
    if previous is None:
        raise ValueError(
            f"El proyecto {change_order.project_id} no tiene un budget activo -- crea el BASELINE primero"
        )

    revised = Budget(
        project_id=change_order.project_id,
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

    if change_order.budget_change_amount != 0:
        db.add(
            BudgetLine(
                budget_id=revised.id,
                wbs_node_id=change_order.wbs_node_id,
                authorized_amount=change_order.budget_change_amount,
            )
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
    # ORDEN MAESTRA §21/§22 — el disponible descuenta el compromiso ABIERTO
    # (relevado por lo ya devengado) más el costo devengado. El pago no vuelve
    # a consumir presupuesto.
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
