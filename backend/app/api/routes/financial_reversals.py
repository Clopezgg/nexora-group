import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.domain.errors import InvalidFinancialReferenceError
from app.schemas.ap import SupplierPaymentResponse
from app.schemas.ar import CustomerReceiptResponse
from app.schemas.reversal import BusinessReversalResponse, ReversalRequest
from app.services import ap_service, ar_service, audit_service, payment_receipt_reversal_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(tags=["financial-reversals"])


@router.get(
    "/ap/supplier-invoices/{invoice_id}/payments",
    response_model=list[SupplierPaymentResponse],
)
def list_supplier_payments(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ap.supplier_payment", "read")),
) -> list[SupplierPaymentResponse]:
    invoice = ap_service.get_supplier_invoice(db, invoice_id=invoice_id)
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de proveedor no existe")
    assert_company_access(
        db,
        user_id=user.id,
        resource="ap.supplier_payment",
        action="read",
        company_id=invoice.company_id,
    )
    return [
        SupplierPaymentResponse.model_validate(row, from_attributes=True)
        for row in payment_receipt_reversal_service.list_supplier_payments(db, invoice_id=invoice_id)
    ]


@router.post(
    "/ap/supplier-payments/{payment_id}/reverse",
    response_model=BusinessReversalResponse,
)
def reverse_supplier_payment(
    payment_id: uuid.UUID,
    payload: ReversalRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "reverse")),
    correlation_id: str = Depends(get_correlation_id),
) -> BusinessReversalResponse:
    from app.models.ap import SupplierInvoice, SupplierPayment

    payment = db.get(SupplierPayment, payment_id)
    if payment is None:
        raise InvalidFinancialReferenceError("El pago de proveedor no existe")
    invoice = db.get(SupplierInvoice, payment.supplier_invoice_id)
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de proveedor no existe")
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="reverse",
        company_id=invoice.company_id,
    )
    try:
        original_document_id = payment.accounting_document_id
        payment, invoice, reversal = payment_receipt_reversal_service.reverse_supplier_payment(
            db, payment_id=payment_id, reason=payload.reason, commit=False
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="ap.supplier_payment.reverse",
            entity_type="ap.supplier_payment",
            entity_id=payment.id,
            company_id=invoice.company_id,
            project_id=invoice.project_id,
            before={
                "accountingDocumentId": str(original_document_id),
                "amount": str(payment.amount),
            },
            after={
                "reversalAccountingDocumentId": str(reversal.id),
                "invoiceStatus": invoice.status,
                "amountPaid": str(invoice.amount_paid),
                "reason": payload.reason,
            },
            correlation_id=correlation_id,
        )
        db.commit()
        return BusinessReversalResponse(
            original_id=payment.id,
            invoice_id=invoice.id,
            original_accounting_document_id=original_document_id,
            reversal_accounting_document_id=reversal.id,
            invoice_status=invoice.status,
            applied_amount_after_reversal=invoice.amount_paid,
        )
    except Exception:
        db.rollback()
        raise


@router.get(
    "/ar/customer-invoices/{invoice_id}/receipts",
    response_model=list[CustomerReceiptResponse],
)
def list_customer_receipts(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("ar.customer_receipt", "read")),
) -> list[CustomerReceiptResponse]:
    invoice = ar_service.get_customer_invoice(db, invoice_id=invoice_id)
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de cliente no existe")
    assert_company_access(
        db,
        user_id=user.id,
        resource="ar.customer_receipt",
        action="read",
        company_id=invoice.company_id,
    )
    return [
        CustomerReceiptResponse.model_validate(row, from_attributes=True)
        for row in payment_receipt_reversal_service.list_customer_receipts(db, invoice_id=invoice_id)
    ]


@router.post(
    "/ar/customer-receipts/{receipt_id}/reverse",
    response_model=BusinessReversalResponse,
)
def reverse_customer_receipt(
    receipt_id: uuid.UUID,
    payload: ReversalRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.journal_entry", "reverse")),
    correlation_id: str = Depends(get_correlation_id),
) -> BusinessReversalResponse:
    from app.models.ar import CustomerInvoice, CustomerReceipt

    receipt = db.get(CustomerReceipt, receipt_id)
    if receipt is None:
        raise InvalidFinancialReferenceError("El cobro de cliente no existe")
    invoice = db.get(CustomerInvoice, receipt.customer_invoice_id)
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de cliente no existe")
    assert_company_access(
        db,
        user_id=user.id,
        resource="accounting.journal_entry",
        action="reverse",
        company_id=invoice.company_id,
    )
    try:
        original_document_id = receipt.accounting_document_id
        receipt, invoice, reversal = payment_receipt_reversal_service.reverse_customer_receipt(
            db, receipt_id=receipt_id, reason=payload.reason, commit=False
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="ar.customer_receipt.reverse",
            entity_type="ar.customer_receipt",
            entity_id=receipt.id,
            company_id=invoice.company_id,
            project_id=invoice.project_id,
            before={
                "accountingDocumentId": str(original_document_id),
                "amount": str(receipt.amount),
            },
            after={
                "reversalAccountingDocumentId": str(reversal.id),
                "invoiceStatus": invoice.status,
                "amountCollected": str(invoice.amount_collected),
                "reason": payload.reason,
            },
            correlation_id=correlation_id,
        )
        db.commit()
        return BusinessReversalResponse(
            original_id=receipt.id,
            invoice_id=invoice.id,
            original_accounting_document_id=original_document_id,
            reversal_accounting_document_id=reversal.id,
            invoice_status=invoice.status,
            applied_amount_after_reversal=invoice.amount_collected,
        )
    except Exception:
        db.rollback()
        raise
