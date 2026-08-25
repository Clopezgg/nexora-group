import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories import (
    budget_repository,
    inventory_repository,
    project_control_repository,
    project_repository,
)

"""Forecast / Earned Value (orden maestra §42, docs/BUDGET_CONTROLLING.md).

Simplificación honesta y documentada: no existe todavía un motor de
scheduling con asignación de $ por fecha, así que PV/EV se derivan del
`planned_percent`/`actual_percent` del ProgressRecord más reciente contra
BAC (Budget At Completion = AUTHORIZED del budget activo). AC consume el
costo real de emisiones de inventario posteadas al proyecto; no representa
efectivo ni se deriva de PAID. Ningún valor se inventa: si no hay
ProgressRecord todavía, PV/EV/CPI/SPI/ETC/EAC/VAC son `None` (no 0 falso,
no fake) -- la orden maestra §42 exige "solo mostrar valores calculables
con datos disponibles"."""


@dataclass
class ForecastSnapshot:
    bac: Decimal
    pv: Decimal | None
    ev: Decimal | None
    ac: Decimal
    cpi: Decimal | None
    spi: Decimal | None
    etc: Decimal | None
    eac: Decimal | None
    vac: Decimal | None


def compute_forecast(db: Session, *, project_id: uuid.UUID) -> ForecastSnapshot:
    active_budget = budget_repository.get_active_budget(db, project_id)
    bac = budget_repository.sum_authorized(db, active_budget.id) if active_budget is not None else Decimal("0")

    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} no existe")
    actuals = inventory_repository.project_actuals_by_project(db, company_id=project.company_id)
    ac = actuals.get(project_id, Decimal("0"))

    latest_progress = project_control_repository.latest_progress(db, project_id)
    if latest_progress is None:
        return ForecastSnapshot(
            bac=bac, pv=None, ev=None, ac=ac, cpi=None, spi=None, etc=None, eac=None, vac=None
        )

    pv = bac * (latest_progress.planned_percent / Decimal("100"))
    ev = bac * (latest_progress.actual_percent / Decimal("100"))

    cpi = (ev / ac) if ac > 0 else None
    spi = (ev / pv) if pv > 0 else None
    etc = ((bac - ev) / cpi) if cpi and cpi > 0 else None
    eac = (ac + etc) if etc is not None else None
    vac = (bac - eac) if eac is not None else None

    return ForecastSnapshot(bac=bac, pv=pv, ev=ev, ac=ac, cpi=cpi, spi=spi, etc=etc, eac=eac, vac=vac)
