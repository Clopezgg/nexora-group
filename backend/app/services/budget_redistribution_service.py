import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetLine
from app.repositories import budget_repository, project_control_repository, project_repository
from app.services import budget_service, forecast_service


def redistribute_unassigned_budget(
    db: Session,
    *,
    project_id: uuid.UUID,
    lines: list[budget_service.BudgetLineInput],
    notes: str | None = None,
    commit: bool = True,
) -> Budget:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise ValueError("Proyecto no encontrado")
    active = budget_repository.get_active_budget(db, project_id)
    if active is None:
        raise ValueError("El proyecto no tiene presupuesto activo")
    current_lines = budget_repository.list_lines(db, active.id)
    if not current_lines or any(line.wbs_node_id is not None for line in current_lines):
        raise ValueError("Solo se puede redistribuir un presupuesto cuyas líneas activas estén sin WBS")

    summary = budget_service.compute_summary(db, project_id=project_id)
    forecast = forecast_service.compute_forecast(db, project_id=project_id)
    if summary.committed != 0 or summary.accrued != 0 or summary.paid != 0 or forecast.ac != 0:
        raise ValueError(
            "El presupuesto ya tiene ejecución financiera; no se puede reclasificar el histórico. Usa una revisión/orden de cambio."
        )

    nodes = {node.id: node for node in project_control_repository.list_wbs_for_project(db, project_id)}
    if not nodes:
        raise ValueError("Crea primero la estructura WBS del proyecto")
    if any(line.wbs_node_id is None for line in lines):
        raise ValueError("Cada línea redistribuida debe tener un WBS")
    for line in lines:
        if line.wbs_node_id not in nodes:
            raise ValueError("Una línea de redistribución referencia un WBS que no pertenece al proyecto")

    original_total = budget_repository.sum_authorized(db, active.id)
    new_total = sum((line.authorized_amount for line in lines), Decimal("0"))
    if new_total != original_total:
        raise ValueError(
            f"La redistribución debe conservar exactamente el total histórico ({original_total})"
        )

    revised = Budget(
        project_id=project_id,
        version="REVISED",
        status="ACTIVE",
        currency_code=active.currency_code,
        previous_budget_id=active.id,
        change_order_id=None,
        notes=notes or "Redistribución auditada del presupuesto histórico sin WBS; el total no cambia.",
    )
    db.add(revised)
    db.flush()
    for line in lines:
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
    active.status = "SUPERSEDED"
    if commit:
        db.commit()
        db.refresh(revised)
    else:
        db.flush()
    return revised
