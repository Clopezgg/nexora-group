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


def get_wbs_node(db: Session, node_id: uuid.UUID) -> WBSNode | None:
    return db.get(WBSNode, node_id)


def _assert_wbs_for_project(
    db: Session, *, project_id: uuid.UUID, wbs_node_id: uuid.UUID | None
) -> WBSNode | None:
    if wbs_node_id is None:
        return None
    node = db.get(WBSNode, wbs_node_id)
    if node is None:
        raise ValueError(f"WBSNode {wbs_node_id} no existe")
    if node.project_id != project_id:
        raise ValueError("El WBS seleccionado debe pertenecer al mismo proyecto")
    return node


def _validated_parent(
    db: Session,
    *,
    project_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    node_id: uuid.UUID | None = None,
) -> WBSNode | None:
    if parent_id is None:
        return None
    if node_id is not None and parent_id == node_id:
        raise ValueError("Un nodo WBS no puede ser su propio padre")
    parent = _assert_wbs_for_project(db, project_id=project_id, wbs_node_id=parent_id)
    if node_id is not None:
        cursor: WBSNode | None = parent
        visited: set[uuid.UUID] = set()
        while cursor is not None:
            if cursor.id == node_id:
                raise ValueError("La jerarquía WBS no puede contener ciclos")
            if cursor.id in visited:
                raise ValueError("La jerarquía WBS existente contiene un ciclo")
            visited.add(cursor.id)
            cursor = db.get(WBSNode, cursor.parent_id) if cursor.parent_id else None
    return parent


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
    parent = _validated_parent(db, project_id=project_id, parent_id=parent_id)
    level = parent.level + 1 if parent is not None else 0
    node = WBSNode(
        project_id=project_id,
        parent_id=parent_id,
        code=code.strip(),
        name=name.strip(),
        level=level,
        manager=manager,
        planned_start=planned_start,
        planned_finish=planned_finish,
        status="PLANNING",
    )
    db.add(node)
    db.flush()
    return node


def update_wbs_node(db: Session, *, node: WBSNode, values: dict) -> WBSNode:
    new_parent_id = values.get("parent_id", node.parent_id)
    parent = _validated_parent(
        db, project_id=node.project_id, parent_id=new_parent_id, node_id=node.id
    )
    effective_start = values.get("planned_start", node.planned_start)
    effective_finish = values.get("planned_finish", node.planned_finish)
    if effective_start and effective_finish and effective_finish < effective_start:
        raise ValueError("La fecha final del WBS no puede ser anterior a la fecha de inicio")

    new_level = parent.level + 1 if parent is not None else 0
    level_delta = new_level - node.level
    for field in (
        "code",
        "name",
        "manager",
        "planned_start",
        "planned_finish",
        "status",
        "progress_percent",
    ):
        if field in values:
            setattr(node, field, values[field])
    if "parent_id" in values:
        node.parent_id = new_parent_id
    node.level = new_level

    if level_delta:
        descendants = list_wbs_for_project(db, node.project_id)
        children_by_parent: dict[uuid.UUID, list[WBSNode]] = {}
        for candidate in descendants:
            if candidate.parent_id is not None:
                children_by_parent.setdefault(candidate.parent_id, []).append(candidate)
        stack = list(children_by_parent.get(node.id, []))
        while stack:
            descendant = stack.pop()
            descendant.level += level_delta
            stack.extend(children_by_parent.get(descendant.id, []))
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
    _assert_wbs_for_project(db, project_id=project_id, wbs_node_id=wbs_node_id)
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
    _assert_wbs_for_project(db, project_id=project_id, wbs_node_id=wbs_node_id)
    milestone = Milestone(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        name=name,
        due_date=due_date,
        status="PLANNED",
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
    contract_change_amount: Decimal = Decimal("0"),
    schedule_change_days: int | None = None,
) -> ChangeOrder:
    _assert_wbs_for_project(db, project_id=project_id, wbs_node_id=wbs_node_id)
    change_order = ChangeOrder(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        reason=reason,
        scope_change=scope_change,
        budget_change_amount=budget_change_amount,
        contract_change_amount=contract_change_amount,
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
    evidence_id: uuid.UUID | None = None,
) -> ProgressRecord:
    _assert_wbs_for_project(db, project_id=project_id, wbs_node_id=wbs_node_id)
    record = ProgressRecord(
        project_id=project_id,
        wbs_node_id=wbs_node_id,
        record_date=record_date,
        planned_percent=planned_percent,
        actual_percent=actual_percent,
        description=description,
        responsible=responsible,
        evidence_id=evidence_id,
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
