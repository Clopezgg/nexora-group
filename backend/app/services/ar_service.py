import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidFinancialReferenceError,
    InvalidInvoiceStateError,
    OverpaymentError,
)
from app.models.ar import CustomerInvoice, CustomerReceipt
from app.models.crm import Customer
from app.models.treasury import TreasuryAccount
from app.services import posting_service
from app.services.financial_validation_service import (
    assert_account_belongs_to_company,
    assert_customer_belongs_to_company,
    assert_operation_scope,
    assert_project_belongs_to_company,
)
from app.services.posting_service import JournalLineInput

"""Accounts Receivable (orden maestra §36). `customer_id` referencia la
entidad real `Customer` (Track E - Commercial, ver app/models/crm.py)."""


def create_customer_invoice(
    db: Session,
    *,
    company_id: uuid.UUID,
    customer_id: uuid.UUID,
    invoice_number: str,
    scope: str,
    project_id: uuid.UUID | None,
    revenue_account_id: uuid.UUID,
    receivable_account_id: uuid.UUID,
    currency_code: str,
    amount: Decimal,
    invoice_date: date,
    due_date: date,
    description: str | None,
    commit: bool = True,
) -> CustomerInvoice:
    if amount <= 0:
        raise OverpaymentError("La factura requiere amount > 0")
    assert_operation_scope(scope, project_id)
    assert_account_belongs_to_company(
        db,
        account_id=revenue_account_id,
        company_id=company_id,
        field_name="revenue_account_id",
    )
    assert_account_belongs_to_company(
        db,
        account_id=receivable_account_id,
        company_id=company_id,
        field_name="receivable_account_id",
    )
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    assert_customer_belongs_to_company(db, customer_id=customer_id, company_id=company_id)
    invoice = CustomerInvoice(
        company_id=company_id,
        customer_id=customer_id,
        invoice_number=invoice_number,
        scope=scope,
        project_id=project_id,
        revenue_account_id=revenue_account_id,
        receivable_account_id=receivable_account_id,
        currency_code=currency_code,
        amount=amount,
        invoice_date=invoice_date,
        due_date=due_date,
        description=description,
        status="DRAFT",
    )
    db.add(invoice)
    if commit:
        db.commit()
        db.refresh(invoice)
    else:
        db.flush()
    return invoice


def approve_customer_invoice(db: Session, *, invoice_id: uuid.UUID) -> CustomerInvoice:
    invoice = db.execute(
        select(CustomerInvoice).where(CustomerInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"CustomerInvoice {invoice_id} no existe")
    if invoice.status != "DRAFT":
        raise InvalidInvoiceStateError(
            f"Solo se puede aprobar una factura DRAFT (estado actual: {invoice.status})"
        )

    customer = db.get(Customer, invoice.customer_id)
    customer_name = customer.legal_name if customer is not None else str(invoice.customer_id)

    document = posting_service.post_manual(
        db,
        company_id=invoice.company_id,
        document_type_code="CIN",
        scope=invoice.scope,
        project_id=invoice.project_id,
        currency_code=invoice.currency_code,
        effective_date=invoice.invoice_date,
        lines=[
            JournalLineInput(
                account_id=invoice.receivable_account_id,
                debit_amount=invoice.amount,
                project_id=invoice.project_id,
                description=f"Factura {invoice.invoice_number} a {customer_name}",
            ),
            JournalLineInput(
                account_id=invoice.revenue_account_id,
                credit_amount=invoice.amount,
                description=f"Factura {invoice.invoice_number} a {customer_name}",
            ),
        ],
        description=f"Factura {invoice.invoice_number} a {customer_name}",
        source_type="customer_invoice",
        source_id=invoice.id,
        commit=False,
    )

    invoice.status = "APPROVED"
    invoice.accounting_document_id = document.id
    db.commit()
    db.refresh(invoice)
    return invoice


def collect_customer_receipt(
    db: Session,
    *,
    invoice_id: uuid.UUID,
    treasury_account_id: uuid.UUID,
    amount: Decimal,
    receipt_date: date,
    commit: bool = True,
) -> CustomerReceipt:
    invoice = db.execute(
        select(CustomerInvoice).where(CustomerInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"CustomerInvoice {invoice_id} no existe")
    if invoice.status not in ("APPROVED", "PARTIALLY_COLLECTED"):
        raise InvalidInvoiceStateError(
            f"No se puede cobrar una factura en estado {invoice.status}"
        )

    remaining = invoice.amount - invoice.amount_collected
    if amount <= 0 or amount > remaining:
        raise OverpaymentError(
            f"El cobro ({amount}) excede el saldo pendiente ({remaining}) de la factura"
        )

    treasury_account = db.get(TreasuryAccount, treasury_account_id)
    if treasury_account is None:
        raise ValueError(f"TreasuryAccount {treasury_account_id} no existe")
    if treasury_account.company_id != invoice.company_id:
        raise InvalidFinancialReferenceError(
            "treasury_account_id debe pertenecer a la compañía de la factura"
        )
    if treasury_account.currency_code != invoice.currency_code:
        raise InvalidFinancialReferenceError(
            "treasury_account_id debe usar la moneda de la factura"
        )

    customer = db.get(Customer, invoice.customer_id)
    customer_name = customer.legal_name if customer is not None else str(invoice.customer_id)

    document = posting_service.post_manual(
        db,
        company_id=invoice.company_id,
        document_type_code="REC",
        scope=invoice.scope,
        project_id=invoice.project_id,
        currency_code=invoice.currency_code,
        effective_date=receipt_date,
        lines=[
            JournalLineInput(
                account_id=treasury_account.gl_account_id,
                debit_amount=amount,
                description=f"Cobro factura {invoice.invoice_number}",
            ),
            JournalLineInput(
                account_id=invoice.receivable_account_id,
                credit_amount=amount,
                description=f"Cobro factura {invoice.invoice_number}",
            ),
        ],
        description=f"Cobro a {customer_name} - factura {invoice.invoice_number}",
        source_type="customer_invoice",
        source_id=invoice.id,
        commit=False,
    )

    receipt = CustomerReceipt(
        customer_invoice_id=invoice.id,
        treasury_account_id=treasury_account_id,
        amount=amount,
        receipt_date=receipt_date,
        accounting_document_id=document.id,
    )
    db.add(receipt)

    invoice.amount_collected += amount
    invoice.status = "COLLECTED" if invoice.amount_collected == invoice.amount else "PARTIALLY_COLLECTED"

    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(receipt)
    return receipt


def get_customer_invoice(db: Session, *, invoice_id: uuid.UUID) -> CustomerInvoice | None:
    return db.get(CustomerInvoice, invoice_id)


def list_customer_invoices(db: Session, *, company_id: uuid.UUID) -> list[CustomerInvoice]:
    return list(
        db.execute(
            select(CustomerInvoice)
            .where(CustomerInvoice.company_id == company_id)
            .order_by(CustomerInvoice.created_at.desc())
        ).scalars()
    )


def apply_invoice_reversal(db: Session, *, invoice_id: uuid.UUID, document_type_code: str) -> None:
    """Adaptador para posting_service.register_reversal_hook (NXR-REQ-0025,
    Corrections) -- mismo criterio que ap_service.apply_accrual_reversal.
    Revertir el asiento de una factura (document_type_code "CIN") sin
    sincronizar su status dejaría la factura APPROVED apuntando a un
    AccountingDocument ya REVERSED, pero todavía cobrable. El source_type
    "customer_invoice" también cubre el recibo ("REC"); revertir un
    recibo no está soportado todavía (reduciría amount_collected, reabriría
    la factura) y se rechaza explícitamente."""
    if document_type_code == "REC":
        raise InvalidInvoiceStateError(
            "Revertir el recibo de una factura no está soportado todavía; "
            "revierta solo el asiento de una factura sin cobros registrados"
        )
    if document_type_code != "CIN":
        return
    invoice = db.execute(
        select(CustomerInvoice).where(CustomerInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"CustomerInvoice {invoice_id} no existe")
    if invoice.amount_collected > 0:
        raise InvalidInvoiceStateError(
            "No se puede revertir el asiento de una factura con cobros registrados"
        )
    if invoice.status != "APPROVED":
        raise InvalidInvoiceStateError(
            f"No se puede revertir el asiento de una factura en estado {invoice.status}"
        )
    invoice.status = "CANCELLED"
