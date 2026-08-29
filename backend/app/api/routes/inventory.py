import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
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
from app.services import audit_service, inventory_service
from app.services.financial_validation_service import assert_supplier_belongs_to_company
from app.services.permission_service import (
    accessible_project_ids,
    assert_company_access,
    require_permission,
)

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
    correlation_id: str = Depends(get_correlation_id),
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
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.item.create",
        entity_type="inventory.item",
        entity_id=item.id,
        company_id=item.company_id,
        project_id=None,
        before=None,
        after={
            "sku": item.sku,
            "name": item.name,
            "itemType": item.item_type,
        },
        correlation_id=correlation_id,
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
    allowed = accessible_project_ids(
        db, user_id=user.id, resource="inventory.warehouse", action="read"
    )
    if allowed is not None:
        allowed_set = set(allowed)
        warehouses = [
            row for row in warehouses
            if row.project_id is None or row.project_id in allowed_set
        ]
    return [WarehouseResponse.model_validate(w, from_attributes=True) for w in warehouses]


@router.post("/warehouses", response_model=WarehouseResponse, status_code=201)
def create_warehouse(
    payload: WarehouseCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.warehouse", "create")),
    correlation_id: str = Depends(get_correlation_id),
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
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.warehouse.create",
        entity_type="inventory.warehouse",
        entity_id=warehouse.id,
        company_id=warehouse.company_id,
        project_id=warehouse.project_id,
        before=None,
        after={
            "code": warehouse.code,
            "name": warehouse.name,
        },
        correlation_id=correlation_id,
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
    correlation_id: str = Depends(get_correlation_id),
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
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.stock.receive",
        entity_type="inventory.stock",
        entity_id=entry.id,
        company_id=payload.company_id,
        project_id=None,
        before=None,
        after={
            "itemId": str(payload.item_id),
            "warehouseId": str(payload.warehouse_id),
            "quantity": str(payload.quantity),
            "unitCost": str(payload.unit_cost),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return StockLedgerEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/stock/issue-to-project", response_model=StockLedgerEntryResponse, status_code=201)
def issue_to_project(
    payload: StockIssueToProjectRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
    correlation_id: str = Depends(get_correlation_id),
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
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.stock.issue_to_project",
        entity_type="inventory.stock",
        entity_id=entry.id,
        company_id=payload.company_id,
        project_id=payload.project_id,
        before=None,
        after={
            "itemId": str(payload.item_id),
            "warehouseId": str(payload.warehouse_id),
            "projectId": str(payload.project_id),
            "quantity": str(payload.quantity),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return StockLedgerEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/stock/transfer", response_model=list[StockLedgerEntryResponse], status_code=201)
def transfer_stock(
    payload: StockTransferRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
    correlation_id: str = Depends(get_correlation_id),
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
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.stock.transfer",
        entity_type="inventory.stock",
        entity_id=outgoing.id,
        company_id=payload.company_id,
        project_id=None,
        before=None,
        after={
            "itemId": str(payload.item_id),
            "fromWarehouseId": str(payload.from_warehouse_id),
            "toWarehouseId": str(payload.to_warehouse_id),
            "quantity": str(payload.quantity),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return [
        StockLedgerEntryResponse.model_validate(outgoing, from_attributes=True),
        StockLedgerEntryResponse.model_validate(incoming, from_attributes=True),
    ]


@router.post("/stock/return-to-supplier", response_model=StockLedgerEntryResponse, status_code=201)
def return_to_supplier(
    payload: StockReturnToSupplierRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.stock", "move")),
    correlation_id: str = Depends(get_correlation_id),
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
        commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.stock.return_to_supplier",
        entity_type="inventory.stock",
        entity_id=entry.id,
        company_id=payload.company_id,
        project_id=None,
        before=None,
        after={
            "itemId": str(payload.item_id),
            "warehouseId": str(payload.warehouse_id),
            "supplierId": str(payload.supplier_id),
            "quantity": str(payload.quantity),
        },
        correlation_id=correlation_id,
    )
    db.commit()
    return StockLedgerEntryResponse.model_validate(entry, from_attributes=True)


@router.post("/physical-counts", response_model=PhysicalCountResponse, status_code=201)
def create_physical_count(
    payload: PhysicalCountCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.physical_count", "create")),
    correlation_id: str = Depends(get_correlation_id),
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
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.physical_count.create",
        entity_type="inventory.physical_count",
        entity_id=count.id,
        company_id=count.company_id,
        project_id=None,
        before=None,
        after={
            "warehouseId": str(payload.warehouse_id),
            "status": "COUNTED",
        },
        correlation_id=correlation_id,
    )
    db.commit()
    db.refresh(count)
    return PhysicalCountResponse.model_validate(count, from_attributes=True)


@router.post("/physical-counts/{physical_count_id}/approve", response_model=PhysicalCountResponse)
def approve_physical_count(
    physical_count_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("inventory.physical_count", "approve")),
    correlation_id: str = Depends(get_correlation_id),
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
    before_status = existing.status
    count = inventory_service.apply_physical_count(
        db, physical_count_id=physical_count_id, approved_by_id=user.id, commit=False,
    )
    audit_service.record(
        db,
        actor_user_id=user.id,
        action="inventory.physical_count.approve",
        entity_type="inventory.physical_count",
        entity_id=count.id,
        company_id=count.company_id,
        project_id=None,
        before={"status": before_status},
        after={"status": count.status},
        correlation_id=correlation_id,
    )
    db.commit()
    return PhysicalCountResponse.model_validate(count, from_attributes=True)
