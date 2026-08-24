import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project


def get_by_id(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def count_active_projects(db: Session) -> int:
    stmt = select(func.count()).select_from(Project).where(Project.status == "ACTIVE")
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
    customer_ref: str | None = None,
    manager: str | None = None,
    currency_code: str | None = None,
    cost_center_id: uuid.UUID | None = None,
    planned_start: date | None = None,
    planned_end: date | None = None,
    description: str | None = None,
) -> Project:
    project = Project(
        company_id=company_id,
        name=name,
        code=code,
        customer_ref=customer_ref,
        manager=manager,
        currency_code=currency_code,
        cost_center_id=cost_center_id,
        planned_start=planned_start,
        planned_end=planned_end,
        description=description,
        status="PLANNING",
    )
    db.add(project)
    db.flush()
    return project
