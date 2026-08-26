import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, FuelLog, MaintenanceOrder, MaintenancePlan


def create_equipment(
    db: Session,
    *,
    company_id: uuid.UUID,
    asset_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    equipment_type: str,
    name: str,
    serial_number: str | None,
    plate_number: str | None,
    operator: str | None,
) -> Equipment:
    equipment = Equipment(
        company_id=company_id,
        asset_id=asset_id,
        project_id=project_id,
        equipment_type=equipment_type,
        name=name,
        serial_number=serial_number,
        plate_number=plate_number,
        operator=operator,
    )
    db.add(equipment)
    db.flush()
    return equipment


def get_equipment(db: Session, equipment_id: uuid.UUID) -> Equipment | None:
    return db.get(Equipment, equipment_id)


def list_equipment(db: Session, *, company_id: uuid.UUID) -> list[Equipment]:
    stmt = select(Equipment).where(Equipment.company_id == company_id).order_by(Equipment.name)
    return list(db.execute(stmt).scalars())


def create_fuel_log(
    db: Session,
    *,
    company_id: uuid.UUID,
    equipment_id: uuid.UUID | None,
    vehicle_description: str | None,
    log_date: date,
    quantity: Decimal,
    unit_cost: Decimal,
    total_cost: Decimal,
    scope: str,
    project_id: uuid.UUID | None,
) -> FuelLog:
    log = FuelLog(
        company_id=company_id,
        equipment_id=equipment_id,
        vehicle_description=vehicle_description,
        log_date=log_date,
        quantity=quantity,
        unit_cost=unit_cost,
        total_cost=total_cost,
        scope=scope,
        project_id=project_id,
    )
    db.add(log)
    db.flush()
    return log


def list_fuel_logs(db: Session, *, equipment_id: uuid.UUID) -> list[FuelLog]:
    stmt = select(FuelLog).where(FuelLog.equipment_id == equipment_id).order_by(FuelLog.log_date)
    return list(db.execute(stmt).scalars())


def create_maintenance_plan(
    db: Session,
    *,
    equipment_id: uuid.UUID,
    name: str,
    trigger_type: str,
    trigger_value: Decimal,
    description: str | None,
) -> MaintenancePlan:
    plan = MaintenancePlan(
        equipment_id=equipment_id,
        name=name,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        description=description,
    )
    db.add(plan)
    db.flush()
    return plan


def list_maintenance_plans(db: Session, *, equipment_id: uuid.UUID) -> list[MaintenancePlan]:
    stmt = select(MaintenancePlan).where(MaintenancePlan.equipment_id == equipment_id)
    return list(db.execute(stmt).scalars())


def create_maintenance_order(
    db: Session,
    *,
    equipment_id: uuid.UUID,
    plan_id: uuid.UUID | None,
    order_type: str,
    opened_at: date,
    supplier_id: uuid.UUID | None,
    supplier_ref: str | None,
    description: str | None,
) -> MaintenanceOrder:
    order = MaintenanceOrder(
        equipment_id=equipment_id,
        plan_id=plan_id,
        order_type=order_type,
        opened_at=opened_at,
        supplier_id=supplier_id,
        supplier_ref=supplier_ref,
        description=description,
    )
    db.add(order)
    db.flush()
    return order


def get_maintenance_order(db: Session, order_id: uuid.UUID) -> MaintenanceOrder | None:
    return db.get(MaintenanceOrder, order_id)


def list_maintenance_orders(db: Session, *, equipment_id: uuid.UUID) -> list[MaintenanceOrder]:
    stmt = (
        select(MaintenanceOrder)
        .where(MaintenanceOrder.equipment_id == equipment_id)
        .order_by(MaintenanceOrder.opened_at)
    )
    return list(db.execute(stmt).scalars())
