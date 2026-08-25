import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError, InvalidOperationScopeError
from app.models.accounting import OPERATION_SCOPES
from app.models.chart_of_accounts import Account, ChartOfAccount
from app.models.cost_center import CostCenter
from app.models.project import Project
from app.models.supplier import Supplier


def assert_operation_scope(scope: str, project_id: uuid.UUID | None) -> None:
    if scope not in OPERATION_SCOPES:
        raise InvalidOperationScopeError(f"scope inválido: {scope!r}")
    if scope in ("CENTRAL", "GENERAL") and project_id is not None:
        raise InvalidOperationScopeError(f"scope={scope} requiere project_id=None")
    if scope == "PROJECT" and project_id is None:
        raise InvalidOperationScopeError("scope=PROJECT requiere project_id")


def assert_account_belongs_to_company(
    db: Session, *, account_id: uuid.UUID, company_id: uuid.UUID, field_name: str
) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise InvalidFinancialReferenceError(f"{field_name} no existe")
    account_company_id = db.execute(
        select(ChartOfAccount.company_id).where(
            ChartOfAccount.id == account.chart_of_account_id
        )
    ).scalar_one()
    if account_company_id != company_id:
        raise InvalidFinancialReferenceError(
            f"{field_name} debe pertenecer a la compañía propietaria"
        )
    return account


def assert_project_belongs_to_company(
    db: Session, *, project_id: uuid.UUID | None, company_id: uuid.UUID
) -> Project | None:
    if project_id is None:
        return None
    project = db.get(Project, project_id)
    if project is None or project.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "project_id debe pertenecer a la compañía propietaria"
        )
    return project


def assert_cost_center_belongs_to_company(
    db: Session, *, cost_center_id: uuid.UUID | None, company_id: uuid.UUID
) -> CostCenter | None:
    if cost_center_id is None:
        return None
    cost_center = db.get(CostCenter, cost_center_id)
    if cost_center is None or cost_center.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "cost_center_id debe pertenecer a la compañía propietaria"
        )
    return cost_center


def assert_supplier_belongs_to_company(
    db: Session, *, supplier_id: uuid.UUID, company_id: uuid.UUID
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "supplier_id debe pertenecer a la compañía propietaria"
        )
    return supplier
