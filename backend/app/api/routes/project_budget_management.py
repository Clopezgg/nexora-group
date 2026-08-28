import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.repositories import budget_repository, project_repository
from app.schemas.project_budget import BudgetRedistributionRequest
from app.schemas.project_control import BudgetLineResponse, BudgetResponse
from app.services import audit_service, budget_redistribution_service, budget_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/projects", tags=["projects"])


def _budget_to_response(db: Session, budget) -> BudgetResponse:
    return BudgetResponse(
        id=budget.id,
        project_id=budget.project_id,
        version=budget.version,
        status=budget.status,
        currency_code=budget.currency_code,
        previous_budget_id=budget.previous_budget_id,
        change_order_id=budget.change_order_id,
        lines=[
            BudgetLineResponse(
                id=line.id,
                wbs_node_id=line.wbs_node_id,
                economic_category_id=line.economic_category_id,
                cost_center_id=line.cost_center_id,
                fiscal_period_id=line.fiscal_period_id,
                authorized_amount=line.authorized_amount,
            )
            for line in budget_repository.list_lines(db, budget.id)
        ],
    )


@router.post("/{project_id}/budgets/redistribute-unassigned", response_model=BudgetResponse)
def redistribute_unassigned_budget(
    project_id: uuid.UUID,
    payload: BudgetRedistributionRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> BudgetResponse:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="create", company_id=project.company_id
    )
    previous = budget_repository.get_active_budget(db, project_id)
    try:
        revised = budget_redistribution_service.redistribute_unassigned_budget(
            db,
            project_id=project_id,
            lines=[
                budget_service.BudgetLineInput(
                    authorized_amount=line.authorized_amount,
                    wbs_node_id=line.wbs_node_id,
                    economic_category_id=line.economic_category_id,
                    cost_center_id=line.cost_center_id,
                    fiscal_period_id=line.fiscal_period_id,
                )
                for line in payload.lines
            ],
            notes=payload.notes,
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="project.budget.redistribute_wbs",
            entity_type="project.budget",
            entity_id=revised.id,
            company_id=project.company_id,
            project_id=project.id,
            before={"budgetId": str(previous.id) if previous else None, "authorized": str(budget_repository.sum_authorized(db, previous.id)) if previous else None},
            after={"budgetId": str(revised.id), "authorized": str(budget_repository.sum_authorized(db, revised.id)), "lineCount": len(payload.lines)},
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(revised)
        return _budget_to_response(db, revised)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
