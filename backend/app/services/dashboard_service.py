import uuid

from sqlalchemy.orm import Session

from app.repositories import project_repository
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import permission_service


def get_summary(db: Session, *, user_id: uuid.UUID) -> DashboardSummaryResponse:
    # Los módulos de Tesorería (ingresos/egresos/saldo) llegan en una fase
    # posterior del roadmap. Hasta entonces no existen movimientos que agregar,
    # por lo que 0 es el valor real calculado, no un placeholder.
    # INV-COMP-001: `active_projects` nunca puede contar proyectos de
    # compañías a las que el usuario no tiene acceso -- solo un rol con
    # scope ANY sobre `project`/`read` (Administrator, Auditor) ve el
    # agregado real de toda la plataforma.
    if permission_service.user_has_any_company_scope(db, user_id=user_id, resource="project", action="read"):
        active_projects = project_repository.count_active_projects(db)
    else:
        company_ids = permission_service.list_user_company_ids(db, user_id=user_id)
        active_projects = project_repository.count_active_projects_for_companies(db, company_ids=company_ids)
    return DashboardSummaryResponse(
        treasury_balance=0,
        period_income=0,
        period_expense=0,
        active_projects=active_projects,
    )
