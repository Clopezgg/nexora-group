import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import (
    ImmutableMaintenanceOrderError,
    InvalidFinancialReferenceError,
    InvalidOperationScopeError,
)
from app.models.equipment import EQUIPMENT_STATUSES, MAINTENANCE_TERMINAL_STATUSES, Equipment, FuelLog, MaintenanceOrder, MaintenancePlan
from app.repositories import equipment_repository
from app.services.financial_validation_service import assert_project_belongs_to_company

"""Equipment / Fuel / Maintenance (orden maestra §63-64). El costo de
combustible y mantenimiento se atribuye a Project como costo -- nunca como
custodia de efectivo (CLAUDE.md §1); la contabilización real hacia el Posting
Engine queda documentada como deuda intencional (docs/ENTERPRISE_RESOURCES.md) mientras
no exista una cuenta de gasto configurable por company como en Fixed Assets."""


def _assert_fuel_scope(scope: str, project_id: uuid.UUID | None) -> None:
    if scope not in ("GENERAL", "PROJECT"):
        raise InvalidOperationScopeError(
            f"scope inválido para fuel log: {scope!r} (solo GENERAL o PROJECT)"
        )
    if scope == "GENERAL" and project_id is not None:
        raise InvalidOperationScopeError("scope=GENERAL requiere project_id=None")
    if scope == "PROJECT" and project_id is None:
        raise InvalidOperationScopeError("scope=PROJECT requiere project_id")


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
    commit: bool = True,
) -> Equipment:
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    equipment = equipment_repository.create_equipment(
        db,
        company_id=company_id,
        asset_id=asset_id,
        project_id=project_id,
        equipment_type=equipment_type,
        name=name,
        serial_number=serial_number,
        plate_number=plate_number,
        operator=operator,
    )
    if commit:
        db.commit()
        db.refresh(equipment)
    else:
        db.flush()
    return equipment


def get_equipment(db: Session, equipment_id: uuid.UUID) -> Equipment | None:
    return equipment_repository.get_equipment(db, equipment_id)


def list_equipment(db: Session, *, company_id: uuid.UUID) -> list[Equipment]:
    return equipment_repository.list_equipment(db, company_id=company_id)


def change_equipment_status(db: Session, *, equipment_id: uuid.UUID, status: str, commit: bool = True) -> Equipment:
    equipment = equipment_repository.get_equipment(db, equipment_id)
    if equipment is None:
        raise ValueError(f"Equipment {equipment_id} no existe")
    if status not in EQUIPMENT_STATUSES:
        raise InvalidOperationScopeError(f"status inválido: {status!r}")
    equipment.status = status
    if commit:
        db.commit()
        db.refresh(equipment)
    else:
        db.flush()
    return equipment


def record_fuel_log(
    db: Session,
    *,
    company_id: uuid.UUID,
    equipment_id: uuid.UUID | None,
    vehicle_description: str | None,
    log_date: date,
    quantity: Decimal,
    unit_cost: Decimal,
    scope: str,
    project_id: uuid.UUID | None,
    commit: bool = True,
) -> FuelLog:
    """`total_cost` SIEMPRE se calcula server-side (quantity * unit_cost);
    nunca se acepta un total hardcodeado del cliente (CLAUDE.md: no hardcoded
    financial data)."""
    _assert_fuel_scope(scope, project_id)
    assert_project_belongs_to_company(db, project_id=project_id, company_id=company_id)
    if equipment_id is not None:
        equipment = equipment_repository.get_equipment(db, equipment_id)
        if equipment is None or equipment.company_id != company_id:
            raise InvalidFinancialReferenceError(
                "equipment_id debe pertenecer a la compañía propietaria"
            )
    total_cost = (quantity * unit_cost).quantize(Decimal("0.01"))
    log = equipment_repository.create_fuel_log(
        db,
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
    if commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log


def list_fuel_logs(db: Session, *, equipment_id: uuid.UUID) -> list[FuelLog]:
    return equipment_repository.list_fuel_logs(db, equipment_id=equipment_id)


def create_maintenance_plan(
    db: Session,
    *,
    equipment_id: uuid.UUID,
    name: str,
    trigger_type: str,
    trigger_value: Decimal,
    description: str | None,
    commit: bool = True,
) -> MaintenancePlan:
    plan = equipment_repository.create_maintenance_plan(
        db,
        equipment_id=equipment_id,
        name=name,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        description=description,
    )
    if commit:
        db.commit()
        db.refresh(plan)
    else:
        db.flush()
    return plan


def list_maintenance_plans(db: Session, *, equipment_id: uuid.UUID) -> list[MaintenancePlan]:
    return equipment_repository.list_maintenance_plans(db, equipment_id=equipment_id)


def create_maintenance_order(
    db: Session,
    *,
    equipment_id: uuid.UUID,
    plan_id: uuid.UUID | None,
    order_type: str,
    opened_at: date,
    supplier_ref: str | None,
    description: str | None,
    commit: bool = True,
) -> MaintenanceOrder:
    order = equipment_repository.create_maintenance_order(
        db,
        equipment_id=equipment_id,
        plan_id=plan_id,
        order_type=order_type,
        opened_at=opened_at,
        supplier_ref=supplier_ref,
        description=description,
    )
    equipment = equipment_repository.get_equipment(db, equipment_id)
    if equipment is not None:
        equipment.status = "UNDER_MAINTENANCE"
    if commit:
        db.commit()
        db.refresh(order)
    else:
        db.flush()
    return order


def list_maintenance_orders(db: Session, *, equipment_id: uuid.UUID) -> list[MaintenanceOrder]:
    return equipment_repository.list_maintenance_orders(db, equipment_id=equipment_id)


def update_maintenance_order(
    db: Session,
    *,
    order_id: uuid.UUID,
    status: str | None = None,
    parts_cost: Decimal | None = None,
    labor_cost: Decimal | None = None,
    downtime_hours: Decimal | None = None,
    description: str | None = None,
    closed_at: date | None = None,
    commit: bool = True,
) -> MaintenanceOrder:
    """INV-EQP-001: un MaintenanceOrder CLOSED/CANCELLED es terminal. Se
    rechaza CUALQUIER mutación (incluido volver a "cerrarlo") antes de tocar
    un solo campo -- los valores persistidos quedan exactamente igual."""
    order = equipment_repository.get_maintenance_order(db, order_id)
    if order is None:
        raise ValueError(f"MaintenanceOrder {order_id} no existe")
    if order.status in MAINTENANCE_TERMINAL_STATUSES:
        raise ImmutableMaintenanceOrderError(
            f"MaintenanceOrder {order.id} está {order.status}; es inmutable"
        )

    if status is not None:
        order.status = status
        if status == "CLOSED":
            order.closed_at = closed_at or date.today()
    if parts_cost is not None:
        order.parts_cost = parts_cost
    if labor_cost is not None:
        order.labor_cost = labor_cost
    if downtime_hours is not None:
        order.downtime_hours = downtime_hours
    if description is not None:
        order.description = description

    if commit:
        db.commit()
        db.refresh(order)
        if order.status == "CLOSED":
            equipment = equipment_repository.get_equipment(db, order.equipment_id)
            if equipment is not None and equipment.status == "UNDER_MAINTENANCE":
                equipment.status = "AVAILABLE"
                db.commit()
    else:
        if order.status == "CLOSED":
            equipment = equipment_repository.get_equipment(db, order.equipment_id)
            if equipment is not None and equipment.status == "UNDER_MAINTENANCE":
                equipment.status = "AVAILABLE"
        db.flush()

    return order
