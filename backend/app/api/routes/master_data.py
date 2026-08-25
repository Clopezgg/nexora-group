import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import account_repository, company_repository
from app.schemas.master_data import (
    AccountCreateRequest,
    AccountResponse,
    CompanyCreateRequest,
    CompanyResponse,
)
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/master-data", tags=["master-data"])


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("core.company", "read")),
) -> list[CompanyResponse]:
    companies = company_repository.list_companies(db)
    return [CompanyResponse.model_validate(company, from_attributes=True) for company in companies]


@router.post("/companies", response_model=CompanyResponse, status_code=201)
def create_company(
    payload: CompanyCreateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("core.company", "create")),
) -> CompanyResponse:
    company = company_repository.create_company(
        db,
        name=payload.name,
        code=payload.code,
        legal_name=payload.legal_name,
        functional_currency_code=payload.functional_currency_code,
        country=payload.country,
        fiscal_id=payload.fiscal_id,
    )
    db.commit()
    db.refresh(company)
    return CompanyResponse.model_validate(company, from_attributes=True)


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.account", "read")),
) -> list[AccountResponse]:
    assert_company_access(
        db, user_id=user.id, resource="accounting.account", action="read", company_id=company_id
    )
    accounts = account_repository.list_accounts_for_company(db, company_id)
    return [AccountResponse.model_validate(account, from_attributes=True) for account in accounts]


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(
    payload: AccountCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.account", "create")),
) -> AccountResponse:
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.account",
        action="create",
        company_id=payload.company_id,
    )
    account = account_repository.create_account(
        db,
        company_id=payload.company_id,
        code=payload.code,
        name=payload.name,
        account_type=payload.account_type,
        parent_id=payload.parent_id,
    )
    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account, from_attributes=True)
