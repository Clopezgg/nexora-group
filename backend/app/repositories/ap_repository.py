import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import BudgetCurrencyMismatchError, NotFoundError
from app.models.ap import SupplierInvoice
from app.models.chart_of_accounts import Account
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


def _project_invoice_total_by_account_type(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    include_types: tuple[str, ...] | None = None,
    exclude_types: tuple[str, ...] | None = None,
) -> Decimal:
    """Sum of accrued PROJECT AP invoices, filtered by the *debit* account's
    type. ORDEN MAESTRA §13/§15: an invoice booked to an ASSET account is a
    contractual advance / prepayment, not project cost — it must be kept out
    of the `accrued` figure that drives Budget vs Actual."""
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"Company {company_id} no existe")
    total_expr = func.sum(SupplierInvoice.amount + SupplierInvoice.tax_amount)
    stmt = (
        select(SupplierInvoice.currency_code, total_expr.label("total"))
        .join(Account, Account.id == SupplierInvoice.expense_account_id)
        .where(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.project_id == project_id,
            SupplierInvoice.status.in_(ACCRUED_STATUSES),
        )
        .group_by(SupplierInvoice.currency_code)
    )
    if include_types is not None:
        stmt = stmt.where(Account.account_type.in_(include_types))
    if exclude_types is not None:
        stmt = stmt.where(Account.account_type.not_in(exclude_types))
    total = Decimal("0")
    for currency_code, nominal_total in db.execute(stmt):
        _assert_functional_currency(company, currency_code)
        total += Decimal(nominal_total)
    return total


def project_accrued_total(db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Decimal:
    """Accrued PROJECT AP cost for Budget vs Actual (NXR-REQ-0034). Mirrors
    procurement_repository.project_commitment_total's currency-authority
    guard: this codebase has no FX policy yet, so a foreign-currency
    invoice on this project raises instead of silently mixing currencies
    into one nominal figure. Advances/prepayments (ASSET debit) are excluded
    — see `project_advance_total`."""
    return _project_invoice_total_by_account_type(
        db, company_id=company_id, project_id=project_id, exclude_types=("ASSET",)
    )


def project_advance_total(db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID) -> Decimal:
    """PROJECT advances / prepayments (ASSET). ORDEN MAESTRA §15/§23: reported
    separately from recognised cost — never consumes the project's budget.

    Fuente de verdad: el saldo GL (débito − crédito) de la cuenta de anticipos
    configurada de la compañía para este proyecto — cubre tanto el accrual de
    una factura ASSET como una reclasificación contable (§7). Más las facturas
    ASSET devengadas cuyo débito NO es esa cuenta (para no doble contar)."""
    from app.models.accounting import LEDGER_EFFECTIVE_STATUSES, AccountingDocument, JournalLine

    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(f"Company {company_id} no existe")

    gl_advance = Decimal("0")
    if company.supplier_advance_account_id is not None:
        gl_advance = Decimal(
            db.execute(
                select(
                    func.coalesce(func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0)
                )
                .join(AccountingDocument, AccountingDocument.id == JournalLine.accounting_document_id)
                .where(
                    JournalLine.account_id == company.supplier_advance_account_id,
                    JournalLine.project_id == project_id,
                    AccountingDocument.status.in_(LEDGER_EFFECTIVE_STATUSES),
                )
            ).scalar_one()
        )

    other_asset_invoices = Decimal(
        db.execute(
            select(func.coalesce(func.sum(SupplierInvoice.amount + SupplierInvoice.tax_amount), 0))
            .join(Account, Account.id == SupplierInvoice.expense_account_id)
            .where(
                SupplierInvoice.company_id == company_id,
                SupplierInvoice.project_id == project_id,
                SupplierInvoice.status.in_(ACCRUED_STATUSES),
                Account.account_type == "ASSET",
                SupplierInvoice.expense_account_id != company.supplier_advance_account_id
                if company.supplier_advance_account_id is not None
                else True,
            )
        ).scalar_one()
    )
    return gl_advance + other_asset_invoices


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
