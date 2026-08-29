import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.repositories import company_repository
from app.schemas.master_data import (
    CompanyResponse,
    CompanyUpdateRequest,
    ResourcePostingConfigRequest,
    ResourcePostingConfigResponse,
)
from app.services import audit_service, resource_posting_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/master-data", tags=["master-data"])


@router.patch("/companies/{company_id}/profile", response_model=CompanyResponse)
def update_company_profile(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> CompanyResponse:
    company = company_repository.get_by_id(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="update", company_id=company_id
    )
    before = {
        "name": company.name,
        "code": company.code,
        "legalName": company.legal_name,
        "functionalCurrencyCode": company.functional_currency_code,
        "country": company.country,
        "fiscalId": company.fiscal_id,
    }
    values = payload.model_dump(exclude_unset=True)
    try:
        company_repository.update_company(db, company=company, **values)
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="core.company.profile.update",
            entity_type="core.company",
            entity_id=company.id,
            company_id=company.id,
            project_id=None,
            before=before,
            after={
                "name": company.name,
                "code": company.code,
                "legalName": company.legal_name,
                "functionalCurrencyCode": company.functional_currency_code,
                "country": company.country,
                "fiscalId": company.fiscal_id,
            },
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(company)
        return CompanyResponse.model_validate(company, from_attributes=True)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/companies/{company_id}/resource-posting-configs",
    response_model=list[ResourcePostingConfigResponse],
)
def list_resource_posting_configs(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> list[ResourcePostingConfigResponse]:
    if company_repository.get_by_id(db, company_id) is None:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="read", company_id=company_id
    )
    return [
        ResourcePostingConfigResponse.model_validate(row, from_attributes=True)
        for row in resource_posting_service.list_configs(db, company_id=company_id)
    ]


@router.put(
    "/companies/{company_id}/resource-posting-configs/{source_type}",
    response_model=ResourcePostingConfigResponse,
)
def upsert_resource_posting_config(
    company_id: uuid.UUID,
    source_type: str,
    payload: ResourcePostingConfigRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> ResourcePostingConfigResponse:
    if company_repository.get_by_id(db, company_id) is None:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")
    assert_company_access(
        db, user_id=user.id, resource="core.company", action="update", company_id=company_id
    )
    normalized_source = source_type.upper()
    if payload.source_type != normalized_source:
        raise HTTPException(
            status_code=422,
            detail="sourceType del payload debe coincidir con el origen de la URL",
        )

    existing = next(
        (
            row
            for row in resource_posting_service.list_configs(db, company_id=company_id)
            if row.source_type == normalized_source
        ),
        None,
    )
    before = None
    if existing is not None:
        before = {
            "sourceType": existing.source_type,
            "expenseAccountId": str(existing.expense_account_id),
            "offsetAccountId": str(existing.offset_account_id),
            "active": existing.active,
        }

    try:
        row = resource_posting_service.upsert_config(
            db,
            company_id=company_id,
            source_type=normalized_source,
            expense_account_id=payload.expense_account_id,
            offset_account_id=payload.offset_account_id,
            active=payload.active,
            commit=False,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="accounting.resource_posting_config.upsert",
            entity_type="accounting.resource_posting_config",
            entity_id=row.id,
            company_id=company_id,
            project_id=None,
            before=before,
            after={
                "sourceType": row.source_type,
                "expenseAccountId": str(row.expense_account_id),
                "offsetAccountId": str(row.offset_account_id),
                "active": row.active,
            },
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(row)
        return ResourcePostingConfigResponse.model_validate(row, from_attributes=True)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
