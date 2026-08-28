import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.repositories import company_repository
from app.schemas.master_data import CompanyResponse, CompanyUpdateRequest
from app.services import audit_service
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
