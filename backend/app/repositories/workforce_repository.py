import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workforce import TimeEntry, Worker


def create_worker(
    db: Session,
    *,
    company_id: uuid.UUID,
    full_name: str,
    role_title: str | None,
    standard_hourly_rate: Decimal,
) -> Worker:
    worker = Worker(
        company_id=company_id,
        full_name=full_name,
        role_title=role_title,
        standard_hourly_rate=standard_hourly_rate,
    )
    db.add(worker)
    db.flush()
    return worker


def get_worker(db: Session, worker_id: uuid.UUID) -> Worker | None:
    return db.get(Worker, worker_id)


def list_workers(db: Session, *, company_id: uuid.UUID) -> list[Worker]:
    stmt = select(Worker).where(Worker.company_id == company_id).order_by(Worker.full_name)
    return list(db.execute(stmt).scalars())


def create_time_entry(
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
    entry = TimeEntry(
        company_id=company_id,
        worker_id=worker_id,
        scope=scope,
        project_id=project_id,
        work_date=work_date,
        hours_worked=hours_worked,
        hourly_rate=hourly_rate,
    )
    db.add(entry)
    db.flush()
    return entry


def get_time_entry(db: Session, time_entry_id: uuid.UUID) -> TimeEntry | None:
    return db.get(TimeEntry, time_entry_id)


def list_time_entries(db: Session, *, company_id: uuid.UUID) -> list[TimeEntry]:
    stmt = select(TimeEntry).where(TimeEntry.company_id == company_id).order_by(TimeEntry.work_date)
    return list(db.execute(stmt).scalars())
