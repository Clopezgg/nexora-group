from sqlalchemy.orm import Session

from app.repositories import project_repository
from app.schemas.dashboard import DashboardSummaryResponse


def get_summary(db: Session) -> DashboardSummaryResponse:
    # Los módulos de Tesorería (ingresos/egresos/saldo) llegan en una fase
    # posterior del roadmap. Hasta entonces no existen movimientos que agregar,
    # por lo que 0 es el valor real calculado, no un placeholder.
    return DashboardSummaryResponse(
        treasury_balance=0,
        period_income=0,
        period_expense=0,
        active_projects=project_repository.count_active_projects(db),
    )
