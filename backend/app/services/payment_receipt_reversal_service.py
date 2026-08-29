import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError, InvalidInvoiceStateError
from app.models.accounting import AccountingDocument, JournalLine
from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.ar import CustomerInvoice, CustomerReceipt
from app.services import posting_service
from app.services.posting_service import JournalLineInput


def _reverse_posted_document(
    db: Session,
    *,
    original: AccountingDocument,
    reason: str,
    source_type: str,
    source_id: uuid.UUID,
) -> AccountingDocument:
    if original.status != "POSTED":
        raise InvalidInvoiceStateError(
            f"El documento contable original ya no es reversible (estado {original.status})"
        )
    lines = list(
        db.execute(
            select(JournalLine).where(JournalLine.accounting_document_id == original.id)
        ).scalars()
    )
    if not lines:
        raise InvalidFinancialReferenceError("El documento original no contiene líneas contables")
    reversal_lines = [
        JournalLineInput(
            account_id=line.account_id,
            debit_amount=line.credit_amount,
            credit_amount=line.debit_amount,
            description=f"Reversal de {original.document_number}: {line.description or ''}".strip(),
            project_id=line.project_id,
            cost_center_id=line.cost_center_id,
            extra_dimensions=line.extra_dimensions,
        )
        for line in lines
    ]
    reversal = posting_service.post_manual(
        db,
        company_id=original.company_id,
        document_type_code="ANU",
        scope=original.scope,
        project_id=original.project_id,
        currency_code=original.currency_code,
        fx_rate=original.fx_rate,
        lines=reversal_lines,
        description=f"Reversal de {original.document_number}: {reason}",
        source_type=source_type,
        source_id=source_id,
        commit=False,
    )
    original.status = "REVERSED"
    original.reversed_document_id = reversal.id
    original.reversal_reason = reason
    db.flush()
    return reversal


def list_supplier_payments(db: Session, *, invoice_id: uuid.UUID) -> list[SupplierPayment]:
    return list(
        db.execute(
            select(SupplierPayment)
            .where(SupplierPayment.supplier_invoice_id == invoice_id)
            .order_by(SupplierPayment.payment_date.desc(), SupplierPayment.created_at.desc())
        ).scalars()
    )


def reverse_supplier_payment(
    db: Session,
    *,
    payment_id: uuid.UUID,
    reason: str,
    commit: bool = True,
) -> tuple[SupplierPayment, SupplierInvoice, AccountingDocument]:
    if not reason.strip():
        raise InvalidFinancialReferenceError("El motivo del reversal es obligatorio")
    payment = db.execute(
        select(SupplierPayment).where(SupplierPayment.id == payment_id).with_for_update()
    ).scalar_one_or_none()
    if payment is None:
        raise InvalidFinancialReferenceError("El pago de proveedor no existe")
    invoice = db.execute(
        select(SupplierInvoice)
        .where(SupplierInvoice.id == payment.supplier_invoice_id)
        .with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de proveedor del pago no existe")
    original = db.execute(
        select(AccountingDocument)
        .where(AccountingDocument.id == payment.accounting_document_id)
        .with_for_update()
    ).scalar_one_or_none()
    if original is None:
        raise InvalidFinancialReferenceError("El documento contable del pago no existe")
    if original.document_type_code != "PAY":
        raise InvalidFinancialReferenceError("El documento contable no corresponde a un pago AP")
    if invoice.amount_paid < payment.amount:
        raise InvalidInvoiceStateError("El saldo pagado de la factura es inconsistente con el pago")

    reversal = _reverse_posted_document(
        db,
        original=original,
        reason=reason.strip(),
        source_type="supplier_payment_reversal",
        source_id=payment.id,
    )
    invoice.amount_paid = Decimal(invoice.amount_paid) - Decimal(payment.amount)
    total = Decimal(invoice.amount) + Decimal(invoice.tax_amount)
    if invoice.amount_paid == 0:
        invoice.status = "APPROVED"
    elif invoice.amount_paid < total:
        invoice.status = "PARTIALLY_PAID"
    else:
        invoice.status = "PAID"
    if commit:
        db.commit()
        db.refresh(payment)
        db.refresh(invoice)
        db.refresh(reversal)
    else:
        db.flush()
    return payment, invoice, reversal


def list_customer_receipts(db: Session, *, invoice_id: uuid.UUID) -> list[CustomerReceipt]:
    return list(
        db.execute(
            select(CustomerReceipt)
            .where(CustomerReceipt.customer_invoice_id == invoice_id)
            .order_by(CustomerReceipt.receipt_date.desc(), CustomerReceipt.created_at.desc())
        ).scalars()
    )


def reverse_customer_receipt(
    db: Session,
    *,
    receipt_id: uuid.UUID,
    reason: str,
    commit: bool = True,
) -> tuple[CustomerReceipt, CustomerInvoice, AccountingDocument]:
    if not reason.strip():
        raise InvalidFinancialReferenceError("El motivo del reversal es obligatorio")
    receipt = db.execute(
        select(CustomerReceipt).where(CustomerReceipt.id == receipt_id).with_for_update()
    ).scalar_one_or_none()
    if receipt is None:
        raise InvalidFinancialReferenceError("El cobro de cliente no existe")
    invoice = db.execute(
        select(CustomerInvoice)
        .where(CustomerInvoice.id == receipt.customer_invoice_id)
        .with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de cliente del cobro no existe")
    original = db.execute(
        select(AccountingDocument)
        .where(AccountingDocument.id == receipt.accounting_document_id)
        .with_for_update()
    ).scalar_one_or_none()
    if original is None:
        raise InvalidFinancialReferenceError("El documento contable del cobro no existe")
    if original.document_type_code != "REC":
        raise InvalidFinancialReferenceError("El documento contable no corresponde a un cobro AR")
    if invoice.amount_collected < receipt.amount:
        raise InvalidInvoiceStateError("El saldo cobrado de la factura es inconsistente con el cobro")

    reversal = _reverse_posted_document(
        db,
        original=original,
        reason=reason.strip(),
        source_type="customer_receipt_reversal",
        source_id=receipt.id,
    )
    invoice.amount_collected = Decimal(invoice.amount_collected) - Decimal(receipt.amount)
    if invoice.amount_collected == 0:
        invoice.status = "APPROVED"
    elif invoice.amount_collected < invoice.amount:
        invoice.status = "PARTIALLY_COLLECTED"
    else:
        invoice.status = "COLLECTED"
    if commit:
        db.commit()
        db.refresh(receipt)
        db.refresh(invoice)
        db.refresh(reversal)
    else:
        db.flush()
    return receipt, invoice, reversal
