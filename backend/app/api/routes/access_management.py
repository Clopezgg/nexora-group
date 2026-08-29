import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.company import Company
from app.models.permission import UserCompanyAccess, UserProjectAccess
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.access_management import (
    CompanyAccessResponse,
    ProjectAccessResponse,
    RoleAccessResponse,
    UserAccessSummaryResponse,
)
from app.services import audit_service
from app.services.permission_service import (
    assert_company_access,
    grant_project_access,
    require_permission,
    revoke_project_access,
    user_has_company_access,
)

router = APIRouter(prefix="/access-management", tags=["access-management"])


def _user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def _company_or_404(db: Session, company_id: uuid.UUID) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")
    return company


def _project_or_404(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


def _is_administrator(db: Session, user_id: uuid.UUID) -> bool:
    stmt = (
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.name == "Administrator")
    )
    return db.execute(stmt).first() is not None


def _summary(db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID | None) -> UserAccessSummaryResponse:
    _user_or_404(db, user_id)
    assigned_role_ids = set(
        db.execute(select(UserRole.role_id).where(UserRole.user_id == user_id)).scalars()
    )
    roles = list(db.execute(select(Role).order_by(Role.name)).scalars())
    assigned_company_ids = set(
        db.execute(
            select(UserCompanyAccess.company_id).where(UserCompanyAccess.user_id == user_id)
        ).scalars()
    )
    companies = list(db.execute(select(Company).order_by(Company.name)).scalars())
    assigned_project_ids = set(
        db.execute(
            select(UserProjectAccess.project_id).where(UserProjectAccess.user_id == user_id)
        ).scalars()
    )
    project_stmt = select(Project).order_by(Project.name)
    if company_id is not None:
        project_stmt = project_stmt.where(Project.company_id == company_id)
    projects = list(db.execute(project_stmt).scalars())
    return UserAccessSummaryResponse(
        user_id=user_id,
        roles=[
            RoleAccessResponse(id=role.id, name=role.name, assigned=role.id in assigned_role_ids)
            for role in roles
        ],
        companies=[
            CompanyAccessResponse(
                id=company.id,
                name=company.name,
                assigned=company.id in assigned_company_ids,
            )
            for company in companies
        ],
        projects=[
            ProjectAccessResponse(
                id=project.id,
                company_id=project.company_id,
                code=project.code,
                name=project.name,
                assigned=project.id in assigned_project_ids,
            )
            for project in projects
        ],
    )


@router.get("/users/{user_id}", response_model=UserAccessSummaryResponse)
def get_user_access(
    user_id: uuid.UUID,
    company_id: uuid.UUID | None = Query(default=None, alias="companyId"),
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
) -> UserAccessSummaryResponse:
    if company_id is not None:
        assert_company_access(
            db,
            user_id=requesting_user.id,
            resource="core.user",
            action="create",
            company_id=company_id,
        )
    return _summary(db, user_id=user_id, company_id=company_id)


@router.put("/users/{user_id}/roles/{role_id}", response_model=UserAccessSummaryResponse)
def grant_user_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserAccessSummaryResponse:
    target = _user_or_404(db, user_id)
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(UserRole(user_id=user_id, role_id=role_id))
        db.flush()
        audit_service.record(
            db,
            actor_user_id=requesting_user.id,
            action="core.user.role.grant",
            entity_type="core.user",
            entity_id=target.id,
            company_id=None,
            project_id=None,
            before=None,
            after={"roleId": str(role.id), "roleName": role.name},
            correlation_id=correlation_id,
        )
        db.commit()
    return _summary(db, user_id=user_id, company_id=None)


@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserAccessSummaryResponse)
def revoke_user_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserAccessSummaryResponse:
    target = _user_or_404(db, user_id)
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if user_id == requesting_user.id and role.name == "Administrator":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No puedes retirar tu propio rol Administrator desde esta sesión",
        )
    assignments = list(
        db.execute(select(UserRole).where(UserRole.user_id == user_id)).scalars()
    )
    match = next((row for row in assignments if row.role_id == role_id), None)
    if match is not None:
        if len(assignments) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El usuario debe conservar al menos un rol",
            )
        db.delete(match)
        audit_service.record(
            db,
            actor_user_id=requesting_user.id,
            action="core.user.role.revoke",
            entity_type="core.user",
            entity_id=target.id,
            company_id=None,
            project_id=None,
            before={"roleId": str(role.id), "roleName": role.name},
            after=None,
            correlation_id=correlation_id,
        )
        db.commit()
    return _summary(db, user_id=user_id, company_id=None)


@router.put("/users/{user_id}/companies/{company_id}", response_model=UserAccessSummaryResponse)
def grant_user_company(
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserAccessSummaryResponse:
    target = _user_or_404(db, user_id)
    company = _company_or_404(db, company_id)
    assert_company_access(
        db,
        user_id=requesting_user.id,
        resource="core.user",
        action="create",
        company_id=company_id,
    )
    existing = db.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.user_id == user_id,
            UserCompanyAccess.company_id == company_id,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(UserCompanyAccess(user_id=user_id, company_id=company_id))
        db.flush()
        audit_service.record(
            db,
            actor_user_id=requesting_user.id,
            action="core.user.company_access.grant",
            entity_type="core.user",
            entity_id=target.id,
            company_id=company_id,
            project_id=None,
            before=None,
            after={"companyId": str(company.id), "companyName": company.name},
            correlation_id=correlation_id,
        )
        db.commit()
    return _summary(db, user_id=user_id, company_id=company_id)


@router.delete("/users/{user_id}/companies/{company_id}", response_model=UserAccessSummaryResponse)
def revoke_user_company(
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserAccessSummaryResponse:
    target = _user_or_404(db, user_id)
    company = _company_or_404(db, company_id)
    assert_company_access(
        db,
        user_id=requesting_user.id,
        resource="core.user",
        action="create",
        company_id=company_id,
    )
    grant = db.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.user_id == user_id,
            UserCompanyAccess.company_id == company_id,
        )
    ).scalar_one_or_none()
    if grant is not None:
        project_ids = select(Project.id).where(Project.company_id == company_id)
        db.execute(
            delete(UserProjectAccess).where(
                UserProjectAccess.user_id == user_id,
                UserProjectAccess.project_id.in_(project_ids),
            )
        )
        db.delete(grant)
        audit_service.record(
            db,
            actor_user_id=requesting_user.id,
            action="core.user.company_access.revoke",
            entity_type="core.user",
            entity_id=target.id,
            company_id=company_id,
            project_id=None,
            before={"companyId": str(company.id), "companyName": company.name},
            after=None,
            correlation_id=correlation_id,
        )
        db.commit()
    return _summary(db, user_id=user_id, company_id=company_id)


@router.put("/users/{user_id}/projects/{project_id}", response_model=UserAccessSummaryResponse)
def grant_user_project(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserAccessSummaryResponse:
    target = _user_or_404(db, user_id)
    project = _project_or_404(db, project_id)
    assert_company_access(
        db,
        user_id=requesting_user.id,
        resource="core.user",
        action="create",
        company_id=project.company_id,
    )
    target_has_company = user_has_company_access(
        db, user_id=user_id, company_id=project.company_id
    ) or _is_administrator(db, user_id)
    if not target_has_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asigna primero la compañía al usuario antes de asignar uno de sus proyectos",
        )
    before_assigned = db.execute(
        select(UserProjectAccess.id).where(
            UserProjectAccess.user_id == user_id,
            UserProjectAccess.project_id == project_id,
        )
    ).first() is not None
    grant_project_access(db, user_id=user_id, project_id=project_id)
    if not before_assigned:
        audit_service.record(
            db,
            actor_user_id=requesting_user.id,
            action="core.user.project_access.grant",
            entity_type="core.user",
            entity_id=target.id,
            company_id=project.company_id,
            project_id=project.id,
            before=None,
            after={"projectId": str(project.id), "projectName": project.name},
            correlation_id=correlation_id,
        )
        db.commit()
    return _summary(db, user_id=user_id, company_id=project.company_id)


@router.delete("/users/{user_id}/projects/{project_id}", response_model=UserAccessSummaryResponse)
def revoke_user_project(
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserAccessSummaryResponse:
    target = _user_or_404(db, user_id)
    project = _project_or_404(db, project_id)
    assert_company_access(
        db,
        user_id=requesting_user.id,
        resource="core.user",
        action="create",
        company_id=project.company_id,
    )
    removed = revoke_project_access(db, user_id=user_id, project_id=project_id)
    if removed:
        audit_service.record(
            db,
            actor_user_id=requesting_user.id,
            action="core.user.project_access.revoke",
            entity_type="core.user",
            entity_id=target.id,
            company_id=project.company_id,
            project_id=project.id,
            before={"projectId": str(project.id), "projectName": project.name},
            after=None,
            correlation_id=correlation_id,
        )
        db.commit()
    return _summary(db, user_id=user_id, company_id=project.company_id)
