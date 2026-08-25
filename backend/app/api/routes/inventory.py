import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.domain.errors import NotAuthorizedError
from app.models.project import Project
from app.repositories import inventory_repository
from app.schemas.inventory import (
    ItemCreateRequest,
    ItemResponse,
    PhysicalCountCreateRequest,
    PhysicalCountResponse,
    StockIssueToProjectRequest,
    StockLedgerEntryResponse,
    StockPositionResponse,
    StockReceiveRequest,
    StockReturnToSupplierRequest,
    StockTransferRequest,
    WarehouseCreateRequest,
    WarehouseResponse,
)
from app.services import inventory_service
from app.services.financial_validation_service import assert_supplier_belongs_to_company
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _assert_stock_resources_belong_to_company(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_ids: tuple[uuid.UUID, ...],
    project_id: uuid.UUID | None = None,
) -> None:
    item = inventory_repository.get_item(db, item_id)
    if item is None or item.company_id != company_id:
        raise NotAuthorizedError("El ítem no pertenece a la compañía de la operación")
    for warehouse_id in warehouse_ids:
        warehouse = inventory_repository.get_warehouse(db, warehouse_id)
        if warehouse is None or warehouse.company_id != company_id:
            raise NotAuthorizedError("El almacén no pertenece a la compañía de la operación")
    if project_id is not None:
        project = db.get(Project, project_id)
        if project is None or project.company_id != company_id:
            raise NotAuthorizedError("El proyecto no pertenece a la compañía de la operación")


@router.get("/items", response_model=list[ItemResponse])
def list_items(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.item", "read")),
):
    assert_company_access(db, user_id=user.id, resource="inventory.item", action="read", company_id=company_id)
    items = inventory_repository.list_items(db, company_id=company_id)
    return [ItemResponse.model_validate(item, from_attributes=True) for item in items]


@router.post("/items", response_model=ItemResponse, status_code=201)
def create_item(
    payload: ItemCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.item", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.item", action="create", company_id=payload.company_id
    )
    item = inventory_repository.create_item(
        db,
        company_id=payload.company_id,
        sku=payload.sku,
        name=payload.name,
        item_type=payload.item_type,
        category=payload.category,
        uom=payload.uom,
        description=payload.description,
        track_inventory=payload.track_inventory,
    )
    db.commit()
    db.refresh(item)
    return ItemResponse.model_validate(item, from_attributes=True)


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.warehouse", "read")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.warehouse", action="read", company_id=company_id
    )
    warehouses = inventory_repository.list_warehouses(db, company_id=company_id)
    return [WarehouseResponse.model_validate(w, from_attributes=True) for w in warehouses]


@router.post("/warehouses", response_model=WarehouseResponse, status_code=201)
def create_warehouse(
    payload: WarehouseCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.warehouse", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.warehouse", action="create", company_id=payload.company_id
    )
    warehouse = inventory_repository.create_warehouse(
        db,
        company_id=payload.company_id,
        project_id=payload.project_id,
        code=payload.code,
        name=payload.name,
    )
    db.commit()
    db.refresh(warehouse)
    return WarehouseResponse.model_validate(warehouse, from_attributes=True)


@router.get("/stock/position", response_model=StockPositionResponse)
def get_stock_position(
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "read")),
):
    item = inventory_repository.get_item(db, item_id)
    if item is None:
        raise NotAuthorizedError("El ítem no existe o no pertenece a una compañía accesible")
    _assert_stock_resources_belong_to_company(
        db,
        company_id=item.company_id,
        item_id=item_id,
        warehouse_ids=(warehouse_id,),
    )
    assert_company_access(
        db, user_id=user.id, resource="inventory.stock", action="read", company_id=item.company_id
    )
    last = inventory_repository.get_last_ledger_entry(
        db, company_id=item.company_id, item_id=item_id, warehouse_id=warehouse_id
    )
    if last is None:
        return StockPositionResponse(
            item_id=item_id, warehouse_id=warehouse_id, quantity_on_hand=0, average_cost=0
        )
    return StockPositionResponse(
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity_on_hand=last.resulting_qty_on_hand,
        average_cost=last.resulting_avg_cost,
    )


@router.post("/stock/receive", response_model=StockLedgerEntryResponse, status_code=201)
def receive_stock(
    payload: StockReceiveRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.stock", action="move", company_id=payload.company_id
    )
    _assert_stock_resources_belong_to_company(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_ids=(payload.warehouse_id,),
    )
    entry = inventory_service.receive_stock(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
    )
    return StockLedgerEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/stock/issue-to-project", response_model=StockLedgerEntryResponse, status_code=201)
def issue_to_project(
    payload: StockIssueToProjectRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.stock", action="move", company_id=payload.company_id
    )
    _assert_stock_resources_belong_to_company(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_ids=(payload.warehouse_id,),
        project_id=payload.project_id,
    )
    entry = inventory_service.issue_to_project(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        project_id=payload.project_id,
        quantity=payload.quantity,
    )
    return StockLedgerEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/stock/transfer", response_model=list[StockLedgerEntryResponse], status_code=201)
def transfer_stock(
    payload: StockTransferRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.stock", action="move", company_id=payload.company_id
    )
    _assert_stock_resources_belong_to_company(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_ids=(payload.from_warehouse_id, payload.to_warehouse_id),
    )
    outgoing, incoming = inventory_service.transfer_stock(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        from_warehouse_id=payload.from_warehouse_id,
        to_warehouse_id=payload.to_warehouse_id,
        quantity=payload.quantity,
    )
    return [
        StockLedgerEntryResponse.model_validate(outgoing, from_attributes=True),
        StockLedgerEntryResponse.model_validate(incoming, from_attributes=True),
    ]


@router.post("/stock/return-to-supplier", response_model=StockLedgerEntryResponse, status_code=201)
def return_to_supplier(
    payload: StockReturnToSupplierRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.stock", action="move", company_id=payload.company_id
    )
    _assert_stock_resources_belong_to_company(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_ids=(payload.warehouse_id,),
    )
    assert_supplier_belongs_to_company(
        db, supplier_id=payload.supplier_id, company_id=payload.company_id
    )
    entry = inventory_service.return_to_supplier(
        db,
        company_id=payload.company_id,
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        supplier_id=payload.supplier_id,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    return StockLedgerEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/physical-counts", response_model=PhysicalCountResponse, status_code=201)
def create_physical_count(
    payload: PhysicalCountCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.physical_count", "create")),
):
    assert_company_access(
        db, user_id=user.id, resource="inventory.physical_count", action="create", company_id=payload.company_id
    )
    count = inventory_repository.create_physical_count(
        db, company_id=payload.company_id, warehouse_id=payload.warehouse_id, count_date=payload.count_date
    )
    for line in payload.lines:
        inventory_repository.add_physical_count_line(
            db,
            physical_count_id=count.id,
            item_id=line.item_id,
            expected_quantity=line.expected_quantity,
            counted_quantity=line.counted_quantity,
        )
    count.status = "COUNTED"
    db.commit()
    db.refresh(count)
    return PhysicalCountResponse.model_validate(count, from_attributes=True)


@router.post("/physical-counts/{physical_count_id}/approve", response_model=PhysicalCountResponse)
def approve_physical_count(
    physical_count_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.physical_count", "approve")),
):
    existing = inventory_repository.get_physical_count(db, physical_count_id)
    if existing is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Conteo físico no encontrado")
    assert_company_access(
        db,
        user_id=user.id,
        resource="inventory.physical_count",
        action="approve",
        company_id=existing.company_id,
    )
    count = inventory_service.apply_physical_count(db, physical_count_id=physical_count_id, approved_by_id=user.id)
    return PhysicalCountResponse.model_validate(count, from_attributes=True)
