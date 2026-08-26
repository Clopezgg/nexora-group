import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import BudgetCurrencyMismatchError, NotFoundError
from app.models.ap import SupplierInvoice
from app.models.company import Company

# An invoice only carries a real accrual once posting_service has actually
# committed the Debit expense / Credit payable document -- see
# ap_service.approve_supplier_invoice. DRAFT/REVIEW/CANCELLED never posted
# one.
ACCRUED_STATUSES = ("APPROVED", "SCHEDULED", "PARTIALLY_PAID", "PAID", "RECONCILED")


def _assert_functional_currency(company: Company, currency_code: str) -> None:
    if company.functional_currency_code is None:
        raise BudgetCurrencyMismatchError(
            f"La company {company.id} no tiene moneda funcional; no se pueden agregar montos de AP"
        )
    if currency_code != company.functional_currency_code:
        raise BudgetCurrencyMismatchError(
            f"La factura usa {currency_code}, pero la moneda funcional de la company es "
            f"{company.functional_currency_code}; no existe una política FX autoritativa"
        )


def project_accrued_total(db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Decimal:
    """Accrued AP total for Budget vs Actual (NXR-REQ-0034). Mirrors
    procurement_repository.project_commitment_total's currency-authority
    guard: this codebase has no FX policy yet, so a foreign-currency
    invoice on this project raises instead of silently mixing currencies
    into one nominal figure."""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"Company {company_id} no existe")
    total_expr = func.sum(SupplierInvoice.amount + SupplierInvoice.tax_amount)
    stmt = (
        select(SupplierInvoice.currency_code, total_expr.label("total"))
        .where(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.project_id == project_id,
            SupplierInvoice.status.in_(ACCRUED_STATUSES),
        )
        .group_by(SupplierInvoice.currency_code)
    )
    accrued = Decimal("0")
    for currency_code, nominal_total in db.execute(stmt):
        _assert_functional_currency(company, currency_code)
        accrued += Decimal(nominal_total)
    return accrued


def project_paid_total(db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Decimal:
    """Paid AP total for Budget vs Actual (NXR-REQ-0035). Sums
    `SupplierInvoice.amount_paid`, which ap_service.pay_supplier_invoice
    already maintains per invoice -- no need to re-derive it from
    SupplierPayment rows."""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"Company {company_id} no existe")
    total_expr = func.sum(SupplierInvoice.amount_paid)
    stmt = (
        select(SupplierInvoice.currency_code, total_expr.label("total"))
        .where(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.project_id == project_id,
            SupplierInvoice.amount_paid > 0,
        )
        .group_by(SupplierInvoice.currency_code)
    )
    paid = Decimal("0")
    for currency_code, nominal_total in db.execute(stmt):
        _assert_functional_currency(company, currency_code)
        paid += Decimal(nominal_total)
    return paid
