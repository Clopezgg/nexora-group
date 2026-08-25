import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.ar import (
    CustomerInvoiceCreateRequest,
    CustomerInvoiceResponse,
    CustomerReceiptCreateRequest,
    CustomerReceiptResponse,
)
from app.services import ar_service, idempotency_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/ar", tags=["accounts-receivable"])


def _resolve_invoice(db: Session, invoice_id: uuid.UUID):
    invoice = ar_service.get_customer_invoice(db, invoice_id=invoice_id)
    if invoice is None:
        raise ValueError(f"CustomerInvoice {invoice_id} no existe")
    return invoice


@router.post("/customer-invoices", response_model=CustomerInvoiceResponse, status_code=201)
def create_customer_invoice(
    payload: CustomerInvoiceCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ar.customer_invoice", "create")),
) -> CustomerInvoiceResponse:
    assert_company_access(
        db, user_id=user.id, resource="ar.customer_invoice", action="create", company_id=payload.company_id
    )
    invoice = ar_service.create_customer_invoice(
        db,
        company_id=payload.company_id,
        customer_name=payload.customer_name,
        invoice_number=payload.invoice_number,
        scope=payload.scope,
        project_id=payload.project_id,
        revenue_account_id=payload.revenue_account_id,
        receivable_account_id=payload.receivable_account_id,
        currency_code=payload.currency_code,
        amount=payload.amount,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        description=payload.description,
    )
    return CustomerInvoiceResponse.model_validate(invoice, from_attributes=True)


@router.get("/customer-invoices/{invoice_id}", response_model=CustomerInvoiceResponse)
def get_customer_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ar.customer_invoice", "read")),
) -> CustomerInvoiceResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ar.customer_invoice",
        action="read",
        company_id=invoice.company_id,
    )
    return CustomerInvoiceResponse.model_validate(invoice, from_attributes=True)


@router.get("/customer-invoices", response_model=list[CustomerInvoiceResponse])
def list_customer_invoices(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("ar.customer_invoice", "read")),
) -> list[CustomerInvoiceResponse]:
    assert_company_access(
        db,
        user_id=user.id,
        resource="ar.customer_invoice",
        action="read",
        company_id=company_id,
    )
    return [
        CustomerInvoiceResponse.model_validate(invoice, from_attributes=True)
        for invoice in ar_service.list_customer_invoices(db, company_id=company_id)
    ]


@router.post("/customer-invoices/{invoice_id}/approve", response_model=CustomerInvoiceResponse)
def approve_customer_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ar.customer_invoice", "approve")),
) -> CustomerInvoiceResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ar.customer_invoice",
        action="approve",
        company_id=invoice.company_id,
    )
    invoice = ar_service.approve_customer_invoice(db, invoice_id=invoice_id)
    return CustomerInvoiceResponse.model_validate(invoice, from_attributes=True)


@router.post(
    "/customer-invoices/{invoice_id}/receipts", response_model=CustomerReceiptResponse, status_code=201
)
def collect_customer_receipt(
    invoice_id: uuid.UUID,
    payload: CustomerReceiptCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ar.customer_receipt", "create")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CustomerReceiptResponse:
    invoice = _resolve_invoice(db, invoice_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="ar.customer_receipt",
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
                command="ar.customer_receipt.create",
                payload=request_payload,
            )
            if outcome.is_replay:
                return CustomerReceiptResponse.model_validate(outcome.record.result)
        receipt = ar_service.collect_customer_receipt(
            db,
            invoice_id=invoice_id,
            treasury_account_id=payload.treasury_account_id,
            amount=payload.amount,
            receipt_date=payload.receipt_date,
            commit=outcome is None,
        )
        response = CustomerReceiptResponse.model_validate(receipt, from_attributes=True)
        if outcome is not None:
            idempotency_service.complete(
                db,
                outcome.record,
                result=response.model_dump(mode="json"),
                entity_type="CustomerReceipt",
                entity_id=receipt.id,
            )
            db.commit()
        return response
    except Exception:
        db.rollback()
        raise
