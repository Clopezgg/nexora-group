import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.deps_correlation import get_correlation_id
from app.models.project import Project
from app.repositories import (
    budget_repository,
    project_control_repository,
    project_repository,
)
from app.schemas.project_control import (
    BudgetBaselineCreateRequest,
    BudgetLineResponse,
    BudgetResponse,
    BudgetSummaryResponse,
    ChangeOrderCreateRequest,
    ChangeOrderResponse,
    ForecastResponse,
    MilestoneCreateRequest,
    MilestoneResponse,
    ProgressRecordCreateRequest,
    ProgressRecordResponse,
    ProjectCreateRequest,
    ProjectResponse,
    TaskCreateRequest,
    TaskResponse,
    WBSNodeCreateRequest,
    WBSNodeResponse,
)
from app.services import audit_service, budget_service, forecast_service
from app.services.financial_validation_service import assert_evidence_belongs_to_company
from app.services.permission_service import (
    accessible_project_ids,
    assert_company_access,
    assert_project_access,
    grant_project_access,
    require_permission,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


def _budget_to_response(db: Session, budget) -> BudgetResponse:
    lines = budget_repository.list_lines(db, budget.id)
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
            for line in lines
        ],
    )


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    company_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False, alias="includeArchived"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "read")),
) -> list[ProjectResponse]:
    assert_company_access(db, user_id=user.id, resource="project", action="read", company_id=company_id)
    projects = project_repository.list_projects_for_company(db, company_id)
    allowed_project_ids = accessible_project_ids(
        db, user_id=user.id, resource="project", action="read"
    )
    if allowed_project_ids is not None:
        allowed = set(allowed_project_ids)
        projects = [project for project in projects if project.id in allowed]
    if status_filter:
        wanted = {s.strip().upper() for s in status_filter.split(",") if s.strip()}
        projects = [p for p in projects if p.status in wanted]
    elif not include_archived:
        # ARCHIVED es soft-delete: oculto de la operación diaria salvo que se
        # pida explícitamente (§9).
        projects = [p for p in projects if p.status != "ARCHIVED"]
    return [ProjectResponse.model_validate(project, from_attributes=True) for project in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> ProjectResponse:
    assert_company_access(
        db, user_id=user.id, resource="project", action="create", company_id=payload.company_id
    )
    project = project_repository.create_project(
        db,
        company_id=payload.company_id,
        name=payload.name,
        code=payload.code,
        customer_id=payload.customer_id,
        customer_ref=payload.customer_ref,
        manager=payload.manager,
        manager_user_id=payload.manager_user_id,
        currency_code=payload.currency_code,
        cost_center_id=payload.cost_center_id,
        planned_start=payload.planned_start,
        planned_end=payload.planned_end,
        description=payload.description,
        address_line_1=payload.address_line_1,
        address_line_2=payload.address_line_2,
        city=payload.city,
        state_department=payload.state_department,
        country=payload.country,
        location_reference=payload.location_reference,
    )
    db.flush()
    # The creator must be able to continue operating the project when their
    # role has project_scope=OWN. Administrator/ANY can also carry the row;
    # it never grants a permission by itself.
    grant_project_access(db, user_id=user.id, project_id=project.id)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.create",
        entity_type="project",
        entity_id=project.id,
        company_id=project.company_id,
        project_id=project.id,
        before=None,
        after={"name": project.name, "code": project.code},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project", "read")),
) -> ProjectResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project", action="read", company_id=project.company_id
    )
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.get("/{project_id}/wbs", response_model=list[WBSNodeResponse])
def list_wbs(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.wbs", "read")),
) -> list[WBSNodeResponse]:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.wbs", action="read", company_id=project.company_id
    )
    nodes = project_control_repository.list_wbs_for_project(db, project_id)
    return [WBSNodeResponse.model_validate(node, from_attributes=True) for node in nodes]


@router.post("/{project_id}/wbs", response_model=WBSNodeResponse, status_code=201)
def create_wbs_node(
    project_id: uuid.UUID,
    payload: WBSNodeCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.wbs", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> WBSNodeResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.wbs", action="create", company_id=project.company_id
    )
    node = project_control_repository.create_wbs_node(
        db,
        project_id=project_id,
        code=payload.code,
        name=payload.name,
        parent_id=payload.parent_id,
        manager=payload.manager,
        planned_start=payload.planned_start,
        planned_finish=payload.planned_finish,
    )
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.wbs.create",
        entity_type="project.wbs",
        entity_id=node.id,
        company_id=project.company_id,
        project_id=project_id,
        before=None,
        after={"code": node.code, "name": node.name},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(node)
    return WBSNodeResponse.model_validate(node, from_attributes=True)


@router.get("/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.planning", "read")),
) -> list[TaskResponse]:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.planning", action="read", company_id=project.company_id
    )
    tasks = project_control_repository.list_tasks_for_project(db, project_id)
    return [TaskResponse.model_validate(task, from_attributes=True) for task in tasks]


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    project_id: uuid.UUID,
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.planning", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> TaskResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.planning", action="create", company_id=project.company_id
    )
    task = project_control_repository.create_task(
        db,
        project_id=project_id,
        name=payload.name,
        wbs_node_id=payload.wbs_node_id,
        owner=payload.owner,
        planned_start=payload.planned_start,
        planned_end=payload.planned_end,
        depends_on_task_id=payload.depends_on_task_id,
    )
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.task.create",
        entity_type="project.task",
        entity_id=task.id,
        company_id=project.company_id,
        project_id=project_id,
        before=None,
        after={"name": task.name},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(task)
    return TaskResponse.model_validate(task, from_attributes=True)


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
def list_milestones(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.planning", "read")),
) -> list[MilestoneResponse]:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.planning", action="read", company_id=project.company_id
    )
    milestones = project_control_repository.list_milestones_for_project(db, project_id)
    return [MilestoneResponse.model_validate(m, from_attributes=True) for m in milestones]


@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
def create_milestone(
    project_id: uuid.UUID,
    payload: MilestoneCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.planning", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> MilestoneResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.planning", action="create", company_id=project.company_id
    )
    milestone = project_control_repository.create_milestone(
        db, project_id=project_id, name=payload.name, due_date=payload.due_date, wbs_node_id=payload.wbs_node_id
    )
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.milestone.create",
        entity_type="project.milestone",
        entity_id=milestone.id,
        company_id=project.company_id,
        project_id=project_id,
        before=None,
        after={"name": milestone.name, "dueDate": str(milestone.due_date)},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(milestone)
    return MilestoneResponse.model_validate(milestone, from_attributes=True)


@router.post("/{project_id}/budgets/baseline", response_model=BudgetResponse, status_code=201)
def create_budget_baseline(
    project_id: uuid.UUID,
    payload: BudgetBaselineCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> BudgetResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="create", company_id=project.company_id
    )
    budget = budget_service.create_baseline(
        db,
        project_id=project_id,
        currency_code=payload.currency_code,
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
        action="project.budget.create",
        entity_type="project.budget",
        entity_id=budget.id,
        company_id=project.company_id,
        project_id=project_id,
        before=None,
        after={"version": budget.version, "status": budget.status, "currencyCode": budget.currency_code},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(budget)
    return _budget_to_response(db, budget)


@router.get("/{project_id}/budgets", response_model=list[BudgetResponse])
def list_budgets(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "read")),
) -> list[BudgetResponse]:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="read", company_id=project.company_id
    )
    budgets = budget_repository.list_budgets_for_project(db, project_id)
    return [_budget_to_response(db, b) for b in budgets]


@router.get("/{project_id}/budgets/active", response_model=BudgetResponse)
def get_active_budget(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "read")),
) -> BudgetResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="read", company_id=project.company_id
    )
    budget = budget_repository.get_active_budget(db, project_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="El proyecto todavía no tiene un budget BASELINE")
    return _budget_to_response(db, budget)


@router.get("/{project_id}/budgets/summary", response_model=BudgetSummaryResponse)
def get_budget_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "read")),
) -> BudgetSummaryResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="read", company_id=project.company_id
    )
    summary = budget_service.compute_summary(db, project_id=project_id)
    return BudgetSummaryResponse(
        authorized=summary.authorized,
        committed=summary.committed,
        accrued=summary.accrued,
        paid=summary.paid,
        available=summary.available,
        advances=summary.advances,
        contract_commitment=summary.contract_commitment,
        standalone_po_commitment=summary.standalone_po_commitment,
        po_under_contract=summary.po_under_contract,
        open_commitment=summary.open_commitment,
    )


@router.get("/{project_id}/forecast", response_model=ForecastResponse)
def get_forecast(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.budget", "read")),
) -> ForecastResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.budget", action="read", company_id=project.company_id
    )
    snapshot = forecast_service.compute_forecast(db, project_id=project_id)
    return ForecastResponse(
        bac=snapshot.bac,
        pv=snapshot.pv,
        ev=snapshot.ev,
        ac=snapshot.ac,
        cpi=snapshot.cpi,
        spi=snapshot.spi,
        etc=snapshot.etc,
        eac=snapshot.eac,
        vac=snapshot.vac,
    )


@router.get("/{project_id}/change-orders", response_model=list[ChangeOrderResponse])
def list_change_orders(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.change_order", "read")),
) -> list[ChangeOrderResponse]:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.change_order", action="read", company_id=project.company_id
    )
    change_orders = project_control_repository.list_change_orders_for_project(db, project_id)
    return [ChangeOrderResponse.model_validate(co, from_attributes=True) for co in change_orders]


@router.post("/{project_id}/change-orders", response_model=ChangeOrderResponse, status_code=201)
def create_change_order(
    project_id: uuid.UUID,
    payload: ChangeOrderCreateRequest,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
    _user=Depends(require_permission("project.change_order", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> ChangeOrderResponse:
    user, _roles = current
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.change_order", action="create", company_id=project.company_id
    )
    change_order = project_control_repository.create_change_order(
        db,
        project_id=project_id,
        reason=payload.reason,
        requested_by=user.id,
        wbs_node_id=payload.wbs_node_id,
        scope_change=payload.scope_change,
        budget_change_amount=payload.budget_change_amount,
        schedule_change_days=payload.schedule_change_days,
    )
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.change_order.create",
        entity_type="project.change_order",
        entity_id=change_order.id,
        company_id=project.company_id,
        project_id=project_id,
        before=None,
        after={"status": change_order.status, "reason": change_order.reason},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(change_order)
    return ChangeOrderResponse.model_validate(change_order, from_attributes=True)


@router.post("/change-orders/{change_order_id}/submit", response_model=ChangeOrderResponse)
def submit_change_order(
    change_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.change_order", "submit")),
    correlation_id: str = Depends(get_correlation_id),
) -> ChangeOrderResponse:
    change_order = project_control_repository.get_change_order(db, change_order_id)
    if change_order is None:
        raise HTTPException(status_code=404, detail="ChangeOrder no encontrada")
    project = _get_project_or_404(db, change_order.project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.change_order", action="submit", company_id=project.company_id
    )
    assert_project_access(
        db,
        user_id=user.id,
        resource="project.change_order",
        action="submit",
        project_id=project.id,
    )
    if change_order.status != "DRAFT":
        raise HTTPException(status_code=409, detail=f"Solo se puede enviar una ChangeOrder en DRAFT (actual: {change_order.status})")
    before_status = change_order.status
    change_order.status = "SUBMITTED"
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.change_order.submit",
        entity_type="project.change_order",
        entity_id=change_order.id,
        company_id=project.company_id,
        project_id=change_order.project_id,
        before={"status": before_status},
        after={"status": change_order.status},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(change_order)
    return ChangeOrderResponse.model_validate(change_order, from_attributes=True)


@router.post("/change-orders/{change_order_id}/approve", response_model=BudgetResponse)
def approve_change_order(
    change_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.change_order", "approve")),
    correlation_id: str = Depends(get_correlation_id),
) -> BudgetResponse:
    change_order = project_control_repository.get_change_order(db, change_order_id)
    if change_order is None:
        raise HTTPException(status_code=404, detail="ChangeOrder no encontrada")
    project = _get_project_or_404(db, change_order.project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.change_order", action="approve", company_id=project.company_id
    )
    assert_project_access(
        db,
        user_id=user.id,
        resource="project.change_order",
        action="approve",
        project_id=project.id,
    )
    before_status = change_order.status
    budget = budget_service.approve_change_order(db, change_order_id=change_order_id, approved_by=user.id, commit=False)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.change_order.approve",
        entity_type="project.change_order",
        entity_id=change_order.id,
        company_id=project.company_id,
        project_id=change_order.project_id,
        before={"status": before_status},
        after={"status": "APPROVED", "budgetId": str(budget.id)},
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(budget)
    return _budget_to_response(db, budget)


@router.get("/{project_id}/progress", response_model=list[ProgressRecordResponse])
def list_progress(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.progress", "read")),
) -> list[ProgressRecordResponse]:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.progress", action="read", company_id=project.company_id
    )
    records = project_control_repository.list_progress_for_project(db, project_id)
    return [ProgressRecordResponse.model_validate(r, from_attributes=True) for r in records]


@router.post("/{project_id}/progress", response_model=ProgressRecordResponse, status_code=201)
def create_progress(
    project_id: uuid.UUID,
    payload: ProgressRecordCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("project.progress", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> ProgressRecordResponse:
    project = _get_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="project.progress", action="create", company_id=project.company_id
    )
    assert_evidence_belongs_to_company(
        db, evidence_id=payload.evidence_id, company_id=project.company_id
    )
    record = project_control_repository.create_progress_record(
        db,
        project_id=project_id,
        record_date=payload.record_date,
        planned_percent=payload.planned_percent,
        actual_percent=payload.actual_percent,
        wbs_node_id=payload.wbs_node_id,
        description=payload.description,
        responsible=payload.responsible,
        evidence_id=payload.evidence_id,
    )
    db.flush()
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="project.progress.create",
        entity_type="project.progress",
        entity_id=record.id,
        company_id=project.company_id,
        project_id=project_id,
        before=None,
        after={
            "recordDate": str(record.record_date),
            "actualPercent": str(record.actual_percent),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(record)
    return ProgressRecordResponse.model_validate(record, from_attributes=True)
