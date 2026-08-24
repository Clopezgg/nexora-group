import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.change_order import ChangeOrder
from app.models.planning import Milestone, Task
from app.models.progress import ProgressRecord
from app.models.wbs import WBSNode

"""Repositorio de Project Control (WBS, Planning, Change Orders, Progress).
Budget vive en budget_repository.py / budget_service.py porque su lógica de
versionado es más rica que un CRUD simple."""


def list_wbs_for_project(db: Session, project_id: uuid.UUID) -> list[WBSNode]:
    stmt = select(WBSNode).where(WBSNode.project_id == project_id).order_by(WBSNode.code)
    return list(db.execute(stmt).scalars())


def create_wbs_node(
    db: Session,
    *,
    project_id: uuid.UUID,
    code: str,
    name: str,
    parent_id: uuid.UUID | None = None,
    manager: str | None = None,
    planned_start: date | None = None,
    planned_finish: date | None = None,
) -> WBSNode:
    level = 0
    if parent_id is not None:
        parent = db.get(WBSNode, parent_id)
        if parent is None:
            raise ValueError(f"WBSNode padre {parent_id} no existe")
        level = parent.level + 1
    node = WBSNode(
        project_id=project_id,
        parent_id=parent_id,
        code=code,
        name=name,
        level=level,
        manager=manager,
        planned_start=planned_start,
        planned_finish=planned_finish,
        status="PLANNING",
    )
    db.add(node)
    db.flush()
    return node


def create_task(
    db: Session,
    *,
    project_id: uuid.UUID,
    name: str,
    wbs_node_id: uuid.UUID | None = None,
    owner: str | None = None,
    planned_start: date | None = None,
    planned_end: date | None = None,
    depends_on_task_id: uuid.UUID | None = None,
) -> Task:
    task = Task(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        name=name,
        owner=owner,
        planned_start=planned_start,
        planned_end=planned_end,
        depends_on_task_id=depends_on_task_id,
        status="PLANNED",
    )
    db.add(task)
    db.flush()
    return task


def list_tasks_for_project(db: Session, project_id: uuid.UUID) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id).order_by(Task.planned_start)
    return list(db.execute(stmt).scalars())


def create_milestone(
    db: Session,
    *,
    project_id: uuid.UUID,
    name: str,
    due_date: date,
    wbs_node_id: uuid.UUID | None = None,
) -> Milestone:
    milestone = Milestone(
        project_id=project_id, wbs_node_id=wbs_node_id, name=name, due_date=due_date, status="PLANNED"
    )
    db.add(milestone)
    db.flush()
    return milestone


def list_milestones_for_project(db: Session, project_id: uuid.UUID) -> list[Milestone]:
    stmt = select(Milestone).where(Milestone.project_id == project_id).order_by(Milestone.due_date)
    return list(db.execute(stmt).scalars())


def create_change_order(
    db: Session,
    *,
    project_id: uuid.UUID,
    reason: str,
    requested_by: uuid.UUID,
    wbs_node_id: uuid.UUID | None = None,
    scope_change: str | None = None,
    budget_change_amount: Decimal = Decimal("0"),
    schedule_change_days: int | None = None,
) -> ChangeOrder:
    change_order = ChangeOrder(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        reason=reason,
        scope_change=scope_change,
        budget_change_amount=budget_change_amount,
        schedule_change_days=schedule_change_days,
        requested_by=requested_by,
        status="DRAFT",
    )
    db.add(change_order)
    db.flush()
    return change_order


def list_change_orders_for_project(db: Session, project_id: uuid.UUID) -> list[ChangeOrder]:
    stmt = (
        select(ChangeOrder).where(ChangeOrder.project_id == project_id).order_by(ChangeOrder.created_at)
    )
    return list(db.execute(stmt).scalars())


def get_change_order(db: Session, change_order_id: uuid.UUID) -> ChangeOrder | None:
    return db.get(ChangeOrder, change_order_id)


def create_progress_record(
    db: Session,
    *,
    project_id: uuid.UUID,
    record_date: date,
    planned_percent: Decimal,
    actual_percent: Decimal,
    wbs_node_id: uuid.UUID | None = None,
    description: str | None = None,
    responsible: str | None = None,
    evidence_ref: str | None = None,
) -> ProgressRecord:
    record = ProgressRecord(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        record_date=record_date,
        planned_percent=planned_percent,
        actual_percent=actual_percent,
        description=description,
        responsible=responsible,
        evidence_ref=evidence_ref,
    )
    db.add(record)
    db.flush()
    return record


def list_progress_for_project(db: Session, project_id: uuid.UUID) -> list[ProgressRecord]:
    stmt = (
        select(ProgressRecord)
        .where(ProgressRecord.project_id == project_id)
        .order_by(ProgressRecord.record_date)
    )
    return list(db.execute(stmt).scalars())


def latest_progress(db: Session, project_id: uuid.UUID) -> ProgressRecord | None:
    stmt = (
        select(ProgressRecord)
        .where(ProgressRecord.project_id == project_id)
        .order_by(ProgressRecord.record_date.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()
