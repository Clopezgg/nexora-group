import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidFinancialReferenceError,
    InvalidInvoiceStateError,
    OverpaymentError,
)
from app.models.ap import (
    SupplierInvoice,
    SupplierInvoicePaymentPlanItem,
    SupplierPayment,
)
from app.models.accounting import AccountingDocument
from app.models.asset import FixedAsset
from app.models.supplier import Supplier
from app.models.treasury import TreasuryAccount
from app.services import approval_service, posting_service
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
    supplier_contract_id: uuid.UUID | None = None,
    commit: bool = True,
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
    if supplier_contract_id is not None:
        from app.models.supplier import SupplierContract

        contract = db.get(SupplierContract, supplier_contract_id)
        if contract is None or contract.company_id != company_id:
            raise InvalidFinancialReferenceError(
                "supplier_contract_id no existe o pertenece a otra compañía"
            )
        if contract.supplier_id != supplier_id:
            raise InvalidFinancialReferenceError(
                "El contrato pertenece a otro proveedor"
            )
        if contract.project_id is not None and contract.project_id != project_id:
            raise InvalidFinancialReferenceError(
                "El proyecto de la factura no coincide con el del contrato"
            )
        if contract.currency_code != currency_code:
            raise InvalidFinancialReferenceError(
                "La moneda de la factura no coincide con la del contrato"
            )
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
        supplier_contract_id=supplier_contract_id,
        status="DRAFT",
    )
    db.add(invoice)
    if commit:
        db.commit()
        db.refresh(invoice)
    else:
        db.flush()
    return invoice


def submit_supplier_invoice_for_approval(
    db: Session,
    *,
    invoice_id: uuid.UUID,
    requested_by: uuid.UUID,
    assigned_to: uuid.UUID,
    priority: str = "NORMAL",
) -> SupplierInvoice:
    """DRAFT -> REVIEW. Crea una ApprovalRequest real (Approval Inbox,
    Track G) en vez de dejar que la factura mute su propio estado sin
    pasar por segregación de funciones -- resuelve DEFERRED-FINAL-016.
    `approval_service.decide()` es quien finalmente llama
    `apply_approval_decision` (adaptador ya registrado en `main.py`) para
    aprobar/rechazar de verdad."""
    invoice = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status != "DRAFT":
        raise InvalidInvoiceStateError(
            f"Solo se puede enviar a aprobación una factura DRAFT (estado actual: {invoice.status})"
        )
    invoice.status = "REVIEW"
    db.flush()
    approval_service.create_request(
        db,
        policy_id=None,
        entity_type="ap.supplier_invoice",
        entity_id=invoice.id,
        company_id=invoice.company_id,
        requested_by=requested_by,
        module="ap",
        assigned_to=assigned_to,
        priority=priority,
        amount=invoice.amount + invoice.tax_amount,
        project_id=invoice.project_id,
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def approve_supplier_invoice(
    db: Session, *, invoice_id: uuid.UUID, commit: bool = True
) -> SupplierInvoice:
    """DRAFT o REVIEW -> APPROVED. Contabiliza el accrual: Debit gasto,
    Credit cuentas por pagar (orden maestra §34). DRAFT sigue siendo un
    estado válido de entrada para permitir la aprobación directa cuando no
    se pasó por el Approval Inbox (`submit_supplier_invoice_for_approval`);
    REVIEW es el estado real tras esa submission."""
    invoice = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status not in ("DRAFT", "REVIEW"):
        raise InvalidInvoiceStateError(
            f"Solo se puede aprobar una factura DRAFT o REVIEW (estado actual: {invoice.status})"
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
        effective_date=invoice.invoice_date,
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
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(invoice)
    return invoice


def cancel_supplier_invoice(
    db: Session, *, invoice_id: uuid.UUID, commit: bool = True
) -> SupplierInvoice:
    invoice = db.get(SupplierInvoice, invoice_id)
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status not in ("DRAFT", "REVIEW"):
        raise InvalidInvoiceStateError(
            "Solo se puede cancelar una factura DRAFT o REVIEW; una factura aprobada requiere "
            "reversal contable, no cancelación directa"
        )
    invoice.status = "CANCELLED"
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(invoice)
    return invoice


def pay_supplier_invoice(
    db: Session,
    *,
    invoice_id: uuid.UUID,
    treasury_account_id: uuid.UUID,
    amount: Decimal,
    payment_date: date,
    contract_allocations: list[dict] | None = None,
    contract_override_reason: str | None = None,
    bank_transaction_reference: str | None = None,
    payment_observations: str | None = None,
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
        effective_date=payment_date,
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
        bank_transaction_reference=(bank_transaction_reference or None),
        payment_observations=(payment_observations or None),
    )
    db.add(payment)
    db.flush()

    # Subledger contractual (orden maestra final §8): si la factura está
    # ligada a un contrato con plan de pagos, se registran las asignaciones
    # a las cuotas contractuales. NO reemplaza la contabilidad.
    if contract_allocations:
        from app.services import contract_payment_service

        total_allocated = sum(
            Decimal(str(a["amount_applied"])) for a in contract_allocations
        )
        if total_allocated != amount:
            raise InvalidFinancialReferenceError(
                "La suma de las asignaciones contractuales debe igualar el monto del pago."
            )
        contract_payment_service.allocate_payment(
            db,
            supplier_payment_id=payment.id,
            allocations=contract_allocations,
            override_reason=contract_override_reason,
            commit=False,
        )

    invoice.amount_paid += amount
    invoice.status = "PAID" if invoice.amount_paid == total else "PARTIALLY_PAID"

    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(payment)
    return payment


def apply_approval_decision(db: Session, *, invoice_id: uuid.UUID, decision: str) -> None:
    """Adaptador para Approval Inbox (Track G, `approval_service.decide()`)
    -- entry point nuevo, no toca la firma ni el comportamiento existente
    de `approve_supplier_invoice`/`cancel_supplier_invoice`. Delega en
    ellas: la transición real sigue viviendo únicamente ahí."""
    if decision == "APPROVED":
        approve_supplier_invoice(db, invoice_id=invoice_id, commit=False)
    elif decision == "REJECTED":
        cancel_supplier_invoice(db, invoice_id=invoice_id, commit=False)


def get_supplier_invoice(db: Session, *, invoice_id: uuid.UUID) -> SupplierInvoice | None:
    return db.get(SupplierInvoice, invoice_id)


# -- Plan de pago / cuotas (orden maestra Phase 2) ----------------------

_PLAN_EDITABLE_STATUSES = {"APPROVED", "SCHEDULED"}


def list_payment_plan(
    db: Session, *, invoice_id: uuid.UUID
) -> list[SupplierInvoicePaymentPlanItem]:
    return list(
        db.execute(
            select(SupplierInvoicePaymentPlanItem)
            .where(SupplierInvoicePaymentPlanItem.supplier_invoice_id == invoice_id)
            .order_by(SupplierInvoicePaymentPlanItem.sequence)
        ).scalars()
    )


def set_payment_plan(
    db: Session,
    *,
    invoice_id: uuid.UUID,
    installments: list[dict],
    commit: bool = True,
) -> list[SupplierInvoicePaymentPlanItem]:
    """Reemplaza el plan de pago de una factura. `installments` es una lista
    de `{"due_date": date, "amount": Decimal, "note": str | None}`.

    Invariantes:
    - la factura debe estar APPROVED o SCHEDULED (no DRAFT/REVIEW/PAID/CANCELLED);
    - no puede tener pagos aplicados todavía (`amount_paid == 0`);
    - la suma de las cuotas debe igualar exactamente el total de la factura;
    - fechas de vencimiento estrictamente crecientes;
    - al menos una cuota.
    """
    invoice = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.status not in _PLAN_EDITABLE_STATUSES:
        raise InvalidInvoiceStateError(
            f"No se puede planificar el pago de una factura en estado {invoice.status}"
        )
    if invoice.amount_paid > 0:
        raise InvalidInvoiceStateError(
            "La factura ya tiene pagos aplicados; el plan de pago no puede modificarse"
        )
    if not installments:
        raise ValueError("El plan de pago requiere al menos una cuota")

    total = invoice.amount + invoice.tax_amount
    plan_total = sum((Decimal(str(item["amount"])) for item in installments), Decimal("0"))
    if plan_total != total:
        raise OverpaymentError(
            f"La suma de las cuotas ({plan_total}) debe igualar el total de la factura ({total})"
        )

    previous_due: date | None = None
    for item in installments:
        if Decimal(str(item["amount"])) <= 0:
            raise ValueError("Cada cuota debe tener un monto mayor que cero")
        due = item["due_date"]
        if previous_due is not None and due <= previous_due:
            raise ValueError("Las fechas de vencimiento de las cuotas deben ser crecientes")
        previous_due = due

    for existing in list_payment_plan(db, invoice_id=invoice_id):
        db.delete(existing)
    db.flush()

    rows: list[SupplierInvoicePaymentPlanItem] = []
    for index, item in enumerate(installments, start=1):
        row = SupplierInvoicePaymentPlanItem(
            supplier_invoice_id=invoice_id,
            sequence=index,
            due_date=item["due_date"],
            amount=Decimal(str(item["amount"])),
            note=item.get("note"),
        )
        db.add(row)
        rows.append(row)

    invoice.status = "SCHEDULED"
    invoice.due_date = installments[-1]["due_date"]
    db.flush()
    if commit:
        db.commit()
        for row in rows:
            db.refresh(row)
    return rows


def list_supplier_payments(
    db: Session, *, invoice_id: uuid.UUID
) -> list[SupplierPayment]:
    """Historial de pagos de una factura (orden maestra Phase 2)."""
    return list(
        db.execute(
            select(SupplierPayment)
            .where(SupplierPayment.supplier_invoice_id == invoice_id)
            .order_by(SupplierPayment.payment_date, SupplierPayment.created_at)
        ).scalars()
    )


def list_supplier_invoices(db: Session, *, company_id: uuid.UUID) -> list[SupplierInvoice]:
    return list(
        db.execute(
            select(SupplierInvoice)
            .where(SupplierInvoice.company_id == company_id)
            .order_by(SupplierInvoice.created_at.desc())
        ).scalars()
    )


def apply_accrual_reversal(db: Session, *, invoice_id: uuid.UUID, document_type_code: str) -> None:
    """Adaptador para posting_service.register_reversal_hook (NXR-REQ-0025,
    Corrections). Revertir el accrual de una factura (document_type_code
    "SIN") sin sincronizar su status dejaría la factura APPROVED
    apuntando a un AccountingDocument ya REVERSED -- pagable de nuevo
    pese a que el GL ya no refleja el gasto. El source_type
    "supplier_invoice" también cubre el pago ("PAY"); ese caso todavía no
    tiene un flujo de reversión propio (reducir amount_paid, reabrir la
    factura) y se rechaza explícitamente en vez de dejar un estado a
    medias -- ver docs/DEFERRED.md."""
    if document_type_code == "PAY":
        raise InvalidInvoiceStateError(
            "Revertir el pago de una factura no está soportado todavía; "
            "revierta solo el accrual de una factura sin pagos registrados"
        )
    if document_type_code != "SIN":
        return
    invoice = db.execute(
        select(SupplierInvoice).where(SupplierInvoice.id == invoice_id).with_for_update()
    ).scalar_one_or_none()
    if invoice is None:
        raise ValueError(f"SupplierInvoice {invoice_id} no existe")
    if invoice.amount_paid > 0:
        raise InvalidInvoiceStateError(
            "No se puede revertir el accrual de una factura con pagos registrados"
        )
    active_capitalized_asset_id = db.execute(
        select(FixedAsset.id)
        .join(
            AccountingDocument,
            AccountingDocument.id == FixedAsset.capitalization_document_id,
        )
        .where(
            FixedAsset.supplier_invoice_id == invoice.id,
            AccountingDocument.status == "POSTED",
        )
    ).scalar_one_or_none()
    if active_capitalized_asset_id is not None:
        raise InvalidInvoiceStateError(
            "No se puede revertir el accrual mientras la factura conserve una "
            "capitalización de activo; revierta primero el asiento CAP"
        )
    if invoice.status != "APPROVED":
        raise InvalidInvoiceStateError(
            f"No se puede revertir el accrual de una factura en estado {invoice.status}"
        )
    invoice.status = "CANCELLED"


def build_payment_proposal(db: Session, *, company_id, as_of: date, horizon_days: int = 14) -> dict:
    """Propuesta de pago: facturas de proveedor abiertas con saldo pendiente
    cuyo vencimiento (o próxima cuota impaga) cae dentro del horizonte o ya
    está vencido. Ordenada por urgencia. Orden maestra Phase 7."""
    from app.models.supplier import Supplier

    horizon_end = as_of + timedelta(days=horizon_days)
    invoices = db.execute(
        select(SupplierInvoice)
        .where(SupplierInvoice.company_id == company_id)
        .where(SupplierInvoice.status.in_(_PLAN_EDITABLE_STATUSES | {"PARTIALLY_PAID"}))
    ).scalars().all()

    items: list[dict] = []
    total = Decimal("0")
    for invoice in invoices:
        remaining = (invoice.amount + invoice.tax_amount) - invoice.amount_paid
        if remaining <= 0:
            continue
        plan = list_payment_plan(db, invoice_id=invoice.id)
        next_due = min((p.due_date for p in plan), default=invoice.due_date) if plan else invoice.due_date
        if next_due > horizon_end:
            continue
        supplier = db.get(Supplier, invoice.supplier_id)
        items.append(
            {
                "invoiceId": str(invoice.id),
                "invoiceNumber": invoice.invoice_number,
                "supplierName": (supplier.trade_name or supplier.legal_name) if supplier else None,
                "dueDate": next_due.isoformat(),
                "remaining": str(remaining),
                "overdue": next_due < as_of,
            }
        )
        total += remaining

    items.sort(key=lambda x: (not x["overdue"], x["dueDate"]))
    return {"horizonDays": horizon_days, "asOf": as_of.isoformat(), "total": str(total), "items": items}
