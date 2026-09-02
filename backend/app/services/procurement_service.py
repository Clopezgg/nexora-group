import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidFinancialReferenceError,
    InvalidProcurementStateError,
    ProcurementCurrencyMismatchError,
)
from app.models.company import Company
from app.models.procurement import (
    GoodsReceipt,
    PurchaseOrder,
    PurchaseRequisition,
    RequestForQuotation,
    ServiceEntry,
    SupplierQuotation,
    ThreeWayMatchResult,
)
from app.repositories import procurement_repository
from app.services import inventory_service, numbering_service
from app.services.financial_validation_service import assert_supplier_belongs_to_company

"""Procurement end-to-end (orden maestra §44-51, docs/PROCUREMENT.md).
Cada función numera su propio documento vía `numbering_service` (nunca
MAX()+1) y hace commit al final del caso de uso -- mismo patrón que
`posting_service`."""


def create_requisition(
    db: Session,
    *,
    company_id: uuid.UUID,
    requester_id: uuid.UUID,
    project_id: uuid.UUID | None,
    justification: str | None,
    priority: str,
    required_date,
    lines: list[dict],
    commit: bool = True,
) -> PurchaseRequisition:
    number = numbering_service.next_document_number(db, company_id=company_id, document_type_code="PR")
    requisition = procurement_repository.create_requisition(
        db,
        company_id=company_id,
        requisition_number=number,
        requester_id=requester_id,
        project_id=project_id,
        justification=justification,
        priority=priority,
        required_date=required_date,
    )
    for line in lines:
        procurement_repository.add_requisition_line(
            db,
            purchase_requisition_id=requisition.id,
            item_id=line.get("item_id"),
            description=line["description"],
            quantity=line["quantity"],
            estimated_unit_cost=line.get("estimated_unit_cost", Decimal("0")),
        )
    requisition.status = "SUBMITTED"
    if commit:
        db.commit()
        db.refresh(requisition)
    else:
        db.flush()
    return requisition


def approve_requisition(db: Session, *, requisition_id: uuid.UUID, approved_by_id: uuid.UUID, commit: bool = True) -> PurchaseRequisition:
    requisition = procurement_repository.get_requisition(db, requisition_id)
    if requisition is None:
        raise ValueError(f"PurchaseRequisition {requisition_id} no existe")
    if requisition.status != "SUBMITTED":
        raise InvalidProcurementStateError(
            f"Solo se puede aprobar una requisición SUBMITTED (estado actual: {requisition.status})"
        )
    requisition.status = "APPROVED"
    requisition.approved_by_id = approved_by_id
    if commit:
        db.commit()
        db.refresh(requisition)
    else:
        db.flush()
    return requisition


def create_rfq(
    db: Session,
    *,
    company_id: uuid.UUID,
    purchase_requisition_id: uuid.UUID | None,
    due_date,
    terms: str | None,
    supplier_ids: list[uuid.UUID],
    commit: bool = True,
) -> RequestForQuotation:
    if not supplier_ids:
        raise InvalidProcurementStateError("Una RFQ debe enviarse a al menos un supplier")
    for supplier_id in supplier_ids:
        assert_supplier_belongs_to_company(db, supplier_id=supplier_id, company_id=company_id)
    number = numbering_service.next_document_number(db, company_id=company_id, document_type_code="RFQ")
    rfq = procurement_repository.create_rfq(
        db,
        company_id=company_id,
        rfq_number=number,
        purchase_requisition_id=purchase_requisition_id,
        due_date=due_date,
        terms=terms,
        supplier_ids=supplier_ids,
    )
    if commit:
        db.commit()
        db.refresh(rfq)
    else:
        db.flush()
    return rfq


def submit_quotation(
    db: Session,
    *,
    request_for_quotation_id: uuid.UUID,
    supplier_id: uuid.UUID,
    currency_code: str,
    delivery_days: int | None,
    payment_terms: str | None,
    valid_until,
    notes: str | None,
    lines: list[dict],
    commit: bool = True,
) -> SupplierQuotation:
    rfq = procurement_repository.get_rfq(db, request_for_quotation_id)
    if rfq is None:
        raise ValueError(f"RequestForQuotation {request_for_quotation_id} no existe")
    assert_supplier_belongs_to_company(db, supplier_id=supplier_id, company_id=rfq.company_id)
    quotation = procurement_repository.create_quotation(
        db,
        request_for_quotation_id=request_for_quotation_id,
        supplier_id=supplier_id,
        currency_code=currency_code,
        delivery_days=delivery_days,
        payment_terms=payment_terms,
        valid_until=valid_until,
        notes=notes,
        lines=lines,
    )
    if commit:
        db.commit()
        db.refresh(quotation)
    else:
        db.flush()
    return quotation


def quotation_total(db: Session, quotation_id: uuid.UUID) -> Decimal:
    """Suma para Bid Comparison (orden maestra §48) -- el usuario autorizado
    decide el ganador con esta cifra, sin auto-aprobación por IA."""
    lines = procurement_repository.list_quotation_lines(db, quotation_id)
    return sum((line.quantity * line.unit_price + line.tax_amount for line in lines), Decimal("0"))


def create_purchase_order_from_quotation(
    db: Session,
    *,
    company_id: uuid.UUID,
    supplier_quotation_id: uuid.UUID,
    project_id: uuid.UUID | None,
    commit: bool = True,
) -> PurchaseOrder:
    """El usuario ya decidió el ganador (Bid Comparison manual); esto solo
    convierte la cotización seleccionada en una PO real con sus líneas."""
    quotation = procurement_repository.get_quotation(db, supplier_quotation_id)
    if quotation is None:
        raise ValueError(f"SupplierQuotation {supplier_quotation_id} no existe")
    rfq = procurement_repository.get_rfq(db, quotation.request_for_quotation_id)
    if rfq is None or rfq.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "supplier_quotation_id debe pertenecer a una RFQ de la compañía indicada"
        )
    lines = procurement_repository.list_quotation_lines(db, supplier_quotation_id)
    number = numbering_service.next_document_number(db, company_id=company_id, document_type_code="PO")
    order = procurement_repository.create_purchase_order(
        db,
        company_id=company_id,
        po_number=number,
        supplier_id=quotation.supplier_id,
        project_id=project_id,
        supplier_quotation_id=quotation.id,
        currency_code=quotation.currency_code,
        lines=[
            {
                "description": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "tax_amount": line.tax_amount,
            }
            for line in lines
        ],
    )
    quotation.status = "SELECTED"
    if commit:
        db.commit()
        db.refresh(order)
    else:
        db.flush()
    return order


def _assert_contract_coherent_with_po(
    db: Session,
    *,
    supplier_contract_id: uuid.UUID | None,
    company_id: uuid.UUID,
    supplier_id: uuid.UUID,
    project_id: uuid.UUID | None,
    currency_code: str,
) -> None:
    """ORDEN MAESTRA §19 — una PO ligada a un contrato debe coincidir en
    compañía, proveedor, proyecto y moneda con ese contrato."""
    if supplier_contract_id is None:
        return
    from app.models.supplier import SupplierContract

    contract = db.get(SupplierContract, supplier_contract_id)
    if contract is None or contract.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "supplier_contract_id no existe o pertenece a otra compañía"
        )
    if contract.status in ("CANCELLED", "TERMINATED", "REJECTED"):
        raise InvalidFinancialReferenceError(
            f"El contrato {contract.contract_number} está {contract.status}; no admite nuevas órdenes"
        )
    if contract.supplier_id != supplier_id:
        raise InvalidFinancialReferenceError("El contrato pertenece a otro proveedor")
    if contract.project_id is not None and contract.project_id != project_id:
        raise InvalidFinancialReferenceError(
            "El proyecto de la orden no coincide con el del contrato"
        )
    if contract.currency_code != currency_code:
        raise InvalidFinancialReferenceError(
            "La moneda de la orden no coincide con la del contrato"
        )


def create_purchase_order(
    db: Session,
    *,
    company_id: uuid.UUID,
    supplier_id: uuid.UUID,
    project_id: uuid.UUID | None,
    currency_code: str,
    lines: list[dict],
    supplier_contract_id: uuid.UUID | None = None,
    commit: bool = True,
) -> PurchaseOrder:
    """PO directa sin pasar por RFQ/cotización (compras menores)."""
    _assert_contract_coherent_with_po(
        db,
        supplier_contract_id=supplier_contract_id,
        company_id=company_id,
        supplier_id=supplier_id,
        project_id=project_id,
        currency_code=currency_code,
    )
    number = numbering_service.next_document_number(db, company_id=company_id, document_type_code="PO")
    order = procurement_repository.create_purchase_order(
        db,
        company_id=company_id,
        po_number=number,
        supplier_id=supplier_id,
        project_id=project_id,
        supplier_quotation_id=None,
        currency_code=currency_code,
        lines=lines,
        supplier_contract_id=supplier_contract_id,
    )
    if commit:
        db.commit()
        db.refresh(order)
    else:
        db.flush()
    return order


def approve_purchase_order(db: Session, *, purchase_order_id: uuid.UUID, commit: bool = True) -> PurchaseOrder:
    order = procurement_repository.get_purchase_order(db, purchase_order_id)
    if order is None:
        raise ValueError(f"PurchaseOrder {purchase_order_id} no existe")
    if order.status not in ("DRAFT", "APPROVAL_PENDING"):
        raise InvalidProcurementStateError(f"No se puede aprobar una PO en estado {order.status}")
    if order.project_id is not None:
        company = db.get(Company, order.company_id)
        if company is None:
            raise ValueError(f"Company {order.company_id} no existe")
        if company.functional_currency_code is None:
            raise ProcurementCurrencyMismatchError(
                f"La company {company.id} no tiene moneda funcional; no se puede aprobar una PO de proyecto"
            )
        if order.currency_code != company.functional_currency_code:
            raise ProcurementCurrencyMismatchError(
                f"La PO usa {order.currency_code}, pero la moneda funcional de la company es "
                f"{company.functional_currency_code}; no existe una política FX autoritativa"
            )
    order.status = "APPROVED"
    if commit:
        db.commit()
        db.refresh(order)
    else:
        db.flush()
    return order


def send_purchase_order(db: Session, *, purchase_order_id: uuid.UUID, commit: bool = True) -> PurchaseOrder:
    order = procurement_repository.get_purchase_order(db, purchase_order_id)
    if order is None:
        raise ValueError(f"PurchaseOrder {purchase_order_id} no existe")
    if order.status != "APPROVED":
        raise InvalidProcurementStateError("Solo se puede enviar una PO APPROVED")
    order.status = "SENT"
    if commit:
        db.commit()
        db.refresh(order)
    else:
        db.flush()
    return order


def _po_order_total(db: Session, po_id: uuid.UUID) -> Decimal:
    lines = procurement_repository.list_purchase_order_lines(db, po_id)
    return sum((line.quantity * line.unit_price + line.tax_amount for line in lines), Decimal("0"))


def record_goods_receipt(
    db: Session,
    *,
    company_id: uuid.UUID,
    purchase_order_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    received_by_id: uuid.UUID,
    received_at,
    quality_notes: str | None,
    lines: list[dict],
    commit: bool = True,
) -> GoodsReceipt:
    """GR: soporta recepción parcial. Actualiza `quantity_received` de cada
    PurchaseOrderLine y recalcula el status de la PO
    (PARTIALLY_RECEIVED/RECEIVED), y publica cada línea al Stock Ledger
    (RECEIPT) vía inventory_service -- nunca se toca el ledger a mano."""
    order = procurement_repository.get_purchase_order(db, purchase_order_id)
    if order is None:
        raise ValueError(f"PurchaseOrder {purchase_order_id} no existe")
    if order.status not in ("SENT", "APPROVED", "PARTIALLY_RECEIVED"):
        raise InvalidProcurementStateError(
            f"No se puede recibir mercadería para una PO en estado {order.status}"
        )

    number = numbering_service.next_document_number(db, company_id=company_id, document_type_code="GR")
    receipt = procurement_repository.create_goods_receipt(
        db,
        company_id=company_id,
        receipt_number=number,
        purchase_order_id=purchase_order_id,
        warehouse_id=warehouse_id,
        received_by_id=received_by_id,
        received_at=received_at,
        quality_notes=quality_notes,
        lines=lines,
    )

    for line in lines:
        # FOR UPDATE: dos recepciones concurrentes contra la MISMA línea de
        # PO no deben poder leer el mismo `quantity_received` desactualizado
        # y ambas pasar la validación de cantidad pendiente -- eso
        # sobre-recibiría más de lo realmente ordenado (encontrado con
        # `tests/test_concurrency.py`, mismo patrón que numbering/idempotency).
        po_line = procurement_repository.get_purchase_order_line_for_update(
            db, line["purchase_order_line_id"]
        )
        if po_line is None:
            raise ValueError(f"PurchaseOrderLine {line['purchase_order_line_id']} no existe")
        remaining = po_line.quantity - po_line.quantity_received
        if line["quantity_received"] > remaining:
            raise InvalidProcurementStateError(
                f"Se intentó recibir {line['quantity_received']} pero solo quedan {remaining} pendientes"
            )
        po_line.quantity_received = po_line.quantity_received + line["quantity_received"]
        if po_line.item_id is not None:
            inventory_service.receive_stock(
                db,
                company_id=company_id,
                item_id=po_line.item_id,
                warehouse_id=warehouse_id,
                quantity=line["quantity_received"],
                unit_cost=po_line.unit_price,
                source_type="goods_receipt",
                source_id=receipt.id,
            )

    all_lines = procurement_repository.list_purchase_order_lines(db, purchase_order_id)
    if all(pol.quantity_received >= pol.quantity for pol in all_lines):
        order.status = "RECEIVED"
    else:
        order.status = "PARTIALLY_RECEIVED"

    if commit:
        db.commit()
        db.refresh(receipt)
    else:
        db.flush()
    return receipt


def record_service_entry(
    db: Session,
    *,
    company_id: uuid.UUID,
    purchase_order_id: uuid.UUID,
    period_start,
    period_end,
    progress_percentage: Decimal,
    accepted_value: Decimal,
    approved_by_id: uuid.UUID,
    commit: bool = True,
) -> ServiceEntry:
    order = procurement_repository.get_purchase_order(db, purchase_order_id)
    if order is None:
        raise ValueError(f"PurchaseOrder {purchase_order_id} no existe")
    number = numbering_service.next_document_number(db, company_id=company_id, document_type_code="SEN")
    entry = procurement_repository.create_service_entry(
        db,
        company_id=company_id,
        entry_number=number,
        purchase_order_id=purchase_order_id,
        period_start=period_start,
        period_end=period_end,
        progress_percentage=progress_percentage,
        accepted_value=accepted_value,
        approved_by_id=approved_by_id,
    )
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def run_three_way_match(
    db: Session,
    *,
    purchase_order_id: uuid.UUID,
    supplier_invoice_id: uuid.UUID | None,
    supplier_invoice_amount: Decimal,
    supplier_invoice_quantity: Decimal,
    quantity_tolerance_pct: Decimal = Decimal("0"),
    amount_tolerance_pct: Decimal = Decimal("0"),
    commit: bool = True,
) -> ThreeWayMatchResult:
    """INV-PROC-001: compara PO vs Goods Receipt/Service Entry vs Supplier
    Invoice. Las diferencias fuera de tolerancia NUNCA se descartan
    silenciosamente -- quedan en `exceptions` con status EXCEPTION,
    persistidas siempre (nunca se omite el registro, ni cuando coincide)."""
    order = procurement_repository.get_purchase_order(db, purchase_order_id)
    if order is None:
        raise ValueError(f"PurchaseOrder {purchase_order_id} no existe")

    received_quantity = sum(
        (line.quantity_received for line in procurement_repository.list_purchase_order_lines(db, purchase_order_id)),
        Decimal("0"),
    )
    ordered_amount = _po_order_total(db, purchase_order_id)

    exceptions: list[dict] = []

    if ordered_amount == 0:
        amount_variance_pct = Decimal("100") if supplier_invoice_amount != 0 else Decimal("0")
    else:
        amount_variance_pct = abs(supplier_invoice_amount - ordered_amount) / ordered_amount * 100
    if amount_variance_pct > amount_tolerance_pct:
        exceptions.append(
            {
                "type": "AMOUNT_MISMATCH",
                "ordered_amount": str(ordered_amount),
                "invoice_amount": str(supplier_invoice_amount),
                "variance_pct": str(amount_variance_pct),
                "tolerance_pct": str(amount_tolerance_pct),
            }
        )

    if received_quantity == 0:
        quantity_variance_pct = Decimal("100") if supplier_invoice_quantity != 0 else Decimal("0")
    else:
        quantity_variance_pct = abs(supplier_invoice_quantity - received_quantity) / received_quantity * 100
    if quantity_variance_pct > quantity_tolerance_pct:
        exceptions.append(
            {
                "type": "QUANTITY_MISMATCH",
                "received_quantity": str(received_quantity),
                "invoice_quantity": str(supplier_invoice_quantity),
                "variance_pct": str(quantity_variance_pct),
                "tolerance_pct": str(quantity_tolerance_pct),
            }
        )

    result = procurement_repository.create_three_way_match_result(
        db,
        purchase_order_id=purchase_order_id,
        supplier_invoice_id=supplier_invoice_id,
        supplier_invoice_amount=supplier_invoice_amount,
        supplier_invoice_quantity=supplier_invoice_quantity,
        received_quantity=received_quantity,
        ordered_amount=ordered_amount,
        quantity_tolerance_pct=quantity_tolerance_pct,
        amount_tolerance_pct=amount_tolerance_pct,
        status="EXCEPTION" if exceptions else "MATCHED",
        exceptions=exceptions,
    )
    if commit:
        db.commit()
        db.refresh(result)
    else:
        db.flush()
    return result
