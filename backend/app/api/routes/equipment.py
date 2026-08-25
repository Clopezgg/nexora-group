import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import equipment_repository
from app.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentResponse,
    EquipmentStatusChangeRequest,
    FuelLogCreateRequest,
    FuelLogResponse,
    MaintenanceOrderCreateRequest,
    MaintenanceOrderResponse,
    MaintenanceOrderUpdateRequest,
    MaintenancePlanCreateRequest,
    MaintenancePlanResponse,
)
from app.services import equipment_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _resolve_equipment(db: Session, equipment_id: uuid.UUID):
    equipment = equipment_service.get_equipment(db, equipment_id)
    if equipment is None:
        raise ValueError(f"Equipment {equipment_id} no existe")
    return equipment


def _resolve_order_equipment(db: Session, order_id: uuid.UUID):
    order = equipment_repository.get_maintenance_order(db, order_id)
    if order is None:
        raise ValueError(f"MaintenanceOrder {order_id} no existe")
    equipment = _resolve_equipment(db, order.equipment_id)
    return order, equipment


@router.post("", response_model=EquipmentResponse, status_code=201)
def create_equipment(
    payload: EquipmentCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.equipment", "create")),
) -> EquipmentResponse:
    assert_company_access(
        db, user_id=user.id, resource="equipment.equipment", action="create", company_id=payload.company_id
    )
    equipment = equipment_service.create_equipment(
        db,
        company_id=payload.company_id,
        asset_id=payload.asset_id,
        project_id=payload.project_id,
        equipment_type=payload.equipment_type,
        name=payload.name,
        serial_number=payload.serial_number,
        plate_number=payload.plate_number,
        operator=payload.operator,
    )
    return EquipmentResponse.model_validate(equipment, from_attributes=True)


@router.get("", response_model=list[EquipmentResponse])
def list_equipment(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.equipment", "read")),
) -> list[EquipmentResponse]:
    assert_company_access(
        db, user_id=user.id, resource="equipment.equipment", action="read", company_id=company_id
    )
    return [
        EquipmentResponse.model_validate(item, from_attributes=True)
        for item in equipment_service.list_equipment(db, company_id=company_id)
    ]


@router.get("/{equipment_id}", response_model=EquipmentResponse)
def get_equipment(
    equipment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.equipment", "read")),
) -> EquipmentResponse:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db, user_id=user.id, resource="equipment.equipment", action="read", company_id=equipment.company_id
    )
    return EquipmentResponse.model_validate(equipment, from_attributes=True)


@router.post("/{equipment_id}/status", response_model=EquipmentResponse)
def change_equipment_status(
    equipment_id: uuid.UUID,
    payload: EquipmentStatusChangeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.equipment", "update")),
) -> EquipmentResponse:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db, user_id=user.id, resource="equipment.equipment", action="update", company_id=equipment.company_id
    )
    equipment = equipment_service.change_equipment_status(
        db, equipment_id=equipment_id, status=payload.status
    )
    return EquipmentResponse.model_validate(equipment, from_attributes=True)


@router.post("/fuel-logs", response_model=FuelLogResponse, status_code=201)
def record_fuel_log(
    payload: FuelLogCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.fuel_log", "create")),
) -> FuelLogResponse:
    assert_company_access(
        db, user_id=user.id, resource="equipment.fuel_log", action="create", company_id=payload.company_id
    )
    log = equipment_service.record_fuel_log(
        db,
        company_id=payload.company_id,
        equipment_id=payload.equipment_id,
        vehicle_description=payload.vehicle_description,
        log_date=payload.log_date,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        scope=payload.scope,
        project_id=payload.project_id,
    )
    return FuelLogResponse.model_validate(log, from_attributes=True)


@router.get("/{equipment_id}/fuel-logs", response_model=list[FuelLogResponse])
def list_fuel_logs(
    equipment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.fuel_log", "read")),
) -> list[FuelLogResponse]:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db, user_id=user.id, resource="equipment.fuel_log", action="read", company_id=equipment.company_id
    )
    return [
        FuelLogResponse.model_validate(log, from_attributes=True)
        for log in equipment_service.list_fuel_logs(db, equipment_id=equipment_id)
    ]


@router.post(
    "/{equipment_id}/maintenance-plans", response_model=MaintenancePlanResponse, status_code=201
)
def create_maintenance_plan(
    equipment_id: uuid.UUID,
    payload: MaintenancePlanCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.maintenance_plan", "create")),
) -> MaintenancePlanResponse:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="equipment.maintenance_plan",
        action="create",
        company_id=equipment.company_id,
    )
    plan = equipment_service.create_maintenance_plan(
        db,
        equipment_id=equipment_id,
        name=payload.name,
        trigger_type=payload.trigger_type,
        trigger_value=payload.trigger_value,
        description=payload.description,
    )
    return MaintenancePlanResponse.model_validate(plan, from_attributes=True)


@router.get("/{equipment_id}/maintenance-plans", response_model=list[MaintenancePlanResponse])
def list_maintenance_plans(
    equipment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.maintenance_plan", "read")),
) -> list[MaintenancePlanResponse]:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="equipment.maintenance_plan",
        action="read",
        company_id=equipment.company_id,
    )
    return [
        MaintenancePlanResponse.model_validate(plan, from_attributes=True)
        for plan in equipment_service.list_maintenance_plans(db, equipment_id=equipment_id)
    ]


@router.post(
    "/{equipment_id}/maintenance-orders", response_model=MaintenanceOrderResponse, status_code=201
)
def create_maintenance_order(
    equipment_id: uuid.UUID,
    payload: MaintenanceOrderCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.maintenance_order", "create")),
) -> MaintenanceOrderResponse:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="equipment.maintenance_order",
        action="create",
        company_id=equipment.company_id,
    )
    order = equipment_service.create_maintenance_order(
        db,
        equipment_id=equipment_id,
        plan_id=payload.plan_id,
        order_type=payload.order_type,
        opened_at=payload.opened_at,
        supplier_ref=payload.supplier_ref,
        description=payload.description,
    )
    return MaintenanceOrderResponse.model_validate(order, from_attributes=True)


@router.get("/{equipment_id}/maintenance-orders", response_model=list[MaintenanceOrderResponse])
def list_maintenance_orders(
    equipment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.maintenance_order", "read")),
) -> list[MaintenanceOrderResponse]:
    equipment = _resolve_equipment(db, equipment_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="equipment.maintenance_order",
        action="read",
        company_id=equipment.company_id,
    )
    return [
        MaintenanceOrderResponse.model_validate(order, from_attributes=True)
        for order in equipment_service.list_maintenance_orders(db, equipment_id=equipment_id)
    ]


@router.patch("/maintenance-orders/{order_id}", response_model=MaintenanceOrderResponse)
def update_maintenance_order(
    order_id: uuid.UUID,
    payload: MaintenanceOrderUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("equipment.maintenance_order", "update")),
) -> MaintenanceOrderResponse:
    _order, equipment = _resolve_order_equipment(db, order_id)
    assert_company_access(
        db,
        user_id=user.id,
        resource="equipment.maintenance_order",
        action="update",
        company_id=equipment.company_id,
    )
    order = equipment_service.update_maintenance_order(
        db,
        order_id=order_id,
        status=payload.status,
        parts_cost=payload.parts_cost,
        labor_cost=payload.labor_cost,
        downtime_hours=payload.downtime_hours,
        description=payload.description,
        closed_at=payload.closed_at,
    )
    return MaintenanceOrderResponse.model_validate(order, from_attributes=True)
