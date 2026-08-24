import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.project import Project


def get_by_id(db: Session, project_id: uuid.UUID) -> Project | None:
    return db.get(Project, project_id)


def count_active_projects(db: Session) -> int:
    stmt = select(func.count()).select_from(Project).where(Project.status == "ACTIVE")
    return db.execute(stmt).scalar_one()
