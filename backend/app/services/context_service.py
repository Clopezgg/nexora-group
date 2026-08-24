import uuid

from sqlalchemy.orm import Session

from app.repositories import project_repository, user_context_repository
from app.schemas.context import ActiveUIContextResponse


def get_active_context(db: Session, user_id: uuid.UUID) -> ActiveUIContextResponse:
    context = user_context_repository.get_or_create(db, user_id)
    db.commit()
    project = (
        project_repository.get_by_id(db, context.active_project_id)
        if context.active_project_id
        else None
    )
    return ActiveUIContextResponse(
        active_project_id=context.active_project_id,
        active_project_name=project.name if project else None,
    )


def set_active_context(
    db: Session, user_id: uuid.UUID, active_project_id: uuid.UUID | None
) -> ActiveUIContextResponse:
    if active_project_id is not None and project_repository.get_by_id(db, active_project_id) is None:
        raise ValueError("El proyecto seleccionado no existe.")

    context = user_context_repository.set_active_project(db, user_id, active_project_id)
    db.commit()
    project = (
        project_repository.get_by_id(db, context.active_project_id)
        if context.active_project_id
        else None
    )
    return ActiveUIContextResponse(
        active_project_id=context.active_project_id,
        active_project_name=project.name if project else None,
    )
