import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import (
    InvalidFinancialReferenceError,
    InvalidProcurementStateError,
    ProcurementCurrencyMismatchError,
)
from app.models.ap import SupplierInvoice
from app.models.company import Company
from app.models.evidence import Evidence
from app.models.item import Item
from app.models.procurement import (
    GoodsReceipt,
    PurchaseOrder,
    PurchaseRequisition,
    RequestForQuotation,
    ServiceEntry,
    SupplierQuotation,
    ThreeWayMatchResult,
)
from app.models.warehouse import Warehouse
from app.repositories import procurement_repository
from app.services import inventory_service, numbering_service
from app.services.financial_validation_service import (
    assert_project_belongs_to_company,
    assert_supplier_belongs_to_company,
)

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
    if db.get(Company, company_id) is None:
        raise InvalidFinancialReferenceError("La compañía de la requisición no existe")
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    for line in lines:
        item_id = line.get("item_id")
        if item_id is not None:
            item = db.get(Item, item_id)
            if item is None or item.company_id != company_id:
                raise InvalidFinancialReferenceError(
                    "Cada item de la requisición debe pertenecer a su compañía"
                )
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
    if len(set(supplier_ids)) != len(supplier_ids):
        raise InvalidFinancialReferenceError("Una RFQ no puede invitar dos veces al mismo proveedor")
    if purchase_requisition_id is not None:
        requisition = procurement_repository.get_requisition(db, purchase_requisition_id)
        if requisition is None or requisition.company_id != company_id:
            raise InvalidFinancialReferenceError(
                "La requisición debe pertenecer a la compañía de la RFQ"
            )
        if requisition.status != "APPROVED":
            raise InvalidProcurementStateError("Solo una requisición aprobada puede originar una RFQ")
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
    if not procurement_repository.supplier_is_invited(
        db, rfq_id=request_for_quotation_id, supplier_id=supplier_id
    ):
        raise InvalidFinancialReferenceError("El proveedor no fue invitado a esta RFQ")
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
    quotation = db.execute(
        select(SupplierQuotation)
        .where(SupplierQuotation.id == supplier_quotation_id)
        .with_for_update()
    ).scalar_one_or_none()
    if quotation is None:
        raise ValueError(f"SupplierQuotation {supplier_quotation_id} no existe")
    rfq = procurement_repository.get_rfq(db, quotation.request_for_quotation_id)
    if rfq is None or rfq.company_id != company_id:
        raise InvalidFinancialReferenceError(
            "supplier_quotation_id debe pertenecer a una RFQ de la compañía indicada"
        )
    if quotation.status != "RECEIVED":
        raise InvalidProcurementStateError("La cotización ya fue decidida y no puede reutilizarse")
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
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
        fulfillment_type="GOODS",
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
    fulfillment_type: str = "GOODS",
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
    fulfillment_type: str = "GOODS",
    supplier_contract_id: uuid.UUID | None = None,
    commit: bool = True,
) -> PurchaseOrder:
    """PO directa sin pasar por RFQ/cotización (compras menores)."""
    if fulfillment_type not in {"GOODS", "SERVICE"}:
        raise InvalidFinancialReferenceError("El tipo de cumplimiento de la orden es inválido")
    if db.get(Company, company_id) is None:
        raise InvalidFinancialReferenceError("La compañía de la orden no existe")
    assert_supplier_belongs_to_company(db, supplier_id=supplier_id, company_id=company_id)
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    for line in lines:
        item_id = line.get("item_id")
        if item_id is not None:
            item = db.get(Item, item_id)
            if item is None or item.company_id != company_id or not item.active:
                raise InvalidFinancialReferenceError(
                    "Cada item de la orden debe estar activo y pertenecer a su compañía"
                )
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
        fulfillment_type=fulfillment_type,
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
    if order.company_id != company_id:
        raise InvalidFinancialReferenceError("La recepción y la orden pertenecen a compañías distintas")
    if order.status not in ("SENT", "APPROVED", "PARTIALLY_RECEIVED"):
        raise InvalidProcurementStateError(
            f"No se puede recibir mercadería para una PO en estado {order.status}"
        )
    if order.fulfillment_type != "GOODS":
        raise InvalidFinancialReferenceError(
            "Una orden de servicios se acepta mediante entrada de servicio, no recepción física"
        )
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or warehouse.company_id != company_id or warehouse.status != "ACTIVE":
        raise InvalidFinancialReferenceError(
            "El almacén debe estar activo y pertenecer a la compañía de la orden"
        )
    if not lines:
        raise InvalidFinancialReferenceError("La recepción debe contener al menos una línea")

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
        if po_line.purchase_order_id != order.id:
            raise InvalidFinancialReferenceError("La línea recibida no pertenece a esta orden")
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
                commit=False,
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
    evidence_id: uuid.UUID | None = None,
    commit: bool = True,
) -> ServiceEntry:
    order = db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id).with_for_update()
    ).scalar_one_or_none()
    if order is None:
        raise ValueError(f"PurchaseOrder {purchase_order_id} no existe")
    if order.company_id != company_id:
        raise InvalidFinancialReferenceError("La entrada y la orden pertenecen a compañías distintas")
    if order.status not in ("SENT", "APPROVED", "PARTIALLY_RECEIVED"):
        raise InvalidFinancialReferenceError(
            f"No se puede aceptar servicio para una PO en estado {order.status}"
        )
    if order.fulfillment_type != "SERVICE":
        raise InvalidFinancialReferenceError(
            "Una orden de bienes se recibe físicamente, no mediante entrada de servicio"
        )
    if period_start > period_end:
        raise InvalidFinancialReferenceError("El período de servicio es inválido")

    entries = procurement_repository.list_service_entries_for_po(db, purchase_order_id)
    if any(period_start <= entry.period_end and period_end >= entry.period_start for entry in entries):
        raise InvalidFinancialReferenceError("El período se superpone con otra entrada de servicio")
    total_progress = sum((entry.progress_percentage for entry in entries), Decimal("0"))
    total_accepted = sum((entry.accepted_value for entry in entries), Decimal("0"))
    if total_progress + progress_percentage > Decimal("100"):
        raise InvalidFinancialReferenceError("El avance acumulado excede 100%")
    order_total = _po_order_total(db, purchase_order_id)
    if total_accepted + accepted_value > order_total:
        raise InvalidFinancialReferenceError("El valor aceptado acumulado excede el valor de la orden")
    if evidence_id is not None:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            raise InvalidFinancialReferenceError("La evidencia de la entrada no existe")
        if evidence.company_id != company_id:
            raise InvalidFinancialReferenceError("La evidencia pertenece a otra compañía")
        if evidence.entity_type not in {"PURCHASE_ORDER", "PO"} or evidence.entity_id != order.id:
            raise InvalidFinancialReferenceError("La evidencia no está vinculada a esta orden")
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
        evidence_id=evidence_id,
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
    supplier_invoice_id: uuid.UUID,
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
    invoice = db.get(SupplierInvoice, supplier_invoice_id)
    if invoice is None:
        raise InvalidFinancialReferenceError("La factura de proveedor no existe")
    if invoice.company_id != order.company_id:
        raise InvalidFinancialReferenceError("La factura y la orden pertenecen a compañías distintas")
    if invoice.supplier_id != order.supplier_id:
        raise InvalidFinancialReferenceError("La factura y la orden pertenecen a proveedores distintos")
    if invoice.project_id != order.project_id:
        raise InvalidFinancialReferenceError("La factura y la orden pertenecen a proyectos distintos")
    if invoice.currency_code != order.currency_code:
        raise InvalidFinancialReferenceError("La moneda de la factura no coincide con la orden")
    if invoice.purchase_order_id != order.id:
        raise InvalidFinancialReferenceError("La factura no corresponde a esta orden de compra")
    existing = db.query(ThreeWayMatchResult.id).filter(
        ThreeWayMatchResult.supplier_invoice_id == invoice.id,
        ThreeWayMatchResult.match_kind == "FINANCIAL",
    ).first()
    if existing is not None:
        raise InvalidFinancialReferenceError("La factura ya tiene un three-way match financiero")

    supplier_invoice_amount = invoice.amount + invoice.tax_amount

    received_quantity = sum(
        (line.quantity_received for line in procurement_repository.list_purchase_order_lines(db, purchase_order_id)),
        Decimal("0"),
    )
    ordered_amount = _po_order_total(db, purchase_order_id)
    service_entries = procurement_repository.list_service_entries_for_po(db, purchase_order_id)
    accepted_service_amount = sum((entry.accepted_value for entry in service_entries), Decimal("0"))
    if received_quantity > 0:
        receipt_basis = "GOODS_RECEIPT"
        accepted_amount = ordered_amount
    elif accepted_service_amount > 0:
        receipt_basis = "SERVICE_ENTRY"
        accepted_amount = accepted_service_amount
    else:
        raise InvalidFinancialReferenceError(
            "La orden no tiene recepción física ni entrada de servicio aceptada"
        )

    exceptions: list[dict] = []

    match_amount = accepted_amount
    if match_amount == 0:
        amount_variance_pct = Decimal("100") if supplier_invoice_amount != 0 else Decimal("0")
    else:
        amount_variance_pct = abs(supplier_invoice_amount - match_amount) / match_amount * 100
    if amount_variance_pct > amount_tolerance_pct:
        exceptions.append(
            {
                "type": "AMOUNT_MISMATCH",
                "accepted_amount": str(match_amount),
                "invoice_amount": str(supplier_invoice_amount),
                "variance_pct": str(amount_variance_pct),
                "tolerance_pct": str(amount_tolerance_pct),
            }
        )

    if receipt_basis == "SERVICE_ENTRY":
        quantity_variance_pct = Decimal("0")
    elif received_quantity == 0:
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
        receipt_basis=receipt_basis,
        accepted_amount=accepted_amount,
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


def override_three_way_match_exception(
    db: Session,
    *,
    result_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: str,
    evidence_id: uuid.UUID | None = None,
    commit: bool = True,
) -> ThreeWayMatchResult:
    result = db.query(ThreeWayMatchResult).filter(
        ThreeWayMatchResult.id == result_id
    ).with_for_update().one_or_none()
    if result is None:
        raise InvalidFinancialReferenceError("Three-way match no existe")
    if result.match_kind != "FINANCIAL" or result.status != "EXCEPTION":
        raise InvalidFinancialReferenceError("Solo una excepción financiera puede autorizarse")
    if result.overridden_at is not None:
        raise InvalidFinancialReferenceError("La excepción ya fue autorizada")
    normalized_reason = reason.strip()
    if len(normalized_reason) < 10:
        raise InvalidFinancialReferenceError("El motivo de autorización requiere al menos 10 caracteres")
    if evidence_id is not None:
        evidence = db.get(Evidence, evidence_id)
        order = db.get(PurchaseOrder, result.purchase_order_id)
        if evidence is None:
            raise InvalidFinancialReferenceError("La evidencia de la excepción no existe")
        if order is None or evidence.company_id != order.company_id:
            raise InvalidFinancialReferenceError("La evidencia pertenece a otra compañía")
        if evidence.entity_type != "THREE_WAY_MATCH" or evidence.entity_id != result.id:
            raise InvalidFinancialReferenceError("La evidencia no está vinculada a este three-way match")
        if evidence.category != "TWM_EXCEPTION_OVERRIDE":
            raise InvalidFinancialReferenceError("La evidencia no documenta una excepción de three-way match")
    result.override_reason = normalized_reason
    result.overridden_by_user_id = actor_user_id
    result.overridden_at = datetime.now(timezone.utc)
    result.override_evidence_id = evidence_id
    if commit:
        db.commit()
        db.refresh(result)
    else:
        db.flush()
    return result
