import uuid

from sqlalchemy.orm import Session

from app.domain.errors import NotAuthorizedError
from app.repositories import project_repository, user_context_repository
from app.schemas.context import ActiveUIContextResponse
from app.services.permission_service import assert_project_access


def _get_authorized_project(
    db: Session, user_id: uuid.UUID, active_project_id: uuid.UUID
):
    project = project_repository.get_by_id(db, active_project_id)
    if project is None:
        raise ValueError("El proyecto seleccionado no existe o no está disponible.")
    try:
        assert_project_access(
            db,
            user_id=user_id,
            resource="project",
            action="read",
            project_id=active_project_id,
        )
    except NotAuthorizedError as error:
        # Contexto de UI no concede permisos. Nunca debe convertirse en un
        # canal para descubrir o seleccionar un proyecto fuera del alcance
        # efectivo del usuario.
        raise ValueError("El proyecto seleccionado no existe o no está disponible.") from error
    return project


def get_active_context(db: Session, user_id: uuid.UUID) -> ActiveUIContextResponse:
    # Reading the topbar context must remain a read-only request. Previously
    # this path called get_or_create() and committed on every GET, adding a DB
    # write/transaction to every authenticated shell load.
    context = user_context_repository.get(db, user_id)
    if context is None or context.active_project_id is None:
        return ActiveUIContextResponse(active_project_id=None, active_project_name=None)

    try:
        project = _get_authorized_project(db, user_id, context.active_project_id)
    except ValueError:
        # A previously valid context may become stale after company/project
        # access is revoked. GET remains side-effect free; expose no stale
        # context rather than leaking a project name across the new boundary.
        return ActiveUIContextResponse(active_project_id=None, active_project_name=None)

    return ActiveUIContextResponse(
        active_project_id=project.id,
        active_project_name=project.name,
    )


def set_active_context(
    db: Session, user_id: uuid.UUID, active_project_id: uuid.UUID | None
) -> ActiveUIContextResponse:
    project = (
        _get_authorized_project(db, user_id, active_project_id)
        if active_project_id is not None
        else None
    )

    context = user_context_repository.set_active_project(db, user_id, active_project_id)
    db.commit()
    return ActiveUIContextResponse(
        active_project_id=context.active_project_id,
        active_project_name=project.name if project else None,
    )
