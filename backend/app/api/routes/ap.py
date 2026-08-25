import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.schemas.ap import (
    SupplierInvoiceCreateRequest,
    SupplierInvoiceResponse,
    SupplierPaymentCreateRequest,
    SupplierPaymentResponse,
)
from app.services import ap_service, audit_service, idempotency_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/ap", tags=["accounts-payable"])


def _resolve_invoice(db: Session, invoice_id: uuid.UUID):
    invoice = ap_service.get_supplier_invoice(db, invoice_id=invoice_id)
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    return invoice


@router.post("/supplier-invoices", response_model=SupplierInvoiceResponse, status_code=201)
def create_supplier_invoice(
    payload: SupplierInvoiceCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "create")),
) -> SupplierInvoiceResponse:
    assert_company_access(
        db, user_id=user.id, resource="ap.supplier_invoice", action="create", company_id=payload.company_id
    )
    invoice = ap_service.create_supplier_invoice(
        db,
        company_id=payload.company_id,
        supplier_id=payload.supplier_id,
        invoice_number=payload.invoice_number,
        scope=payload.scope,
        project_id=payload.project_id,
        cost_center_id=payload.cost_center_id,
        expense_account_id=payload.expense_account_id,
        payable_account_id=payload.payable_account_id,
        currency_code=payload.currency_code,
        amount=payload.amount,
        tax_amount=payload.tax_amount,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        description=payload.description,
    )
    return SupplierInvoiceResponse.model_validate(invoice, from_attributes=True)


@router.get("/supplier-invoices/{invoice_id}", response_model=SupplierInvoiceResponse)
def get_supplier_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "read")),
) -> SupplierInvoiceResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ap.supplier_invoice",
        action="read",
        company_id=invoice.company_id,
    )
    return SupplierInvoiceResponse.model_validate(invoice, from_attributes=True)


@router.get("/supplier-invoices", response_model=list[SupplierInvoiceResponse])
def list_supplier_invoices(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "read")),
) -> list[SupplierInvoiceResponse]:
    assert_company_access(
        db,
        user_id=user.id,
        resource="ap.supplier_invoice",
        action="read",
        company_id=company_id,
    )
    return [
        SupplierInvoiceResponse.model_validate(invoice, from_attributes=True)
        for invoice in ap_service.list_supplier_invoices(db, company_id=company_id)
    ]


@router.post("/supplier-invoices/{invoice_id}/approve", response_model=SupplierInvoiceResponse)
def approve_supplier_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_invoice", "approve")),
    correlation_id: str = Depends(get_correlation_id),
) -> SupplierInvoiceResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ap.supplier_invoice",
        action="approve",
        company_id=invoice.company_id,
    )
    before_status = invoice.status
    invoice = ap_service.approve_supplier_invoice(db, invoice_id=invoice_id)
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="ap.supplier_invoice.approve",
        entity_type="ap.supplier_invoice",
        entity_id=invoice.id,
        company_id=invoice.company_id,
        project_id=invoice.project_id,
        before={"status": before_status},
        after={"status": invoice.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return SupplierInvoiceResponse.model_validate(invoice, from_attributes=True)


@router.post(
    "/supplier-invoices/{invoice_id}/payments", response_model=SupplierPaymentResponse, status_code=201
)
def pay_supplier_invoice(
    invoice_id: uuid.UUID,
    payload: SupplierPaymentCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_payment", "create")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str = Depends(get_correlation_id),
) -> SupplierPaymentResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ap.supplier_payment",
        action="create",
        company_id=invoice.company_id,
    )
    outcome = None
    request_payload = {"invoiceId": str(invoice_id), **payload.model_dump(mode="json")}
    try:
        if idempotency_key:
            outcome = idempotency_service.begin(
                db,
                key=idempotency_key,
                command="ap.supplier_payment.create",
                payload=request_payload,
            )
            if outcome.is_replay:
                return SupplierPaymentResponse.model_validate(outcome.record.result)
        payment = ap_service.pay_supplier_invoice(
            db,
            invoice_id=invoice_id,
            treasury_account_id=payload.treasury_account_id,
            amount=payload.amount,
            payment_date=payload.payment_date,
            commit=outcome is None,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="ap.supplier_payment.create",
            entity_type="ap.supplier_payment",
            entity_id=payment.id,
            company_id=invoice.company_id,
            project_id=invoice.project_id,
            before=None,
            after={"amount": str(payment.amount), "invoiceId": str(invoice.id)},
            correlation_id=correlation_id,
        )
        response = SupplierPaymentResponse.model_validate(payment, from_attributes=True)
        if outcome is not None:
            idempotency_service.complete(
                db,
                outcome.record,
                result=response.model_dump(mode="json"),
                entity_type="SupplierPayment",
                entity_id=payment.id,
            )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise
