import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import CrewMembershipError, InvalidTimeEntryStateError
from app.models.workforce import Crew, CrewMember, TimeEntry, Worker
from app.repositories import workforce_repository
from app.services import resource_posting_service
from app.services.financial_validation_service import (
    assert_operation_scope,
    assert_project_belongs_to_company,
)

"""Workforce / Time.

`labor_cost` is always calculated server-side. Approval also posts the cost to
GL using the company's LABOR mapping; no account code is embedded here.
"""


def create_worker(
    db: Session,
    *,
    company_id: uuid.UUID,
    full_name: str,
    role_title: str | None,
    standard_hourly_rate: Decimal,
    commit: bool = True,
) -> Worker:
    worker = workforce_repository.create_worker(
        db,
        company_id=company_id,
        full_name=full_name,
        role_title=role_title,
        standard_hourly_rate=standard_hourly_rate,
    )
    if commit:
        db.commit()
        db.refresh(worker)
    else:
        db.flush()
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
    commit: bool = True,
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
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def list_time_entries(db: Session, *, company_id: uuid.UUID) -> list[TimeEntry]:
    return workforce_repository.list_time_entries(db, company_id=company_id)


def approve_time_entry(
    db: Session,
    *,
    time_entry_id: uuid.UUID,
    approved_by_id: uuid.UUID,
    approved_hours: Decimal | None = None,
    commit: bool = True,
) -> TimeEntry:
    """Approve once and atomically accrue the server-computed labor cost."""
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
    db.flush()
    resource_posting_service.post_resource_cost(
        db,
        company_id=entry.company_id,
        source_type="LABOR",
        source_id=entry.id,
        amount=entry.labor_cost,
        scope=entry.scope,
        effective_date=entry.work_date,
        project_id=entry.project_id,
        description=f"Mano de obra aprobada · {entry.work_date.isoformat()}",
    )
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def reject_time_entry(db: Session, *, time_entry_id: uuid.UUID, approved_by_id: uuid.UUID, commit: bool = True) -> TimeEntry:
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
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def create_crew(
    db: Session, *, company_id: uuid.UUID, name: str, project_id: uuid.UUID | None = None, commit: bool = True,
) -> Crew:
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    crew = workforce_repository.create_crew(
        db, company_id=company_id, project_id=project_id, name=name
    )
    if commit:
        db.commit()
        db.refresh(crew)
    else:
        db.flush()
    return crew


def list_crews(db: Session, *, company_id: uuid.UUID) -> list[Crew]:
    return workforce_repository.list_crews(db, company_id=company_id)


def list_crew_members(db: Session, *, crew_id: uuid.UUID) -> list[Worker]:
    return workforce_repository.list_crew_members(db, crew_id=crew_id)


def add_crew_member(db: Session, *, crew_id: uuid.UUID, worker_id: uuid.UUID, commit: bool = True) -> CrewMember:
    crew = workforce_repository.get_crew(db, crew_id)
    if crew is None:
        raise ValueError(f"Crew {crew_id} no existe")
    worker = workforce_repository.get_worker(db, worker_id)
    if worker is None or worker.company_id != crew.company_id:
        raise ValueError(f"Worker {worker_id} no existe en la company de la cuadrilla")
    if workforce_repository.get_crew_member(db, crew_id=crew_id, worker_id=worker_id) is not None:
        raise CrewMembershipError("Este trabajador ya es miembro de la cuadrilla")
    member = workforce_repository.add_crew_member(db, crew_id=crew_id, worker_id=worker_id)
    if commit:
        db.commit()
        db.refresh(member)
    else:
        db.flush()
    return member


def remove_crew_member(db: Session, *, crew_id: uuid.UUID, worker_id: uuid.UUID, commit: bool = True) -> None:
    member = workforce_repository.get_crew_member(db, crew_id=crew_id, worker_id=worker_id)
    if member is None:
        raise CrewMembershipError("Este trabajador no es miembro de la cuadrilla")
    workforce_repository.remove_crew_member(db, member)
    if commit:
        db.commit()
    else:
        db.flush()