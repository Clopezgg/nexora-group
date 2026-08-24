import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inventory import PhysicalCount, PhysicalCountLine, StockLedgerEntry
from app.models.item import Item
from app.models.warehouse import Warehouse


def list_items(db: Session, *, company_id: uuid.UUID) -> list[Item]:
    return list(db.execute(select(Item).where(Item.company_id == company_id).order_by(Item.sku)).scalars())


def create_item(
    db: Session,
    *,
    company_id: uuid.UUID,
    sku: str,
    name: str,
    item_type: str,
    category: str | None,
    uom: str,
    description: str | None,
    track_inventory: bool,
) -> Item:
    item = Item(
        company_id=company_id,
        sku=sku,
        name=name,
        item_type=item_type,
        category=category,
        uom=uom,
        description=description,
        track_inventory=track_inventory,
    )
    db.add(item)
    db.flush()
    return item


def list_warehouses(db: Session, *, company_id: uuid.UUID) -> list[Warehouse]:
    return list(
        db.execute(select(Warehouse).where(Warehouse.company_id == company_id).order_by(Warehouse.code)).scalars()
    )


def create_warehouse(
    db: Session,
    *,
    company_id: uuid.UUID,
    project_id: uuid.UUID | None,
    code: str,
    name: str,
) -> Warehouse:
    warehouse = Warehouse(company_id=company_id, project_id=project_id, code=code, name=name)
    db.add(warehouse)
    db.flush()
    return warehouse


def get_last_ledger_entry(
    db: Session, *, item_id: uuid.UUID, warehouse_id: uuid.UUID
) -> StockLedgerEntry | None:
    """El "estado actual" de stock/costo NUNCA se guarda en una columna
    mutable de Item/Warehouse -- se deriva de la última entrada del ledger
    append-only (INV-INV-001: sin stock duplicado ni fuente de verdad
    paralela)."""
    stmt = (
        select(StockLedgerEntry)
        .where(StockLedgerEntry.item_id == item_id, StockLedgerEntry.warehouse_id == warehouse_id)
        .order_by(StockLedgerEntry.created_at.desc(), StockLedgerEntry.id.desc())
        .limit(1)
        .with_for_update()
    )
    return db.execute(stmt).scalar_one_or_none()


def append_ledger_entry(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    movement_type: str,
    quantity: Decimal,
    unit_cost: Decimal,
    resulting_qty_on_hand: Decimal,
    resulting_avg_cost: Decimal,
    project_id: uuid.UUID | None = None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> StockLedgerEntry:
    entry = StockLedgerEntry(
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        resulting_qty_on_hand=resulting_qty_on_hand,
        resulting_avg_cost=resulting_avg_cost,
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        notes=notes,
    )
    db.add(entry)
    db.flush()
    return entry


def project_actuals_by_project(db: Session, *, company_id: uuid.UUID) -> dict[uuid.UUID, Decimal]:
    """Posted material-consumption actuals for Budget/Project Control.

    The ledger is append-only, so an ISSUE created by ``issue_to_project`` is
    already posted. Transfers are excluded by both movement type and source;
    they relocate stock but never create project cost or cash.
    """
    total = func.sum(StockLedgerEntry.quantity * StockLedgerEntry.unit_cost)
    stmt = (
        select(StockLedgerEntry.project_id, total.label("total"))
        .where(
            StockLedgerEntry.company_id == company_id,
            StockLedgerEntry.movement_type == "ISSUE",
            StockLedgerEntry.source_type == "project_issue",
            StockLedgerEntry.project_id.is_not(None),
        )
        .group_by(StockLedgerEntry.project_id)
    )
    return {project_id: Decimal(total) for project_id, total in db.execute(stmt)}


def create_physical_count(
    db: Session, *, company_id: uuid.UUID, warehouse_id: uuid.UUID, count_date
) -> PhysicalCount:
    count = PhysicalCount(company_id=company_id, warehouse_id=warehouse_id, count_date=count_date)
    db.add(count)
    db.flush()
    return count


def add_physical_count_line(
    db: Session,
    *,
    physical_count_id: uuid.UUID,
    item_id: uuid.UUID,
    expected_quantity: Decimal,
    counted_quantity: Decimal,
) -> PhysicalCountLine:
    line = PhysicalCountLine(
        physical_count_id=physical_count_id,
        item_id=item_id,
        expected_quantity=expected_quantity,
        counted_quantity=counted_quantity,
    )
    db.add(line)
    db.flush()
    return line


def get_physical_count(db: Session, physical_count_id: uuid.UUID) -> PhysicalCount | None:
    return db.get(PhysicalCount, physical_count_id)


def list_physical_count_lines(db: Session, physical_count_id: uuid.UUID) -> list[PhysicalCountLine]:
    stmt = select(PhysicalCountLine).where(PhysicalCountLine.physical_count_id == physical_count_id)
    return list(db.execute(stmt).scalars())
