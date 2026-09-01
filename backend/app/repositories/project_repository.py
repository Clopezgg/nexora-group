import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.cost_center import CostCenter
from app.models.crm import Customer
from app.models.project import Project
from app.models.user import User


def _resolve_manager_user(db: Session, manager_user_id: uuid.UUID | None) -> uuid.UUID | None:
    """§16: el responsable real es un usuario existente y activo."""
    if manager_user_id is None:
        return None
    manager = db.get(User, manager_user_id)
    if manager is None or not manager.is_active:
        raise InvalidFinancialReferenceError(
            "manager_user_id debe ser un usuario existente y activo"
        )
    return manager.id


def get_by_id(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def count_active_projects(db: Session) -> int:
    stmt = select(func.count()).select_from(Project).where(Project.status == "ACTIVE")
    return db.execute(stmt).scalar_one()


def count_active_projects_for_companies(db: Session, *, company_ids: list[uuid.UUID]) -> int:
    if not company_ids:
        return 0
    stmt = (
        select(func.count())
        .select_from(Project)
        .where(Project.status == "ACTIVE", Project.company_id.in_(company_ids))
    )
    return db.execute(stmt).scalar_one()


def list_projects_for_company(db: Session, company_id: uuid.UUID) -> list[Project]:
    stmt = select(Project).where(Project.company_id == company_id).order_by(Project.created_at)
    return list(db.execute(stmt).scalars())


def create_project(
    db: Session,
    *,
    company_id: uuid.UUID,
    name: str,
    code: str | None = None,
    customer_id: uuid.UUID | None = None,
    customer_ref: str | None = None,
    manager: str | None = None,
    manager_user_id: uuid.UUID | None = None,
    currency_code: str | None = None,
    cost_center_id: uuid.UUID | None = None,
    planned_start: date | None = None,
    planned_end: date | None = None,
    description: str | None = None,
    address_line_1: str | None = None,
    address_line_2: str | None = None,
    city: str | None = None,
    state_department: str | None = None,
    country: str | None = None,
    location_reference: str | None = None,
) -> Project:
    if customer_id is not None:
        customer = db.get(Customer, customer_id)
        if customer is None or customer.company_id != company_id:
            raise InvalidFinancialReferenceError(
                "customer_id debe pertenecer a la compañía propietaria"
            )
    if cost_center_id is not None:
        cost_center = db.get(CostCenter, cost_center_id)
        if cost_center is None or cost_center.company_id != company_id:
            raise InvalidFinancialReferenceError(
                "cost_center_id debe pertenecer a la compañía propietaria"
            )
    if planned_start and planned_end and planned_end < planned_start:
        raise InvalidFinancialReferenceError(
            "La fecha final prevista no puede ser anterior a la fecha de inicio"
        )
    resolved_manager_user_id = _resolve_manager_user(db, manager_user_id)
    project = Project(
        company_id=company_id,
        name=name.strip(),
        code=code.strip() if code else None,
        customer_id=customer_id,
        customer_ref=customer_ref,
        manager=manager,
        manager_user_id=resolved_manager_user_id,
        currency_code=currency_code,
        cost_center_id=cost_center_id,
        planned_start=planned_start,
        planned_end=planned_end,
        description=description,
        address_line_1=address_line_1,
        address_line_2=address_line_2,
        city=city,
        state_department=state_department,
        country=country,
        location_reference=location_reference,
        status="PLANNING",
    )
    db.add(project)
    db.flush()
    return project


def update_project(db: Session, *, project: Project, values: dict) -> Project:
    editable = {
        "name",
        "code",
        "customer_id",
        "customer_ref",
        "manager",
        "manager_user_id",
        "currency_code",
        "cost_center_id",
        "planned_start",
        "planned_end",
        "description",
        "address_line_1",
        "address_line_2",
        "city",
        "state_department",
        "country",
        "location_reference",
    }
    if "manager_user_id" in values:
        values = {
            **values,
            "manager_user_id": _resolve_manager_user(db, values["manager_user_id"]),
        }
    for key, value in values.items():
        if key in editable:
            setattr(project, key, value)
    db.flush()
    return project


def set_project_status(
    db: Session,
    *,
    project: Project,
    status: str,
    actual_end: date | None = None,
) -> Project:
    project.status = status
    if actual_end is not None:
        project.actual_end = actual_end
    db.flush()
    return project
