"""Commitment Engine — un solo cálculo canónico del compromiso de un proyecto
(ORDEN MAESTRA §18-§23).

Regla de no duplicación: una PurchaseOrder ligada a un SupplierContract es un
DESGLOSE del compromiso contractual, nunca un compromiso adicional. Una factura
de proveedor RELEVA (drawdown) el compromiso — el saldo abierto baja cuando se
devenga, no cuando se paga.

    total_commitment      = contract_commitment + standalone_po_commitment
    invoiced_against      = Σ facturas devengadas (débito EXPENSE) ligadas a un
                            contrato o a una PO
    open_commitment       = max(total_commitment - invoiced_against, 0)

`open_commitment` + `actual` (costo devengado) = exposición total del proyecto;
el presupuesto disponible es `authorized - open_commitment - actual`.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ap import SupplierInvoice
from app.models.chart_of_accounts import Account
from app.models.supplier import SupplierContract
from app.repositories import ap_repository, procurement_repository

_ZERO = Decimal("0")

# Un contrato compromete presupuesto cuando está vigente; DRAFT todavía no.
_COMMITTING_CONTRACT_STATUSES = ("ACTIVE", "COMPLETED")


@dataclass
class CommitmentBreakdown:
    contract_commitment: Decimal
    po_under_contract: Decimal          # informativo: POs que desglosan contratos
    standalone_po_commitment: Decimal   # POs sin contrato → se suman aparte
    total_commitment: Decimal
    invoiced_against_commitment: Decimal
    open_commitment: Decimal


def _contract_commitment(db: Session, *, project_id: uuid.UUID) -> Decimal:
    return Decimal(
        db.execute(
            select(func.coalesce(func.sum(SupplierContract.value), 0)).where(
                SupplierContract.project_id == project_id,
                SupplierContract.status.in_(_COMMITTING_CONTRACT_STATUSES),
            )
        ).scalar_one()
    )


def _invoiced_against_commitment(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID
) -> Decimal:
    """Facturas devengadas del proyecto que relevan un compromiso — ligadas a un
    contrato o a una PO — excluyendo débitos ASSET (anticipos, §15)."""
    total_expr = func.sum(SupplierInvoice.amount + SupplierInvoice.tax_amount)
    stmt = (
        select(total_expr)
        .join(Account, Account.id == SupplierInvoice.expense_account_id)
        .where(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.project_id == project_id,
            SupplierInvoice.status.in_(ap_repository.ACCRUED_STATUSES),
            Account.account_type != "ASSET",
            (SupplierInvoice.supplier_contract_id.is_not(None))
            | (SupplierInvoice.purchase_order_id.is_not(None)),
        )
    )
    return Decimal(db.execute(stmt).scalar_one() or 0)


def compute_breakdown(
    db: Session, *, company_id: uuid.UUID, project_id: uuid.UUID
) -> CommitmentBreakdown:
    contract_commitment = _contract_commitment(db, project_id=project_id)
    standalone_po = procurement_repository.project_commitment_total(
        db, company_id=company_id, project_id=project_id, under_contract=False
    )
    po_under_contract = procurement_repository.project_commitment_total(
        db, company_id=company_id, project_id=project_id, under_contract=True
    )
    total_commitment = contract_commitment + standalone_po
    invoiced = _invoiced_against_commitment(db, company_id=company_id, project_id=project_id)
    open_commitment = max(total_commitment - invoiced, _ZERO)
    return CommitmentBreakdown(
        contract_commitment=contract_commitment,
        po_under_contract=po_under_contract,
        standalone_po_commitment=standalone_po,
        total_commitment=total_commitment,
        invoiced_against_commitment=invoiced,
        open_commitment=open_commitment,
    )
