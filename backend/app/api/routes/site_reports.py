import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.project import Project
from app.repositories import project_repository
from app.schemas.site_report import (
    DailySiteReportCreateRequest,
    DailySiteReportPhotoAttachRequest,
    DailySiteReportPhotoResponse,
    DailySiteReportResponse,
)
from app.services import audit_service, site_report_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/site-reports", tags=["site-reports"])


def _resolve_project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


def _resolve_report_or_404(db: Session, report_id: uuid.UUID):
    report = site_report_service.get_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="DailySiteReport no encontrado"
        )
    return report


@router.post("", response_model=DailySiteReportResponse, status_code=201)
def create_report(
    payload: DailySiteReportCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> DailySiteReportResponse:
    project = _resolve_project_or_404(db, payload.project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="create", company_id=project.company_id
    )
    report = site_report_service.create_report(
        db,
        project_id=payload.project_id,
        report_date=payload.report_date,
        weather=payload.weather,
        workforce_summary=payload.workforce_summary,
        activities_performed=payload.activities_performed,
        equipment_used=payload.equipment_used,
        materials_used=payload.materials_used,
        incidents=payload.incidents,
        observations=payload.observations,
        author_id=user.id,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="site.daily_report.create",
        entity_type="site.daily_report",
        entity_id=report.id,
        company_id=project.company_id,
        project_id=payload.project_id,
        before=None,
        after={"reportDate": str(report.report_date), "status": report.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return DailySiteReportResponse.model_validate(report, from_attributes=True)


@router.get("", response_model=list[DailySiteReportResponse])
def list_reports(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "read")),
) -> list[DailySiteReportResponse]:
    project = _resolve_project_or_404(db, project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="read", company_id=project.company_id
    )
    return [
        DailySiteReportResponse.model_validate(r, from_attributes=True)
        for r in site_report_service.list_reports(db, project_id=project_id)
    ]


@router.get("/{report_id}", response_model=DailySiteReportResponse)
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "read")),
) -> DailySiteReportResponse:
    report = _resolve_report_or_404(db, report_id)
    project = _resolve_project_or_404(db, report.project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="read", company_id=project.company_id
    )
    return DailySiteReportResponse.model_validate(report, from_attributes=True)


@router.post("/{report_id}/photos", response_model=DailySiteReportPhotoResponse, status_code=201)
def attach_photo(
    report_id: uuid.UUID,
    payload: DailySiteReportPhotoAttachRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> DailySiteReportPhotoResponse:
    report = _resolve_report_or_404(db, report_id)
    project = _resolve_project_or_404(db, report.project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="create", company_id=project.company_id
    )
    photo = site_report_service.add_photo(
        db, daily_site_report_id=report_id, evidence_id=payload.evidence_id, company_id=project.company_id, commit=False
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="site.daily_report.photo_add",
        entity_type="site.daily_report_photo",
        entity_id=photo.id,
        company_id=project.company_id,
        project_id=report.project_id,
        before=None,
        after={"evidenceId": str(photo.evidence_id)},
        correlation_id=correlation_id,
    )
    db.commit()
    return DailySiteReportPhotoResponse.model_validate(photo, from_attributes=True)


@router.post("/{report_id}/submit", response_model=DailySiteReportResponse)
def submit_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> DailySiteReportResponse:
    report = _resolve_report_or_404(db, report_id)
    project = _resolve_project_or_404(db, report.project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="create", company_id=project.company_id
    )
    before_status = report.status
    updated = site_report_service.submit_report(db, report_id=report_id, commit=False)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="site.daily_report.submit",
        entity_type="site.daily_report",
        entity_id=report_id,
        company_id=project.company_id,
        project_id=report.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return DailySiteReportResponse.model_validate(updated, from_attributes=True)


@router.post("/{report_id}/approve", response_model=DailySiteReportResponse)
def approve_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "approve")),
    correlation_id: str = Depends(get_correlation_id),
) -> DailySiteReportResponse:
    report = _resolve_report_or_404(db, report_id)
    project = _resolve_project_or_404(db, report.project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="approve", company_id=project.company_id
    )
    before_status = report.status
    updated = site_report_service.approve_report(db, report_id=report_id, approved_by_id=user.id, commit=False)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="site.daily_report.approve",
        entity_type="site.daily_report",
        entity_id=report_id,
        company_id=project.company_id,
        project_id=report.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return DailySiteReportResponse.model_validate(updated, from_attributes=True)


@router.post("/{report_id}/reject", response_model=DailySiteReportResponse)
def reject_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site.daily_report", "approve")),
    correlation_id: str = Depends(get_correlation_id),
) -> DailySiteReportResponse:
    report = _resolve_report_or_404(db, report_id)
    project = _resolve_project_or_404(db, report.project_id)
    assert_company_access(
        db, user_id=user.id, resource="site.daily_report", action="approve", company_id=project.company_id
    )
    before_status = report.status
    updated = site_report_service.reject_report(db, report_id=report_id, approved_by_id=user.id, commit=False)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="site.daily_report.reject",
        entity_type="site.daily_report",
        entity_id=report_id,
        company_id=project.company_id,
        project_id=report.project_id,
        before={"status": before_status},
        after={"status": updated.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return DailySiteReportResponse.model_validate(updated, from_attributes=True)
