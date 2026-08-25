import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

EQUIPMENT_STATUSES = ("AVAILABLE", "IN_USE", "UNDER_MAINTENANCE", "OUT_OF_SERVICE")


class Equipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Orden maestra §63. `asset_id` es opcional: no todo equipo se
    capitaliza como Fixed Asset (p.ej. herramienta menor)."""

    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint("hour_meter >= 0", name="ck_equipment_hour_meter_non_negative"),
        CheckConstraint("odometer >= 0", name="ck_equipment_odometer_non_negative"),
        CheckConstraint(
            "status IN ('AVAILABLE','IN_USE','UNDER_MAINTENANCE','OUT_OF_SERVICE')",
            name="ck_equipment_status_valid",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fixed_assets.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    equipment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    plate_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hour_meter: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    odometer: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")


class FuelLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Orden maestra §64. Reusa OperationScope (CLAUDE.md §7) en lugar de
    inventar un concepto de ámbito propio: GENERAL/PROJECT con el mismo
    constraint que AccountingDocument. CENTRAL no aplica a un gasto físico
    de combustible, por eso el CHECK aquí es más estricto (solo GENERAL o
    PROJECT, nunca CENTRAL)."""

    __tablename__ = "fuel_logs"
    __table_args__ = (
        CheckConstraint(
            "(scope = 'GENERAL' AND project_id IS NULL) "
            "OR (scope = 'PROJECT' AND project_id IS NOT NULL)",
            name="ck_fuel_logs_operation_scope",
        ),
        CheckConstraint("quantity > 0", name="ck_fuel_logs_quantity_positive"),
        CheckConstraint("unit_cost > 0", name="ck_fuel_logs_unit_cost_positive"),
        CheckConstraint("total_cost > 0", name="ck_fuel_logs_total_cost_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="GENERAL")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )


MAINTENANCE_TYPES = ("PREVENTIVE", "CORRECTIVE")
# "CLOSED" (no "COMPLETED"): un MaintenanceOrder CLOSED o CANCELLED es
# terminal e inmutable -- ver maintenance_service.update_maintenance_order,
# INV-EQP-001.
MAINTENANCE_ORDER_STATUSES = ("OPEN", "IN_PROGRESS", "CLOSED", "CANCELLED")
MAINTENANCE_TERMINAL_STATUSES = ("CLOSED", "CANCELLED")
MAINTENANCE_TRIGGER_TYPES = ("DATE", "HOURS", "ODOMETER")


class MaintenancePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_plans"
    __table_args__ = (
        CheckConstraint("trigger_value > 0", name="ck_maintenance_plans_trigger_value_positive"),
    )

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    trigger_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class MaintenanceOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "maintenance_orders"
    __table_args__ = (
        CheckConstraint("parts_cost >= 0", name="ck_maintenance_orders_parts_cost_non_negative"),
        CheckConstraint("labor_cost >= 0", name="ck_maintenance_orders_labor_cost_non_negative"),
        CheckConstraint(
            "downtime_hours >= 0", name="ck_maintenance_orders_downtime_hours_non_negative"
        ),
        CheckConstraint(
            "status IN ('OPEN','IN_PROGRESS','CLOSED','CANCELLED')",
            name="ck_maintenance_orders_status_valid",
        ),
        CheckConstraint(
            "order_type IN ('PREVENTIVE','CORRECTIVE')",
            name="ck_maintenance_orders_type_valid",
        ),
    )

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_plans.id", ondelete="SET NULL"), nullable=True
    )
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    opened_at: Mapped[date] = mapped_column(Date, nullable=False)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # `supplier_ref` es texto libre hasta que Track C aterrice el Supplier
    # real (mismo patrón de deuda intencional documentado por Track A/C).
    supplier_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parts_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    downtime_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
