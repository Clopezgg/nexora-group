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
from app.models.ap import SupplierInvoice, SupplierPayment
from app.models.supplier import Supplier
from app.models.treasury import TreasuryAccount
from app.services import posting_service
from app.services.financial_validation_service import (
    assert_account_belongs_to_company,
    assert_cost_center_belongs_to_company,
    assert_operation_scope,
    assert_project_belongs_to_company,
    assert_supplier_belongs_to_company,
)
from app.services.posting_service import JournalLineInput

"""Accounts Payable (orden maestra §34-35). `supplier_id` referencia la
entidad real `Supplier` (Track C - Suppliers/Contracts)."""


def create_supplier_invoice(
    db: Session,
    *,
    company_id: uuid.UUID,
    supplier_id: uuid.UUID,
    invoice_number: str,
    scope: str,
    project_id: uuid.UUID | None,
    cost_center_id: uuid.UUID | None,
    expense_account_id: uuid.UUID,
    payable_account_id: uuid.UUID,
    currency_code: str,
    amount: Decimal,
    tax_amount: Decimal,
    invoice_date: date,
    due_date: date,
    description: str | None,
) -> SupplierInvoice:
    if amount <= 0 or tax_amount < 0:
        raise OverpaymentError("La factura requiere amount > 0 y tax_amount >= 0")
    assert_operation_scope(scope, project_id)
    assert_account_belongs_to_company(
        db,
        account_id=expense_account_id,
        company_id=company_id,
        field_name="expense_account_id",
    )
    assert_account_belongs_to_company(
        db,
        account_id=payable_account_id,
        company_id=company_id,
        field_name="payable_account_id",
    )
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    assert_cost_center_belongs_to_company(
        db, cost_center_id=cost_center_id, company_id=company_id
    )
    assert_supplier_belongs_to_company(db, supplier_id=supplier_id, company_id=company_id)
    invoice = SupplierInvoice(
        company_id=company_id,
        supplier_id=supplier_id,
        invoice_number=invoice_number,
        scope=scope,
        project_id=project_id,
        cost_center_id=cost_center_id,
        expense_account_id=expense_account_id,
        payable_account_id=payable_account_id,
        currency_code=currency_code,
        amount=amount,
        tax_amount=tax_amount,
        invoice_date=invoice_date,
        due_date=due_date,
        description=description,
        status="DRAFT",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def approve_supplier_invoice(db: Session, *, invoice_id: uuid.UUID) -> SupplierInvoice:
    """DRAFT -> APPROVED. Contabiliza el accrual: Debit gasto, Credit
    cuentas por pagar (orden maestra §34)."""
    invoice = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status != "DRAFT":
        raise InvalidInvoiceStateError(
            f"Solo se puede aprobar una factura DRAFT (estado actual: {invoice.status})"
        )

    supplier = db.get(Supplier, invoice.supplier_id)
    supplier_name = supplier.legal_name if supplier is not None else str(invoice.supplier_id)

    total = invoice.amount + invoice.tax_amount
    document = posting_service.post_manual(
        db,
        company_id=invoice.company_id,
        document_type_code="SIN",
        scope=invoice.scope,
        project_id=invoice.project_id,
        currency_code=invoice.currency_code,
        lines=[
            JournalLineInput(
                account_id=invoice.expense_account_id,
                debit_amount=total,
                project_id=invoice.project_id,
                cost_center_id=invoice.cost_center_id,
                description=f"Factura {invoice.invoice_number} de {supplier_name}",
            ),
            JournalLineInput(
                account_id=invoice.payable_account_id,
                credit_amount=total,
                description=f"Factura {invoice.invoice_number} de {supplier_name}",
            ),
        ],
        description=f"Accrual factura {invoice.invoice_number} ({supplier_name})",
        source_type="supplier_invoice",
        source_id=invoice.id,
        commit=False,
    )

    invoice.status = "APPROVED"
    invoice.accrual_document_id = document.id
    db.commit()
    db.refresh(invoice)
    return invoice


def cancel_supplier_invoice(db: Session, *, invoice_id: uuid.UUID) -> SupplierInvoice:
    invoice = db.get(SupplierInvoice, invoice_id)
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status != "DRAFT":
        raise InvalidInvoiceStateError(
            "Solo se puede cancelar una factura DRAFT; una factura aprobada requiere "
            "reversal contable, no cancelación directa"
        )
    invoice.status = "CANCELLED"
    db.commit()
    db.refresh(invoice)
    return invoice


def pay_supplier_invoice(
    db: Session,
    *,
    invoice_id: uuid.UUID,
    treasury_account_id: uuid.UUID,
    amount: Decimal,
    payment_date: date,
    commit: bool = True,
) -> SupplierPayment:
    """Pago simple contra UNA factura (sin allocation multi-factura --
    deuda intencional, ver docs/TREASURY.md)."""
    invoice = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status not in ("APPROVED", "SCHEDULED", "PARTIALLY_PAID"):
        raise InvalidInvoiceStateError(
            f"No se puede pagar una factura en estado {invoice.status}"
        )

    total = invoice.amount + invoice.tax_amount
    remaining = total - invoice.amount_paid
    if amount <= 0 or amount > remaining:
        raise OverpaymentError(
            f"El pago ({amount}) excede el saldo pendiente ({remaining}) de la factura"
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

    supplier = db.get(Supplier, invoice.supplier_id)
    supplier_name = supplier.legal_name if supplier is not None else str(invoice.supplier_id)

    document = posting_service.post_manual(
        db,
        company_id=invoice.company_id,
        document_type_code="PAY",
        scope=invoice.scope,
        project_id=invoice.project_id,
        currency_code=invoice.currency_code,
        lines=[
            JournalLineInput(
                account_id=invoice.payable_account_id,
                debit_amount=amount,
                description=f"Pago factura {invoice.invoice_number}",
            ),
            JournalLineInput(
                account_id=treasury_account.gl_account_id,
                credit_amount=amount,
                description=f"Pago factura {invoice.invoice_number}",
            ),
        ],
        description=f"Pago a {supplier_name} - factura {invoice.invoice_number}",
        source_type="supplier_invoice",
        source_id=invoice.id,
        commit=False,
    )

    payment = SupplierPayment(
        supplier_invoice_id=invoice.id,
        treasury_account_id=treasury_account_id,
        amount=amount,
        payment_date=payment_date,
        accounting_document_id=document.id,
    )
    db.add(payment)

    invoice.amount_paid += amount
    invoice.status = "PAID" if invoice.amount_paid == total else "PARTIALLY_PAID"

    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(payment)
    return payment


def get_supplier_invoice(db: Session, *, invoice_id: uuid.UUID) -> SupplierInvoice | None:
    return db.get(SupplierInvoice, invoice_id)


def list_supplier_invoices(db: Session, *, company_id: uuid.UUID) -> list[SupplierInvoice]:
    return list(
        db.execute(
            select(SupplierInvoice)
            .where(SupplierInvoice.company_id == company_id)
            .order_by(SupplierInvoice.created_at.desc())
        ).scalars()
    )
