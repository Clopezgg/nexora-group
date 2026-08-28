import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.repositories import supplier_repository
from app.schemas.supplier import (
    SupplierContractCreateRequest,
    SupplierContractResponse,
    SupplierCreateRequest,
    SupplierResponse,
)
from app.services.financial_validation_service import (
    assert_project_belongs_to_company,
    assert_supplier_belongs_to_company,
)
from app.services import audit_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/procurement/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.supplier", "read")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.supplier", action="read", company_id=company_id
    )
    suppliers = supplier_repository.list_suppliers(db, company_id=company_id)
    return [SupplierResponse.model_validate(supplier, from_attributes=True) for supplier in suppliers]


@router.post("", response_model=SupplierResponse, status_code=201)
def create_supplier(
    payload: SupplierCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.supplier", "create")),
    correlation_id: str = Depends(get_correlation_id),
):
    try:
        assert_company_access(
            db,
            user_id=user.id,
            resource="procurement.supplier",
            action="create",
            company_id=payload.company_id,
        )
        supplier = supplier_repository.create_supplier(
            db,
            company_id=payload.company_id,
            legal_name=payload.legal_name,
            trade_name=payload.trade_name,
            tax_id=payload.tax_id,
            contact_name=payload.contact_name,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            classification=payload.classification,
            payment_terms=payload.payment_terms,
            banking_details=payload.banking_details,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="procurement.supplier.create",
            entity_type="procurement.supplier",
            entity_id=supplier.id,
            company_id=supplier.company_id,
            project_id=None,
            before=None,
            after={
                "classification": supplier.classification,
                "legalName": supplier.legal_name,
                "status": supplier.status,
                "tradeName": supplier.trade_name,
            },
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(supplier)
        return SupplierResponse.model_validate(supplier, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.get("/contracts", response_model=list[SupplierContractResponse])
def list_contracts(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.contract", "read")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.contract", action="read", company_id=company_id
    )
    contracts = supplier_repository.list_contracts(db, company_id=company_id)
    return [SupplierContractResponse.model_validate(c, from_attributes=True) for c in contracts]


@router.post("/contracts", response_model=SupplierContractResponse, status_code=201)
def create_contract(
    payload: SupplierContractCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.contract", "create")),
    correlation_id: str = Depends(get_correlation_id),
):
    try:
        assert_company_access(
            db,
            user_id=user.id,
            resource="procurement.contract",
            action="create",
            company_id=payload.company_id,
        )
        assert_supplier_belongs_to_company(
            db, supplier_id=payload.supplier_id, company_id=payload.company_id
        )
        assert_project_belongs_to_company(
            db, project_id=payload.project_id, company_id=payload.company_id
        )
        contract = supplier_repository.create_contract(
            db,
            company_id=payload.company_id,
            supplier_id=payload.supplier_id,
            project_id=payload.project_id,
            contract_number=payload.contract_number,
            scope_description=payload.scope_description,
            value=payload.value,
            currency_code=payload.currency_code,
            start_date=payload.start_date,
            end_date=payload.end_date,
            advance_percentage=payload.advance_percentage,
            retention_percentage=payload.retention_percentage,
            payment_terms=payload.payment_terms,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="procurement.contract.create",
            entity_type="procurement.contract",
            entity_id=contract.id,
            company_id=contract.company_id,
            project_id=contract.project_id,
            before=None,
            after={
                "contractNumber": contract.contract_number,
                "currencyCode": contract.currency_code,
                "status": contract.status,
                "supplierId": str(contract.supplier_id),
                "value": str(contract.value),
            },
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(contract)
        return SupplierContractResponse.model_validate(contract, from_attributes=True)
    except Exception:
        db.rollback()
        raise
