import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.procurement import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseRequisitionLine,
    RequestForQuotation,
    RfqSupplier,
    ServiceEntry,
    SupplierQuotation,
    SupplierQuotationLine,
    ThreeWayMatchResult,
)


def create_requisition(
    db: Session,
    *,
    company_id: uuid.UUID,
    requisition_number: str,
    requester_id: uuid.UUID,
    project_id: uuid.UUID | None,
    justification: str | None,
    priority: str,
    required_date,
) -> PurchaseRequisition:
    requisition = PurchaseRequisition(
        company_id=company_id,
        requisition_number=requisition_number,
        requester_id=requester_id,
        project_id=project_id,
        justification=justification,
        priority=priority,
        required_date=required_date,
    )
    db.add(requisition)
    db.flush()
    return requisition


def add_requisition_line(
    db: Session,
    *,
    purchase_requisition_id: uuid.UUID,
    item_id: uuid.UUID | None,
    description: str,
    quantity: Decimal,
    estimated_unit_cost: Decimal,
) -> PurchaseRequisitionLine:
    line = PurchaseRequisitionLine(
        purchase_requisition_id=purchase_requisition_id,
        item_id=item_id,
        description=description,
        quantity=quantity,
        estimated_unit_cost=estimated_unit_cost,
    )
    db.add(line)
    db.flush()
    return line


def list_requisitions(db: Session, *, company_id: uuid.UUID) -> list[PurchaseRequisition]:
    stmt = (
        select(PurchaseRequisition)
        .where(PurchaseRequisition.company_id == company_id)
        .order_by(PurchaseRequisition.requisition_number)
    )
    return list(db.execute(stmt).scalars())


def get_requisition(db: Session, requisition_id: uuid.UUID) -> PurchaseRequisition | None:
    return db.get(PurchaseRequisition, requisition_id)


def list_requisition_lines(db: Session, requisition_id: uuid.UUID) -> list[PurchaseRequisitionLine]:
    stmt = select(PurchaseRequisitionLine).where(
        PurchaseRequisitionLine.purchase_requisition_id == requisition_id
    )
    return list(db.execute(stmt).scalars())


def create_rfq(
    db: Session,
    *,
    company_id: uuid.UUID,
    rfq_number: str,
    purchase_requisition_id: uuid.UUID | None,
    due_date,
    terms: str | None,
    supplier_ids: list[uuid.UUID],
) -> RequestForQuotation:
    rfq = RequestForQuotation(
        company_id=company_id,
        rfq_number=rfq_number,
        purchase_requisition_id=purchase_requisition_id,
        due_date=due_date,
        terms=terms,
        status="SENT",
    )
    db.add(rfq)
    db.flush()
    for supplier_id in supplier_ids:
        db.add(RfqSupplier(request_for_quotation_id=rfq.id, supplier_id=supplier_id))
    db.flush()
    return rfq


def get_rfq(db: Session, rfq_id: uuid.UUID) -> RequestForQuotation | None:
    return db.get(RequestForQuotation, rfq_id)


def create_quotation(
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
) -> SupplierQuotation:
    quotation = SupplierQuotation(
        request_for_quotation_id=request_for_quotation_id,
        supplier_id=supplier_id,
        currency_code=currency_code,
        delivery_days=delivery_days,
        payment_terms=payment_terms,
        valid_until=valid_until,
        notes=notes,
    )
    db.add(quotation)
    db.flush()
    for line in lines:
        db.add(
            SupplierQuotationLine(
                supplier_quotation_id=quotation.id,
                purchase_requisition_line_id=line.get("purchase_requisition_line_id"),
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                tax_amount=line.get("tax_amount", Decimal("0")),
            )
        )
    db.flush()
    return quotation


def list_quotations_for_rfq(db: Session, rfq_id: uuid.UUID) -> list[SupplierQuotation]:
    stmt = select(SupplierQuotation).where(SupplierQuotation.request_for_quotation_id == rfq_id)
    return list(db.execute(stmt).scalars())


def list_quotation_lines(db: Session, quotation_id: uuid.UUID) -> list[SupplierQuotationLine]:
    stmt = select(SupplierQuotationLine).where(SupplierQuotationLine.supplier_quotation_id == quotation_id)
    return list(db.execute(stmt).scalars())


def get_quotation(db: Session, quotation_id: uuid.UUID) -> SupplierQuotation | None:
    return db.get(SupplierQuotation, quotation_id)


def create_purchase_order(
    db: Session,
    *,
    company_id: uuid.UUID,
    po_number: str,
    supplier_id: uuid.UUID,
    project_id: uuid.UUID | None,
    supplier_quotation_id: uuid.UUID | None,
    currency_code: str,
    lines: list[dict],
) -> PurchaseOrder:
    order = PurchaseOrder(
        company_id=company_id,
        po_number=po_number,
        supplier_id=supplier_id,
        project_id=project_id,
        supplier_quotation_id=supplier_quotation_id,
        currency_code=currency_code,
        status="DRAFT",
    )
    db.add(order)
    db.flush()
    for line in lines:
        db.add(
            PurchaseOrderLine(
                purchase_order_id=order.id,
                item_id=line.get("item_id"),
                description=line["description"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                tax_amount=line.get("tax_amount", Decimal("0")),
            )
        )
    db.flush()
    return order


def get_purchase_order(db: Session, po_id: uuid.UUID) -> PurchaseOrder | None:
    return db.get(PurchaseOrder, po_id)


def list_purchase_orders(db: Session, *, company_id: uuid.UUID) -> list[PurchaseOrder]:
    stmt = select(PurchaseOrder).where(PurchaseOrder.company_id == company_id).order_by(PurchaseOrder.po_number)
    return list(db.execute(stmt).scalars())


def list_purchase_order_lines(db: Session, po_id: uuid.UUID) -> list[PurchaseOrderLine]:
    stmt = select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id == po_id)
    return list(db.execute(stmt).scalars())


def project_commitments_by_project(db: Session, *, company_id: uuid.UUID) -> dict[uuid.UUID, Decimal]:
    """Documentary commitments for Budget/Project Control.

    A commitment exists only after purchase-order approval; receipts and
    warehouse movements never create it. The result is deliberately keyed by
    project so Budget can map the project to its WBS without a dependency on
    this supply-chain service.
    """
    commitment_statuses = ("APPROVED", "SENT", "PARTIALLY_RECEIVED", "RECEIVED")
    total = func.sum(PurchaseOrderLine.quantity * PurchaseOrderLine.unit_price + PurchaseOrderLine.tax_amount)
    stmt = (
        select(PurchaseOrder.project_id, total.label("total"))
        .join(PurchaseOrderLine, PurchaseOrderLine.purchase_order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.project_id.is_not(None),
            PurchaseOrder.status.in_(commitment_statuses),
        )
        .group_by(PurchaseOrder.project_id)
    )
    return {project_id: Decimal(total) for project_id, total in db.execute(stmt)}


def get_purchase_order_line(db: Session, line_id: uuid.UUID) -> PurchaseOrderLine | None:
    return db.get(PurchaseOrderLine, line_id)


def create_goods_receipt(
    db: Session,
    *,
    company_id: uuid.UUID,
    receipt_number: str,
    purchase_order_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    received_by_id: uuid.UUID,
    received_at,
    quality_notes: str | None,
    lines: list[dict],
) -> GoodsReceipt:
    receipt = GoodsReceipt(
        company_id=company_id,
        receipt_number=receipt_number,
        purchase_order_id=purchase_order_id,
        warehouse_id=warehouse_id,
        received_by_id=received_by_id,
        received_at=received_at,
        quality_notes=quality_notes,
    )
    db.add(receipt)
    db.flush()
    for line in lines:
        db.add(
            GoodsReceiptLine(
                goods_receipt_id=receipt.id,
                purchase_order_line_id=line["purchase_order_line_id"],
                quantity_received=line["quantity_received"],
            )
        )
    db.flush()
    return receipt


def list_goods_receipts_for_po(db: Session, po_id: uuid.UUID) -> list[GoodsReceipt]:
    stmt = select(GoodsReceipt).where(GoodsReceipt.purchase_order_id == po_id)
    return list(db.execute(stmt).scalars())


def list_goods_receipt_lines(db: Session, receipt_id: uuid.UUID) -> list[GoodsReceiptLine]:
    stmt = select(GoodsReceiptLine).where(GoodsReceiptLine.goods_receipt_id == receipt_id)
    return list(db.execute(stmt).scalars())


def create_service_entry(
    db: Session,
    *,
    company_id: uuid.UUID,
    entry_number: str,
    purchase_order_id: uuid.UUID,
    period_start,
    period_end,
    progress_percentage: Decimal,
    accepted_value: Decimal,
    approved_by_id: uuid.UUID,
) -> ServiceEntry:
    entry = ServiceEntry(
        company_id=company_id,
        entry_number=entry_number,
        purchase_order_id=purchase_order_id,
        period_start=period_start,
        period_end=period_end,
        progress_percentage=progress_percentage,
        accepted_value=accepted_value,
        approved_by_id=approved_by_id,
    )
    db.add(entry)
    db.flush()
    return entry


def list_service_entries_for_po(db: Session, po_id: uuid.UUID) -> list[ServiceEntry]:
    stmt = select(ServiceEntry).where(ServiceEntry.purchase_order_id == po_id)
    return list(db.execute(stmt).scalars())


def create_three_way_match_result(
    db: Session,
    *,
    purchase_order_id: uuid.UUID,
    supplier_invoice_id: uuid.UUID | None,
    supplier_invoice_amount: Decimal,
    supplier_invoice_quantity: Decimal,
    received_quantity: Decimal,
    ordered_amount: Decimal,
    quantity_tolerance_pct: Decimal,
    amount_tolerance_pct: Decimal,
    status: str,
    exceptions: list,
) -> ThreeWayMatchResult:
    result = ThreeWayMatchResult(
        purchase_order_id=purchase_order_id,
        supplier_invoice_id=supplier_invoice_id,
        supplier_invoice_amount=supplier_invoice_amount,
        supplier_invoice_quantity=supplier_invoice_quantity,
        received_quantity=received_quantity,
        ordered_amount=ordered_amount,
        quantity_tolerance_pct=quantity_tolerance_pct,
        amount_tolerance_pct=amount_tolerance_pct,
        status=status,
        exceptions=exceptions,
    )
    db.add(result)
    db.flush()
    return result
