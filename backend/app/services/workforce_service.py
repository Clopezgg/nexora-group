import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import CrewMembershipError, InvalidTimeEntryStateError
from app.models.workforce import Crew, CrewMember, TimeEntry, Worker
from app.repositories import workforce_repository
from app.services.financial_validation_service import (
    assert_operation_scope,
    assert_project_belongs_to_company,
)

"""Workforce / Time (orden maestra §65-66). `labor_cost` se calcula SIEMPRE
en el servidor al aprobar (hourly_rate * approved_hours) -- nunca se acepta
del cliente (CLAUDE.md: no hardcoded financial data). El costo se atribuye
al Project como costo de mano de obra; el pago real del trabajador (nómina/
Treasury) queda fuera de alcance de este track (documentado como deuda
intencional, ver docs/ENTERPRISE_RESOURCES.md)."""


def create_worker(
    db: Session,
    *,
    company_id: uuid.UUID,
    full_name: str,
    role_title: str | None,
    standard_hourly_rate: Decimal,
) -> Worker:
    worker = workforce_repository.create_worker(
        db,
        company_id=company_id,
        full_name=full_name,
        role_title=role_title,
        standard_hourly_rate=standard_hourly_rate,
    )
    db.commit()
    db.refresh(worker)
    return worker


def list_workers(db: Session, *, company_id: uuid.UUID) -> list[Worker]:
    return workforce_repository.list_workers(db, company_id=company_id)


def submit_time_entry(
    db: Session,
    *,
    company_id: uuid.UUID,
    worker_id: uuid.UUID,
    scope: str,
    project_id: uuid.UUID | None,
    work_date: date,
    hours_worked: Decimal,
    hourly_rate: Decimal,
) -> TimeEntry:
    assert_operation_scope(scope, project_id)
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    worker = workforce_repository.get_worker(db, worker_id)
    if worker is None or worker.company_id != company_id:
        raise ValueError(f"Worker {worker_id} no existe en la company {company_id}")

    entry = workforce_repository.create_time_entry(
        db,
        company_id=company_id,
        worker_id=worker_id,
        scope=scope,
        project_id=project_id,
        work_date=work_date,
        hours_worked=hours_worked,
        hourly_rate=hourly_rate,
    )
    db.commit()
    db.refresh(entry)
    return entry


def list_time_entries(db: Session, *, company_id: uuid.UUID) -> list[TimeEntry]:
    return workforce_repository.list_time_entries(db, company_id=company_id)


def approve_time_entry(
    db: Session,
    *,
    time_entry_id: uuid.UUID,
    approved_by_id: uuid.UUID,
    approved_hours: Decimal | None = None,
) -> TimeEntry:
    """INV-WFC-001: `labor_cost` = hourly_rate * approved_hours, calculado
    aquí -- nunca recibido como input. Solo se puede aprobar/rechazar un
    TimeEntry SUBMITTED (decisión única, no reversible por este servicio)."""
    entry = workforce_repository.get_time_entry(db, time_entry_id)
    if entry is None:
        raise ValueError(f"TimeEntry {time_entry_id} no existe")
    if entry.status != "SUBMITTED":
        raise InvalidTimeEntryStateError(
            f"Solo se puede aprobar un TimeEntry SUBMITTED (estado actual: {entry.status})"
        )
    hours = approved_hours if approved_hours is not None else entry.hours_worked
    entry.approved_hours = hours
    entry.labor_cost = (entry.hourly_rate * hours).quantize(Decimal("0.01"))
    entry.status = "APPROVED"
    entry.approved_by_id = approved_by_id
    entry.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return entry


def reject_time_entry(db: Session, *, time_entry_id: uuid.UUID, approved_by_id: uuid.UUID) -> TimeEntry:
    entry = workforce_repository.get_time_entry(db, time_entry_id)
    if entry is None:
        raise ValueError(f"TimeEntry {time_entry_id} no existe")
    if entry.status != "SUBMITTED":
        raise InvalidTimeEntryStateError(
            f"Solo se puede rechazar un TimeEntry SUBMITTED (estado actual: {entry.status})"
        )
    entry.status = "REJECTED"
    entry.approved_by_id = approved_by_id
    entry.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return entry


def create_crew(
    db: Session, *, company_id: uuid.UUID, name: str, project_id: uuid.UUID | None = None
) -> Crew:
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    crew = workforce_repository.create_crew(
        db, company_id=company_id, project_id=project_id, name=name
    )
    db.commit()
    db.refresh(crew)
    return crew


def list_crews(db: Session, *, company_id: uuid.UUID) -> list[Crew]:
    return workforce_repository.list_crews(db, company_id=company_id)


def list_crew_members(db: Session, *, crew_id: uuid.UUID) -> list[Worker]:
    return workforce_repository.list_crew_members(db, crew_id=crew_id)


def add_crew_member(db: Session, *, crew_id: uuid.UUID, worker_id: uuid.UUID) -> CrewMember:
    crew = workforce_repository.get_crew(db, crew_id)
    if crew is None:
        raise ValueError(f"Crew {crew_id} no existe")
    worker = workforce_repository.get_worker(db, worker_id)
    if worker is None or worker.company_id != crew.company_id:
        raise ValueError(f"Worker {worker_id} no existe en la company de la cuadrilla")
    if workforce_repository.get_crew_member(db, crew_id=crew_id, worker_id=worker_id) is not None:
        raise CrewMembershipError("Este trabajador ya es miembro de la cuadrilla")
    member = workforce_repository.add_crew_member(db, crew_id=crew_id, worker_id=worker_id)
    db.commit()
    db.refresh(member)
    return member


def remove_crew_member(db: Session, *, crew_id: uuid.UUID, worker_id: uuid.UUID) -> None:
    member = workforce_repository.get_crew_member(db, crew_id=crew_id, worker_id=worker_id)
    if member is None:
        raise CrewMembershipError("Este trabajador no es miembro de la cuadrilla")
    workforce_repository.remove_crew_member(db, member)
    db.commit()
