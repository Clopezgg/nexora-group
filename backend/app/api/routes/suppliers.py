import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.models.supplier import SUPPLIER_STATUSES_BLOCKING_NEW
from app.repositories import supplier_repository
from app.schemas.supplier import (
    SupplierContractCreateRequest,
    SupplierContractResponse,
    SupplierCreateRequest,
    SupplierResponse,
    SupplierStatusChangeRequest,
    SupplierUpdateRequest,
)
from app.services.financial_validation_service import (
    assert_project_belongs_to_company,
    assert_supplier_belongs_to_company,
)
from app.services import audit_service
from app.services.permission_service import (
    accessible_project_ids,
    assert_company_access,
    require_permission,
)

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
            address_line_1=payload.address_line_1,
            address_line_2=payload.address_line_2,
            city=payload.city,
            state_department=payload.state_department,
            country=payload.country,
            party_role=payload.party_role,
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


_SUPPLIER_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "ACTIVE": {"INACTIVE", "BLOCKED", "ARCHIVED"},
    "INACTIVE": {"ACTIVE", "BLOCKED", "ARCHIVED"},
    "BLOCKED": {"ACTIVE", "INACTIVE", "ARCHIVED"},
    "ARCHIVED": {"ACTIVE"},
}
_SUPPLIER_SENSITIVE_TARGETS = {"BLOCKED", "ARCHIVED"}


def _supplier_snapshot(s) -> dict:
    return {
        "legalName": s.legal_name,
        "tradeName": s.trade_name,
        "taxId": s.tax_id,
        "contactName": s.contact_name,
        "email": s.email,
        "phone": s.phone,
        "partyRole": s.party_role,
        "status": s.status,
        "paymentTerms": s.payment_terms,
    }


@router.patch("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.supplier", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> SupplierResponse:
    supplier = supplier_repository.get_supplier(db, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor / contratista no encontrado")
    assert_company_access(
        db, user_id=user.id, resource="procurement.supplier", action="update",
        company_id=supplier.company_id,
    )
    try:
        before = _supplier_snapshot(supplier)
        supplier_repository.update_supplier(
            db, supplier=supplier, values=payload.model_dump(exclude_unset=True)
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="procurement.supplier.update",
            entity_type="procurement.supplier",
            entity_id=supplier.id,
            company_id=supplier.company_id,
            project_id=None,
            before=before,
            after=_supplier_snapshot(supplier),
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(supplier)
        return SupplierResponse.model_validate(supplier, from_attributes=True)
    except Exception:
        db.rollback()
        raise


@router.post("/{supplier_id}/status", response_model=SupplierResponse)
def change_supplier_status(
    supplier_id: uuid.UUID,
    payload: SupplierStatusChangeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.supplier", "update")),
    correlation_id: str = Depends(get_correlation_id),
) -> SupplierResponse:
    supplier = supplier_repository.get_supplier(db, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor / contratista no encontrado")
    assert_company_access(
        db, user_id=user.id, resource="procurement.supplier", action="update",
        company_id=supplier.company_id,
    )
    target = payload.status
    if target == supplier.status:
        return SupplierResponse.model_validate(supplier, from_attributes=True)
    if target not in _SUPPLIER_STATUS_TRANSITIONS.get(supplier.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"El tercero está en «{supplier.status}» y no puede pasar a «{target}».",
        )
    if target in _SUPPLIER_SENSITIVE_TARGETS or supplier.status == "ARCHIVED":
        if len((payload.reason or "").strip()) < 10:
            raise HTTPException(
                status_code=422,
                detail="Bloquear, archivar o restaurar un tercero requiere un motivo de al menos 10 caracteres.",
            )
    try:
        before = supplier.status
        supplier_repository.set_supplier_status(db, supplier=supplier, status=target)
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="procurement.supplier.status",
            entity_type="procurement.supplier",
            entity_id=supplier.id,
            company_id=supplier.company_id,
            project_id=None,
            before={"status": before},
            after={"status": target, "reason": payload.reason},
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
    category: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.contract", "read")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.contract", action="read", company_id=company_id
    )
    contracts = supplier_repository.list_contracts(
        db, company_id=company_id, category=category
    )
    allowed = accessible_project_ids(
        db, user_id=user.id, resource="procurement.contract", action="read"
    )
    if allowed is not None:
        allowed_set = set(allowed)
        contracts = [
            row for row in contracts
            if row.project_id is None or row.project_id in allowed_set
        ]
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
        supplier = supplier_repository.get_supplier(db, payload.supplier_id)
        if supplier is not None and supplier.status in SUPPLIER_STATUSES_BLOCKING_NEW:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Este proveedor / contratista está "
                    f"{'bloqueado' if supplier.status == 'BLOCKED' else 'archivado'} "
                    "y no admite nuevos contratos."
                ),
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
            contract_category=payload.contract_category,
            scope_description=payload.scope_description,
            value=payload.value,
            currency_code=payload.currency_code,
            start_date=payload.start_date,
            end_date=payload.end_date,
            advance_percentage=payload.advance_percentage,
            advance_amount=payload.advance_amount,
            advance_due_date=payload.advance_due_date,
            retention_percentage=payload.retention_percentage,
            payment_terms=payload.payment_terms,
            payment_terms_type=payload.payment_terms_type,
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
                "contractCategory": contract.contract_category,
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
