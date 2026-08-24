import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import BudgetBaselineExistsError, InvalidChangeOrderStateError
from app.models.budget import Budget, BudgetLine
from app.repositories import budget_repository, project_control_repository

"""Budget / Controlling (orden maestra §40-41, docs/BUDGET_CONTROLLING.md).

Contrato de versionado: BASELINE se crea una sola vez y sus BudgetLine nunca
se editan ni eliminan. Una ChangeOrder aprobada genera un nuevo Budget
version=REVISED (el anterior ACTIVE pasa a SUPERSEDED, nunca se borra) que
copia las líneas del budget anterior y agrega una línea adicional con el
delta de la ChangeOrder (positivo o negativo) contra el WBS que indique la
propia ChangeOrder -- es una simplificación deliberada (no redistribuye
línea por línea el presupuesto completo) documentada aquí y en
docs/BUDGET_CONTROLLING.md.

Métricas AUTHORIZED/COMMITTED/ACCRUED/PAID/AVAILABLE: COMMITTED (Procurement/
Track C) y ACCRUED/PAID (AP/Track A) todavía no existen en este track --
`compute_summary` los deja en 0 real (nunca inventado) mediante los stubs
`committed_amount_stub`/`accrued_amount_stub`/`paid_amount_stub`, listos
para que el coordinador los conecte a las tablas reales cuando esos tracks
aterricen, sin cambiar la forma del contrato.
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


def create_baseline(
    db: Session,
    *,
    project_id: uuid.UUID,
    currency_code: str,
    lines: list[BudgetLineInput],
    notes: str | None = None,
) -> Budget:
    if budget_repository.get_baseline_budget(db, project_id) is not None:
        raise BudgetBaselineExistsError(
            f"El proyecto {project_id} ya tiene un BASELINE; no se puede sobrescribir"
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
    db.commit()
    db.refresh(budget)
    return budget


def approve_change_order(db: Session, *, change_order_id: uuid.UUID, approved_by: uuid.UUID) -> Budget:
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
    db.commit()
    db.refresh(revised)
    return revised


def compute_summary(db: Session, *, project_id: uuid.UUID) -> BudgetSummary:
    active = budget_repository.get_active_budget(db, project_id)
    authorized = budget_repository.sum_authorized(db, active.id) if active is not None else Decimal("0")
    # Stubs honestos: 0 real hasta que Track A (AP) / Track C (Procurement)
    # aporten las tablas reales de compromiso/devengo/pago. Nunca inventado.
    committed = Decimal("0")
    accrued = Decimal("0")
    paid = Decimal("0")
    available = authorized - committed - accrued
    return BudgetSummary(
        authorized=authorized, committed=committed, accrued=accrued, paid=paid, available=available
    )
