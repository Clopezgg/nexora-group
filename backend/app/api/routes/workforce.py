import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import workforce_repository
from app.schemas.workforce import (
    CrewCreateRequest,
    CrewMemberAddRequest,
    CrewMemberResponse,
    CrewResponse,
    CrewWithMembersResponse,
    TimeEntryApproveRequest,
    TimeEntryCreateRequest,
    TimeEntryResponse,
    WorkerCreateRequest,
    WorkerResponse,
)
from app.services import workforce_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/workforce", tags=["workforce"])


def _resolve_time_entry(db: Session, time_entry_id: uuid.UUID):
    entry = workforce_repository.get_time_entry(db, time_entry_id)
    if entry is None:
        raise ValueError(f"TimeEntry {time_entry_id} no existe")
    return entry


def _resolve_crew(db: Session, crew_id: uuid.UUID):
    crew = workforce_repository.get_crew(db, crew_id)
    if crew is None:
        raise ValueError(f"Crew {crew_id} no existe")
    return crew


@router.post("/workers", response_model=WorkerResponse, status_code=201)
def create_worker(
    payload: WorkerCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.worker", "create")),
) -> WorkerResponse:
    assert_company_access(
        db, user_id=user.id, resource="workforce.worker", action="create", company_id=payload.company_id
    )
    worker = workforce_service.create_worker(
        db,
        company_id=payload.company_id,
        full_name=payload.full_name,
        role_title=payload.role_title,
        standard_hourly_rate=payload.standard_hourly_rate,
    )
    return WorkerResponse.model_validate(worker, from_attributes=True)


@router.get("/workers", response_model=list[WorkerResponse])
def list_workers(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.worker", "read")),
) -> list[WorkerResponse]:
    assert_company_access(
        db, user_id=user.id, resource="workforce.worker", action="read", company_id=company_id
    )
    return [
        WorkerResponse.model_validate(worker, from_attributes=True)
        for worker in workforce_service.list_workers(db, company_id=company_id)
    ]


@router.post("/time-entries", response_model=TimeEntryResponse, status_code=201)
def submit_time_entry(
    payload: TimeEntryCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.time_entry", "create")),
) -> TimeEntryResponse:
    assert_company_access(
        db, user_id=user.id, resource="workforce.time_entry", action="create", company_id=payload.company_id
    )
    entry = workforce_service.submit_time_entry(
        db,
        company_id=payload.company_id,
        worker_id=payload.worker_id,
        scope=payload.scope,
        project_id=payload.project_id,
        work_date=payload.work_date,
        hours_worked=payload.hours_worked,
        hourly_rate=payload.hourly_rate,
    )
    return TimeEntryResponse.model_validate(entry, from_attributes=True)


@router.get("/time-entries", response_model=list[TimeEntryResponse])
def list_time_entries(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.time_entry", "read")),
) -> list[TimeEntryResponse]:
    assert_company_access(
        db, user_id=user.id, resource="workforce.time_entry", action="read", company_id=company_id
    )
    return [
        TimeEntryResponse.model_validate(entry, from_attributes=True)
        for entry in workforce_service.list_time_entries(db, company_id=company_id)
    ]


@router.post("/time-entries/{time_entry_id}/approve", response_model=TimeEntryResponse)
def approve_time_entry(
    time_entry_id: uuid.UUID,
    payload: TimeEntryApproveRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.time_entry", "approve")),
) -> TimeEntryResponse:
    entry = _resolve_time_entry(db, time_entry_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="workforce.time_entry",
        action="approve",
        company_id=entry.company_id,
    )
    entry = workforce_service.approve_time_entry(
        db, time_entry_id=time_entry_id, approved_by_id=user.id, approved_hours=payload.approved_hours
    )
    return TimeEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/time-entries/{time_entry_id}/reject", response_model=TimeEntryResponse)
def reject_time_entry(
    time_entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.time_entry", "approve")),
) -> TimeEntryResponse:
    entry = _resolve_time_entry(db, time_entry_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="workforce.time_entry",
        action="approve",
        company_id=entry.company_id,
    )
    entry = workforce_service.reject_time_entry(db, time_entry_id=time_entry_id, approved_by_id=user.id)
    return TimeEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/crews", response_model=CrewResponse, status_code=201)
def create_crew(
    payload: CrewCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.crew", "create")),
) -> CrewResponse:
    assert_company_access(
        db, user_id=user.id, resource="workforce.crew", action="create", company_id=payload.company_id
    )
    crew = workforce_service.create_crew(
        db, company_id=payload.company_id, name=payload.name, project_id=payload.project_id
    )
    return CrewResponse.model_validate(crew, from_attributes=True)


@router.get("/crews", response_model=list[CrewResponse])
def list_crews(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.crew", "read")),
) -> list[CrewResponse]:
    assert_company_access(
        db, user_id=user.id, resource="workforce.crew", action="read", company_id=company_id
    )
    return [
        CrewResponse.model_validate(crew, from_attributes=True)
        for crew in workforce_service.list_crews(db, company_id=company_id)
    ]


@router.get("/crews/{crew_id}", response_model=CrewWithMembersResponse)
def get_crew(
    crew_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.crew", "read")),
) -> CrewWithMembersResponse:
    crew = _resolve_crew(db, crew_id)
    assert_company_access(
        db, user_id=user.id, resource="workforce.crew", action="read", company_id=crew.company_id
    )
    members = workforce_service.list_crew_members(db, crew_id=crew_id)
    return CrewWithMembersResponse(
        id=crew.id,
        company_id=crew.company_id,
        project_id=crew.project_id,
        name=crew.name,
        status=crew.status,
        members=[WorkerResponse.model_validate(w, from_attributes=True) for w in members],
    )


@router.post("/crews/{crew_id}/members", response_model=CrewMemberResponse, status_code=201)
def add_crew_member(
    crew_id: uuid.UUID,
    payload: CrewMemberAddRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.crew", "manage_members")),
) -> CrewMemberResponse:
    crew = _resolve_crew(db, crew_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="workforce.crew",
        action="manage_members",
        company_id=crew.company_id,
    )
    member = workforce_service.add_crew_member(db, crew_id=crew_id, worker_id=payload.worker_id)
    return CrewMemberResponse.model_validate(member, from_attributes=True)


@router.delete("/crews/{crew_id}/members/{worker_id}", status_code=204)
def remove_crew_member(
    crew_id: uuid.UUID,
    worker_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("workforce.crew", "manage_members")),
) -> None:
    crew = _resolve_crew(db, crew_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="workforce.crew",
        action="manage_members",
        company_id=crew.company_id,
    )
    workforce_service.remove_crew_member(db, crew_id=crew_id, worker_id=worker_id)
