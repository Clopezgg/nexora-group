import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import procurement_repository
from app.schemas.procurement import (
    GoodsReceiptCreateRequest,
    GoodsReceiptResponse,
    PurchaseOrderCreateRequest,
    PurchaseOrderFromQuotationRequest,
    PurchaseOrderLineResponse,
    PurchaseOrderResponse,
    QuotationCreateRequest,
    QuotationLineResponse,
    QuotationResponse,
    RequisitionCreateRequest,
    RequisitionLineResponse,
    RequisitionResponse,
    RfqCreateRequest,
    RfqResponse,
    ServiceEntryCreateRequest,
    ServiceEntryResponse,
    ThreeWayMatchRequest,
    ThreeWayMatchResponse,
)
from app.services import procurement_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _requisition_response(db: Session, requisition) -> RequisitionResponse:
    lines = procurement_repository.list_requisition_lines(db, requisition.id)
    return RequisitionResponse(
        id=requisition.id,
        company_id=requisition.company_id,
        requisition_number=requisition.requisition_number,
        project_id=requisition.project_id,
        justification=requisition.justification,
        priority=requisition.priority,
        required_date=requisition.required_date,
        status=requisition.status,
        lines=[RequisitionLineResponse.model_validate(line, from_attributes=True) for line in lines],
    )


@router.get("/requisitions", response_model=list[RequisitionResponse])
def list_requisitions(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.requisition", "read")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.requisition", action="read", company_id=company_id
    )
    requisitions = procurement_repository.list_requisitions(db, company_id=company_id)
    return [_requisition_response(db, r) for r in requisitions]


@router.post("/requisitions", response_model=RequisitionResponse, status_code=201)
def create_requisition(
    payload: RequisitionCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.requisition", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.requisition", action="create", company_id=payload.company_id
    )
    requisition = procurement_service.create_requisition(
        db,
        company_id=payload.company_id,
        requester_id=user.id,
        project_id=payload.project_id,
        justification=payload.justification,
        priority=payload.priority,
        required_date=payload.required_date,
        lines=[line.model_dump() for line in payload.lines],
    )
    return _requisition_response(db, requisition)


@router.post("/requisitions/{requisition_id}/approve", response_model=RequisitionResponse)
def approve_requisition(
    requisition_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.requisition", "approve")),
):
    requisition = procurement_service.approve_requisition(db, requisition_id=requisition_id, approved_by_id=user.id)
    return _requisition_response(db, requisition)


@router.post("/rfqs", response_model=RfqResponse, status_code=201)
def create_rfq(
    payload: RfqCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.rfq", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.rfq", action="create", company_id=payload.company_id
    )
    rfq = procurement_service.create_rfq(
        db,
        company_id=payload.company_id,
        purchase_requisition_id=payload.purchase_requisition_id,
        due_date=payload.due_date,
        terms=payload.terms,
        supplier_ids=payload.supplier_ids,
    )
    return RfqResponse.model_validate(rfq, from_attributes=True)


def _quotation_response(db: Session, quotation) -> QuotationResponse:
    lines = procurement_repository.list_quotation_lines(db, quotation.id)
    total = procurement_service.quotation_total(db, quotation.id)
    return QuotationResponse(
        id=quotation.id,
        request_for_quotation_id=quotation.request_for_quotation_id,
        supplier_id=quotation.supplier_id,
        currency_code=quotation.currency_code,
        status=quotation.status,
        total=total,
        lines=[QuotationLineResponse.model_validate(line, from_attributes=True) for line in lines],
    )


@router.post("/rfqs/{rfq_id}/quotations", response_model=QuotationResponse, status_code=201)
def submit_quotation(
    rfq_id: uuid.UUID,
    payload: QuotationCreateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.quotation", "create")),
):
    quotation = procurement_service.submit_quotation(
        db,
        request_for_quotation_id=rfq_id,
        supplier_id=payload.supplier_id,
        currency_code=payload.currency_code,
        delivery_days=payload.delivery_days,
        payment_terms=payload.payment_terms,
        valid_until=payload.valid_until,
        notes=payload.notes,
        lines=[line.model_dump() for line in payload.lines],
    )
    return _quotation_response(db, quotation)


@router.get("/rfqs/{rfq_id}/quotations", response_model=list[QuotationResponse])
def list_quotations(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.quotation", "read")),
):
    quotations = procurement_repository.list_quotations_for_rfq(db, rfq_id)
    return [_quotation_response(db, q) for q in quotations]


def _purchase_order_response(db: Session, order) -> PurchaseOrderResponse:
    lines = procurement_repository.list_purchase_order_lines(db, order.id)
    return PurchaseOrderResponse(
        id=order.id,
        company_id=order.company_id,
        po_number=order.po_number,
        supplier_id=order.supplier_id,
        project_id=order.project_id,
        currency_code=order.currency_code,
        status=order.status,
        lines=[PurchaseOrderLineResponse.model_validate(line, from_attributes=True) for line in lines],
    )


@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse])
def list_purchase_orders(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.purchase_order", "read")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.purchase_order", action="read", company_id=company_id
    )
    orders = procurement_repository.list_purchase_orders(db, company_id=company_id)
    return [_purchase_order_response(db, o) for o in orders]


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(
    po_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.purchase_order", "read")),
):
    order = procurement_repository.get_purchase_order(db, po_id)
    if order is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    return _purchase_order_response(db, order)


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.purchase_order", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.purchase_order", action="create", company_id=payload.company_id
    )
    order = procurement_service.create_purchase_order(
        db,
        company_id=payload.company_id,
        supplier_id=payload.supplier_id,
        project_id=payload.project_id,
        currency_code=payload.currency_code,
        lines=[line.model_dump() for line in payload.lines],
    )
    return _purchase_order_response(db, order)


@router.post("/purchase-orders/from-quotation", response_model=PurchaseOrderResponse, status_code=201)
def create_purchase_order_from_quotation(
    payload: PurchaseOrderFromQuotationRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.purchase_order", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="procurement.purchase_order", action="create", company_id=payload.company_id
    )
    order = procurement_service.create_purchase_order_from_quotation(
        db,
        company_id=payload.company_id,
        supplier_quotation_id=payload.supplier_quotation_id,
        project_id=payload.project_id,
    )
    return _purchase_order_response(db, order)


@router.post("/purchase-orders/{po_id}/approve", response_model=PurchaseOrderResponse)
def approve_purchase_order(
    po_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.purchase_order", "approve")),
):
    order = procurement_service.approve_purchase_order(db, purchase_order_id=po_id)
    return _purchase_order_response(db, order)


@router.post("/purchase-orders/{po_id}/send", response_model=PurchaseOrderResponse)
def send_purchase_order(
    po_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.purchase_order", "approve")),
):
    order = procurement_service.send_purchase_order(db, purchase_order_id=po_id)
    return _purchase_order_response(db, order)


@router.get("/goods-receipts", response_model=list[GoodsReceiptResponse])
def list_goods_receipts(
    purchase_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.goods_receipt", "read")),
):
    receipts = procurement_repository.list_goods_receipts_for_po(db, purchase_order_id)
    return [GoodsReceiptResponse.model_validate(r, from_attributes=True) for r in receipts]


@router.post("/goods-receipts", response_model=GoodsReceiptResponse, status_code=201)
def create_goods_receipt(
    payload: GoodsReceiptCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.goods_receipt", "create")),
):
    order = procurement_repository.get_purchase_order(db, payload.purchase_order_id)
    if order is not None:
        assert_company_access(
            db, user_id=user.id, resource="procurement.goods_receipt", action="create", company_id=order.company_id
        )
    receipt = procurement_service.record_goods_receipt(
        db,
        company_id=order.company_id,
        purchase_order_id=payload.purchase_order_id,
        warehouse_id=payload.warehouse_id,
        received_by_id=user.id,
        received_at=payload.received_at,
        quality_notes=payload.quality_notes,
        lines=[line.model_dump() for line in payload.lines],
    )
    return GoodsReceiptResponse.model_validate(receipt, from_attributes=True)


@router.post("/service-entries", response_model=ServiceEntryResponse, status_code=201)
def create_service_entry(
    payload: ServiceEntryCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("procurement.service_entry", "create")),
):
    order = procurement_repository.get_purchase_order(db, payload.purchase_order_id)
    if order is not None:
        assert_company_access(
            db, user_id=user.id, resource="procurement.service_entry", action="create", company_id=order.company_id
        )
    entry = procurement_service.record_service_entry(
        db,
        company_id=order.company_id,
        purchase_order_id=payload.purchase_order_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        progress_percentage=payload.progress_percentage,
        accepted_value=payload.accepted_value,
        approved_by_id=user.id,
    )
    return ServiceEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/three-way-match", response_model=ThreeWayMatchResponse, status_code=201)
def run_three_way_match(
    payload: ThreeWayMatchRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("procurement.three_way_match", "create")),
):
    result = procurement_service.run_three_way_match(
        db,
        purchase_order_id=payload.purchase_order_id,
        supplier_invoice_id=payload.supplier_invoice_id,
        supplier_invoice_amount=payload.supplier_invoice_amount,
        supplier_invoice_quantity=payload.supplier_invoice_quantity,
        quantity_tolerance_pct=payload.quantity_tolerance_pct,
        amount_tolerance_pct=payload.amount_tolerance_pct,
    )
    return ThreeWayMatchResponse.model_validate(result, from_attributes=True)
