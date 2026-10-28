import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.company import Company
from app.models.cost_center import CostCenter
from app.models.crm import Customer
from app.models.permission import UserCompanyAccess
from app.models.project import Project
from app.models.user import User


def _resolve_manager_user(
    db: Session, *, company_id: uuid.UUID, manager_user_id: uuid.UUID | None
) -> uuid.UUID | None:
    """§16: responsable activo y explícitamente asignado a la compañía."""
    if manager_user_id is None:
        return None
    manager = db.get(User, manager_user_id)
    if manager is None or not manager.is_active:
        raise InvalidFinancialReferenceError(
            "manager_user_id debe ser un usuario existente y activo"
        )
    access = db.execute(
        select(UserCompanyAccess.id).where(
            UserCompanyAccess.user_id == manager_user_id,
            UserCompanyAccess.company_id == company_id,
        )
    ).scalar_one_or_none()
    if access is None:
        raise InvalidFinancialReferenceError(
            "manager_user_id debe tener acceso explícito a la compañía del proyecto"
        )
    return manager.id


def _validate_project_company(
    db: Session, *, company_id: uuid.UUID, currency_code: str | None
) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise InvalidFinancialReferenceError("company_id debe referenciar una compañía existente")
    if (
        currency_code is not None
        and company.functional_currency_code is not None
        and currency_code != company.functional_currency_code
    ):
        raise InvalidFinancialReferenceError(
            "currency_code del proyecto debe coincidir con la moneda funcional de la compañía"
        )
    return company


def _validate_references(
    db: Session,
    *,
    company_id: uuid.UUID,
    currency_code: str | None,
    customer_id: uuid.UUID | None,
    cost_center_id: uuid.UUID | None,
    manager_user_id: uuid.UUID | None,
) -> None:
    _validate_project_company(db, company_id=company_id, currency_code=currency_code)
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
    _resolve_manager_user(db, company_id=company_id, manager_user_id=manager_user_id)


def get_by_id(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def get_by_id_for_update(db: Session, project_id: uuid.UUID) -> Project | None:
    """Lock the project row for an authoritative lifecycle transition."""
    return db.execute(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()


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
    _validate_references(
        db,
        company_id=company_id,
        currency_code=currency_code,
        customer_id=customer_id,
        cost_center_id=cost_center_id,
        manager_user_id=manager_user_id,
    )
    if planned_start and planned_end and planned_end < planned_start:
        raise InvalidFinancialReferenceError(
            "La fecha final prevista no puede ser anterior a la fecha de inicio"
        )
    project = Project(
        company_id=company_id,
        name=name.strip(),
        code=code.strip() if code else None,
        customer_id=customer_id,
        customer_ref=customer_ref,
        manager=manager,
        manager_user_id=manager_user_id,
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
    candidate = {key: value for key, value in values.items() if key in editable}
    effective_customer = candidate.get("customer_id", project.customer_id)
    effective_cost_center = candidate.get("cost_center_id", project.cost_center_id)
    effective_manager = candidate.get("manager_user_id", project.manager_user_id)
    effective_currency = candidate.get("currency_code", project.currency_code)
    _validate_references(
        db,
        company_id=project.company_id,
        currency_code=effective_currency,
        customer_id=effective_customer,
        cost_center_id=effective_cost_center,
        manager_user_id=effective_manager,
    )
    effective_start = candidate.get("planned_start", project.planned_start)
    effective_end = candidate.get("planned_end", project.planned_end)
    if effective_start and effective_end and effective_end < effective_start:
        raise InvalidFinancialReferenceError(
            "La fecha final prevista no puede ser anterior a la fecha de inicio"
        )
    for key, value in candidate.items():
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
