import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.site_report import DailySiteReport, DailySiteReportPhoto


def create_report(
    db: Session,
    *,
    project_id: uuid.UUID,
    report_date: date,
    weather: str | None,
    workforce_summary: str | None,
    activities_performed: str,
    equipment_used: str | None,
    materials_used: str | None,
    incidents: str | None,
    observations: str | None,
    author_id: uuid.UUID,
) -> DailySiteReport:
    report = DailySiteReport(
        project_id=project_id,
        report_date=report_date,
        weather=weather,
        workforce_summary=workforce_summary,
        activities_performed=activities_performed,
        equipment_used=equipment_used,
        materials_used=materials_used,
        incidents=incidents,
        observations=observations,
        author_id=author_id,
        status="DRAFT",
    )
    db.add(report)
    db.flush()
    return report


def get_report(db: Session, report_id: uuid.UUID) -> DailySiteReport | None:
    stmt = (
        select(DailySiteReport)
        .options(selectinload(DailySiteReport.photos))
        .where(DailySiteReport.id == report_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_reports_for_project(db: Session, project_id: uuid.UUID) -> list[DailySiteReport]:
    stmt = (
        select(DailySiteReport)
        .options(selectinload(DailySiteReport.photos))
        .where(DailySiteReport.project_id == project_id)
        .order_by(DailySiteReport.report_date.desc())
    )
    return list(db.execute(stmt).scalars())


def add_photo(
    db: Session, *, daily_site_report_id: uuid.UUID, evidence_id: uuid.UUID
) -> DailySiteReportPhoto:
    photo = DailySiteReportPhoto(daily_site_report_id=daily_site_report_id, evidence_id=evidence_id)
    db.add(photo)
    db.flush()
    return photo
