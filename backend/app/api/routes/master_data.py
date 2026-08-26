import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.domain.errors import InvalidCashFlowActivityError, NotFoundError
from app.models.chart_of_accounts import CASH_FLOW_ACTIVITIES, ChartOfAccount
from app.repositories import account_repository, company_repository, role_repository
from app.schemas.master_data import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
    UserCreateRequest,
    UserResponse,
)
from app.schemas.tax import TaxCodeCreateRequest, TaxCodeResponse
from app.services import audit_service, tax_service, user_service
from app.services.permission_service import (
    assert_company_access,
    list_user_company_ids,
    require_permission,
    user_has_any_company_scope,
)

router = APIRouter(prefix="/master-data", tags=["master-data"])


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "read")),
) -> list[CompanyResponse]:
    company_ids = None
    if not user_has_any_company_scope(db, user_id=user.id, resource="core.company", action="read"):
        company_ids = list_user_company_ids(db, user_id=user.id)
    companies = company_repository.list_companies(db, company_ids=company_ids)
    return [CompanyResponse.model_validate(company, from_attributes=True) for company in companies]


@router.post("/companies", response_model=CompanyResponse, status_code=201)
def create_company(
    payload: CompanyCreateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("core.company", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> CompanyResponse:
    try:
        company = company_repository.create_company(
            db,
            name=payload.name,
            code=payload.code,
            legal_name=payload.legal_name,
            functional_currency_code=payload.functional_currency_code,
            country=payload.country,
            fiscal_id=payload.fiscal_id,
        )
        db.flush()
        audit_service.record(
            db,
            actor_user_id=_user.id,
            action="core.company.create",
            entity_type="core.company",
            entity_id=company.id,
            company_id=company.id,
            project_id=None,
            before=None,
            after={"name": company.name, "code": company.code},
            correlation_id=correlation_id,
        )
        db.commit()
        return CompanyResponse.model_validate(company, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.company", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> CompanyResponse:
    try:
        existing = company_repository.get_by_id(db, company_id)
        if existing is None:
            raise NotFoundError(f"Company {company_id} no existe")
        assert_company_access(
            db, user_id=user.id, resource="core.company", action="update", company_id=company_id
        )
        before_legal_name = existing.legal_name
        before_fiscal_id = existing.fiscal_id
        company = company_repository.update_company(
            db,
            company=existing,
            legal_name=payload.legal_name,
            fiscal_id=payload.fiscal_id,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="core.company.update",
            entity_type="core.company",
            entity_id=company_id,
            company_id=company_id,
            project_id=None,
            before={"legalName": before_legal_name, "fiscalId": before_fiscal_id},
            after={"legalName": company.legal_name, "fiscalId": company.fiscal_id},
            correlation_id=correlation_id,
        )
        db.commit()
        return CompanyResponse.model_validate(company, from_attributes=True)
    except Exception:
        db.rollback()
        raise


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
    correlation_id: str = Depends(get_correlation_id),
) -> AccountResponse:
    try:
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
        db.flush()
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="accounting.account.create",
            entity_type="accounting.account",
            entity_id=account.id,
            company_id=payload.company_id,
            project_id=None,
            before=None,
            after={"code": account.code, "name": account.name, "type": account.account_type},
            correlation_id=correlation_id,
        )
        db.commit()
        return AccountResponse.model_validate(account, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.account", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> AccountResponse:
    """NXR-REQ-0016/0093, Cash Flow: única forma real de clasificar una
    cuenta hoy (no hay pantalla dedicada de catálogo contable todavía --
    mismo criterio que Tax Codes antes de tener consumidor de UI)."""
    try:
        account = account_repository.get_by_id(db, account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} no existe")
        chart = db.get(ChartOfAccount, account.chart_of_account_id)
        assert_company_access(
            db, user_id=user.id, resource="accounting.account", action="update", company_id=chart.company_id
        )
        if payload.cash_flow_activity is not None and payload.cash_flow_activity not in CASH_FLOW_ACTIVITIES:
            raise InvalidCashFlowActivityError(
                f"cash_flow_activity inválido: {payload.cash_flow_activity!r} (debe ser uno de {CASH_FLOW_ACTIVITIES} o null)"
            )
        before_cfa = account.cash_flow_activity
        account = account_repository.update_cash_flow_activity(
            db, account=account, cash_flow_activity=payload.cash_flow_activity
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="accounting.account.update",
            entity_type="accounting.account",
            entity_id=account_id,
            company_id=chart.company_id,
            project_id=None,
            before={"cashFlowActivity": before_cfa},
            after={"cashFlowActivity": account.cash_flow_activity},
            correlation_id=correlation_id,
        )
        db.commit()
        return AccountResponse.model_validate(account, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.get("/tax-codes", response_model=list[TaxCodeResponse])
def list_tax_codes(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("tax.tax_code", "read")),
) -> list[TaxCodeResponse]:
    assert_company_access(
        db, user_id=user.id, resource="tax.tax_code", action="read", company_id=company_id
    )
    tax_codes = tax_service.list_tax_codes(db, company_id=company_id)
    return [TaxCodeResponse.model_validate(tc, from_attributes=True) for tc in tax_codes]


@router.post("/tax-codes", response_model=TaxCodeResponse, status_code=201)
def create_tax_code(
    payload: TaxCodeCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tax.tax_code", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> TaxCodeResponse:
    assert_company_access(
        db, user_id=user.id, resource="tax.tax_code", action="create", company_id=payload.company_id
    )
    tax_code = tax_service.create_tax_code(
        db,
        company_id=payload.company_id,
        code=payload.code,
        name=payload.name,
        rate_percent=payload.rate_percent,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="tax.tax_code.create",
        entity_type="tax.tax_code",
        entity_id=tax_code.id,
        company_id=payload.company_id,
        project_id=None,
        before=None,
        after={"code": tax_code.code, "name": tax_code.name, "ratePercent": str(tax_code.rate_percent)},
        correlation_id=correlation_id,
    )
    db.commit()
    return TaxCodeResponse.model_validate(tax_code, from_attributes=True)


def _user_response(db: Session, user) -> UserResponse:
    roles = role_repository.get_role_names_for_user(db, user.id)
    return UserResponse(id=user.id, email=user.email, full_name=user.full_name, roles=roles)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("core.user", "read")),
) -> list[UserResponse]:
    assert_company_access(
        db, user_id=user.id, resource="core.user", action="read", company_id=company_id
    )
    users = user_service.list_company_users(db, company_id=company_id)
    return [_user_response(db, u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    requesting_user=Depends(require_permission("core.user", "create")),
    correlation_id: str = Depends(get_correlation_id),
) -> UserResponse:
    assert_company_access(
        db,
        user_id=requesting_user.id,
        resource="core.user",
        action="create",
        company_id=payload.company_id,
    )
    created = user_service.create_user_with_role(
        db,
        company_id=payload.company_id,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        role_name=payload.role_name,
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=requesting_user.id,
        action="core.user.create",
        entity_type="core.user",
        entity_id=created.id,
        company_id=payload.company_id,
        project_id=None,
        before=None,
        after={"email": created.email, "fullName": created.full_name},
        correlation_id=correlation_id,
    )
    db.commit()
    return _user_response(db, created)
