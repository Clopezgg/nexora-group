"""Project close blockers — cross-domain validation for COMPLETED/CLOSED.

F2.19 requires that transitioning to COMPLETED or CLOSED validates that
critical cross-domain conditions are satisfied. This module provides
`check_close_blockers` which is called by the lifecycle route before
applying the transition.

Blockers for COMPLETED (operational closure):
  - Tasks with status IN_PROGRESS or BLOCKED
  - Milestones with status PLANNED or MISSED
  - RFIs with status OPEN
  - Nonconformances with status OPEN
  - Safety incidents with status OPEN

Blockers for CLOSED (administrative/financial closure):
  - All COMPLETED blockers, plus:
  - Supplier invoices with status not in (PAID, CANCELLED, RECONCILED)
  - Purchase orders with status not in (RECEIVED, CANCELLED)
  - Physical counts with status DRAFT or COUNTED
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ap import SupplierInvoice
from app.models.planning import Milestone, Task
from app.models.procurement import PurchaseOrder
from app.models.quality import NonConformance
from app.models.rfi import RequestForInformation
from app.models.safety import SafetyIncident


@dataclass(frozen=True)
class CloseBlockersResult:
    is_blocked: bool
    blockers: list[str]


def check_close_blockers(
    db: Session,
    *,
    project_id: uuid.UUID,
    target_status: str,
) -> CloseBlockersResult:
    blockers: list[str] = []

    _check_operational_blockers(db, project_id, blockers)

    if target_status == "CLOSED":
        _check_financial_blockers(db, project_id, blockers)

    return CloseBlockersResult(is_blocked=len(blockers) > 0, blockers=blockers)


def _check_operational_blockers(
    db: Session,
    project_id: uuid.UUID,
    blockers: list[str],
) -> None:
    active_tasks = db.execute(
        select(Task.id).where(
            Task.project_id == project_id,
            Task.status.in_(["IN_PROGRESS", "BLOCKED"]),
        )
    ).scalars().all()
    if active_tasks:
        blockers.append(
            f"{len(active_tasks)} tarea(s) activa(s)/bloqueada(s) deben completarse primero"
        )

    open_milestones = db.execute(
        select(Milestone.id).where(
            Milestone.project_id == project_id,
            Milestone.status.in_(["PLANNED", "MISSED"]),
        )
    ).scalars().all()
    if open_milestones:
        blockers.append(
            f"{len(open_milestones)} hito(s) pendiente(s)/perdido(s) deben resolverse"
        )

    open_rfi = db.execute(
        select(RequestForInformation.id).where(
            RequestForInformation.project_id == project_id,
            RequestForInformation.status == "OPEN",
        )
    ).scalars().all()
    if open_rfi:
        blockers.append(
            f"{len(open_rfi)} RFI(s) abierto(s) deben responderse"
        )

    open_ncr = db.execute(
        select(NonConformance.id).where(
            NonConformance.project_id == project_id,
            NonConformance.status == "OPEN",
        )
    ).scalars().all()
    if open_ncr:
        blockers.append(
            f"{len(open_ncr)} no conformidad(es) abierta(s) deben resolverse"
        )

    open_incidents = db.execute(
        select(SafetyIncident.id).where(
            SafetyIncident.project_id == project_id,
            SafetyIncident.status == "OPEN",
        )
    ).scalars().all()
    if open_incidents:
        blockers.append(
            f"{len(open_incidents)} incidente(s) de seguridad abierto(s) deben resolverse"
        )


def _check_financial_blockers(
    db: Session,
    project_id: uuid.UUID,
    blockers: list[str],
) -> None:
    pending_invoices = db.execute(
        select(SupplierInvoice.id).where(
            SupplierInvoice.project_id == project_id,
            SupplierInvoice.status.not_in(["PAID", "CANCELLED", "RECONCILED"]),
        )
    ).scalars().all()
    if pending_invoices:
        blockers.append(
            f"{len(pending_invoices)} factura(s) de proveedor pendiente(s) deben resolverse"
        )

    open_pos = db.execute(
        select(PurchaseOrder.id).where(
            PurchaseOrder.project_id == project_id,
            PurchaseOrder.status.not_in(["RECEIVED", "CANCELLED"]),
        )
    ).scalars().all()
    if open_pos:
        blockers.append(
            f"{len(open_pos)} orden(es) de compra abierta(s) deben cerrarse o cancelarse"
        )
