import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.errors import InsufficientStockError
from app.models.inventory import PhysicalCount, StockLedgerEntry
from app.repositories import inventory_repository

"""Stock Ledger append-only (orden maestra §54, docs/INVENTORY.md). Todo
movimiento pasa por aquí -- nunca se inserta un StockLedgerEntry a mano
desde un router ni se guarda "cantidad actual" en una columna mutable de
Item/Warehouse. Valuación: moving average (orden maestra §54)."""


def _current_position(db: Session, *, item_id: uuid.UUID, warehouse_id: uuid.UUID) -> tuple[Decimal, Decimal]:
    last = inventory_repository.get_last_ledger_entry(db, item_id=item_id, warehouse_id=warehouse_id)
    if last is None:
        return Decimal("0"), Decimal("0")
    return last.resulting_qty_on_hand, last.resulting_avg_cost


def receive_stock(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: Decimal,
    unit_cost: Decimal,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
) -> StockLedgerEntry:
    """RECEIPT. Actualiza el costo promedio ponderado (moving average)."""
    if quantity <= 0:
        raise InsufficientStockError("La cantidad recibida debe ser positiva")
    qty_before, avg_cost_before = _current_position(db, item_id=item_id, warehouse_id=warehouse_id)
    new_qty = qty_before + quantity
    new_value = (qty_before * avg_cost_before) + (quantity * unit_cost)
    new_avg_cost = (new_value / new_qty) if new_qty > 0 else Decimal("0")
    entry = inventory_repository.append_ledger_entry(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        movement_type="RECEIPT",
        quantity=quantity,
        unit_cost=unit_cost,
        resulting_qty_on_hand=new_qty,
        resulting_avg_cost=new_avg_cost,
        source_type=source_type,
        source_id=source_id,
    )
    db.commit()
    db.refresh(entry)
    return entry


def _issue(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    quantity: Decimal,
    movement_type: str,
    project_id: uuid.UUID | None,
    source_type: str | None,
    source_id: uuid.UUID | None,
    notes: str | None = None,
) -> StockLedgerEntry:
    if quantity <= 0:
        raise InsufficientStockError("La cantidad a emitir/transferir debe ser positiva")
    qty_before, avg_cost = _current_position(db, item_id=item_id, warehouse_id=warehouse_id)
    if quantity > qty_before:
        raise InsufficientStockError(
            f"Stock insuficiente: disponible={qty_before}, solicitado={quantity} (INV-INV-001)"
        )
    new_qty = qty_before - quantity
    entry = inventory_repository.append_ledger_entry(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=avg_cost,
        resulting_qty_on_hand=new_qty,
        resulting_avg_cost=avg_cost,
        project_id=project_id,
        source_type=source_type,
        source_id=source_id,
        notes=notes,
    )
    db.commit()
    db.refresh(entry)
    return entry


def issue_to_project(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    project_id: uuid.UUID,
    quantity: Decimal,
) -> StockLedgerEntry:
    """INV-INV-002: reduce warehouse stock y reconoce el costo (al costo
    promedio) sobre el project_id indicado. El posting contable real (débito
    a costo de proyecto) lo conecta Track B/A cuando integren este track --
    ver docs/INVENTORY.md contrato de integración; aquí se deja el registro
    de consumo con project_id explícito, listo para ese posting."""
    return _issue(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        movement_type="ISSUE",
        project_id=project_id,
        source_type="project_issue",
        source_id=project_id,
    )


def transfer_stock(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    quantity: Decimal,
) -> tuple[StockLedgerEntry, StockLedgerEntry]:
    _, avg_cost = _current_position(db, item_id=item_id, warehouse_id=from_warehouse_id)
    outgoing = _issue(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=from_warehouse_id,
        quantity=quantity,
        movement_type="TRANSFER",
        project_id=None,
        source_type="transfer_to",
        source_id=to_warehouse_id,
    )
    incoming = receive_stock(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=to_warehouse_id,
        quantity=quantity,
        unit_cost=avg_cost,
        source_type="transfer_from",
        source_id=from_warehouse_id,
    )
    return outgoing, incoming


def apply_physical_count(db: Session, *, physical_count_id: uuid.UUID, approved_by_id: uuid.UUID) -> PhysicalCount:
    """Genera un ADJUSTMENT por cada línea con variance != 0 y marca el
    conteo como APPROVED. No se editan entradas previas del ledger -- una
    corrección siempre es una entrada nueva."""
    count = inventory_repository.get_physical_count(db, physical_count_id)
    if count is None:
        raise ValueError(f"PhysicalCount {physical_count_id} no existe")
    lines = inventory_repository.list_physical_count_lines(db, physical_count_id)
    for line in lines:
        variance = line.counted_quantity - line.expected_quantity
        if variance == 0:
            continue
        qty_before, avg_cost = _current_position(db, item_id=line.item_id, warehouse_id=count.warehouse_id)
        new_qty = qty_before + variance
        inventory_repository.append_ledger_entry(
            db,
            company_id=count.company_id,
            item_id=line.item_id,
            warehouse_id=count.warehouse_id,
            movement_type="PHYSICAL_COUNT",
            quantity=abs(variance),
            unit_cost=avg_cost,
            resulting_qty_on_hand=new_qty,
            resulting_avg_cost=avg_cost,
            source_type="physical_count",
            source_id=physical_count_id,
            notes=f"Ajuste por conteo físico: esperado={line.expected_quantity}, contado={line.counted_quantity}",
        )
    count.status = "APPROVED"
    count.approved_by_id = approved_by_id
    db.commit()
    db.refresh(count)
    return count
