import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.domain.errors import InvalidSiteReportStateError
from app.models.site_report import DailySiteReport, DailySiteReportPhoto
from app.repositories import site_report_repository
from app.services.financial_validation_service import assert_evidence_belongs_to_company

"""Daily Site Report (bloque CONSTRUCTION CONTROL, orden maestra §81,
NXR-REQ-0081). Flujo de aprobación DRAFT -> SUBMITTED -> APPROVED/REJECTED,
mismo criterio de único-estado-terminal-por-transición que TimeEntry
(workforce_service) y ChangeOrder (budget_service): solo se puede
enviar/aprobar/rechazar desde el estado previo correcto, nunca se salta un
paso ni se reabre uno ya decidido."""


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
    commit: bool = True,
) -> DailySiteReport:
    report = site_report_repository.create_report(
        db,
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
    )
    if commit:
        db.commit()
        return site_report_repository.get_report(db, report.id)
    else:
        db.flush()
        return report


def get_report(db: Session, report_id: uuid.UUID) -> DailySiteReport | None:
    return site_report_repository.get_report(db, report_id)


def list_reports(db: Session, *, project_id: uuid.UUID) -> list[DailySiteReport]:
    return site_report_repository.list_reports_for_project(db, project_id)


def add_photo(
    db: Session, *, daily_site_report_id: uuid.UUID, evidence_id: uuid.UUID, company_id: uuid.UUID,
    commit: bool = True,
) -> DailySiteReportPhoto:
    assert_evidence_belongs_to_company(db, evidence_id=evidence_id, company_id=company_id)
    photo = site_report_repository.add_photo(
        db, daily_site_report_id=daily_site_report_id, evidence_id=evidence_id
    )
    if commit:
        db.commit()
        db.refresh(photo)
    else:
        db.flush()
    return photo


def submit_report(db: Session, *, report_id: uuid.UUID, commit: bool = True) -> DailySiteReport:
    report = site_report_repository.get_report(db, report_id)
    if report is None:
        raise ValueError(f"DailySiteReport {report_id} no existe")
    if report.status != "DRAFT":
        raise InvalidSiteReportStateError(
            f"Solo se puede enviar un DailySiteReport DRAFT (estado actual: {report.status})"
        )
    report.status = "SUBMITTED"
    if commit:
        db.commit()
        db.refresh(report)
    else:
        db.flush()
    return report


def approve_report(db: Session, *, report_id: uuid.UUID, approved_by_id: uuid.UUID, commit: bool = True) -> DailySiteReport:
    report = site_report_repository.get_report(db, report_id)
    if report is None:
        raise ValueError(f"DailySiteReport {report_id} no existe")
    if report.status != "SUBMITTED":
        raise InvalidSiteReportStateError(
            f"Solo se puede aprobar un DailySiteReport SUBMITTED (estado actual: {report.status})"
        )
    report.status = "APPROVED"
    report.approved_by_id = approved_by_id
    report.approved_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
        db.refresh(report)
    else:
        db.flush()
    return report


def reject_report(db: Session, *, report_id: uuid.UUID, approved_by_id: uuid.UUID, commit: bool = True) -> DailySiteReport:
    report = site_report_repository.get_report(db, report_id)
    if report is None:
        raise ValueError(f"DailySiteReport {report_id} no existe")
    if report.status != "SUBMITTED":
        raise InvalidSiteReportStateError(
            f"Solo se puede rechazar un DailySiteReport SUBMITTED (estado actual: {report.status})"
        )
    report.status = "REJECTED"
    report.approved_by_id = approved_by_id
    report.approved_at = datetime.now(timezone.utc)
    if commit:
        db.commit()
        db.refresh(report)
    else:
        db.flush()
    return report
