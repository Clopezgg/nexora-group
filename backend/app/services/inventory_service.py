import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.errors import InsufficientStockError
from app.models.inventory import PhysicalCount, StockLedgerEntry
from app.repositories import inventory_repository

"""Stock Ledger append-only (orden maestra §54, docs/INVENTORY.md). Todo
movimiento pasa por aquí -- nunca se inserta un StockLedgerEntry a mano
desde un router ni se guarda "cantidad actual" en una columna mutable de
Item/Warehouse. Valuación: moving average (orden maestra §54)."""


def _lock_stock_position(
    db: Session, *, company_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID
) -> None:
    """Advisory transaction lock (auto-liberado al hacer commit/rollback)
    que serializa lectores/escritores concurrentes de la MISMA posición
    (item, warehouse). El ledger es append-only por diseño -- no existe una
    fila mutable de "cantidad actual" que un SELECT...FOR UPDATE normal
    pudiera bloquear y que de verdad detuviera un INSERT concurrente: dos
    llamadas concurrentes a `_issue`/`_receive_stock_entry` podían leer la
    MISMA "última entrada" (ninguna de las dos había hecho commit todavía)
    y ambas pasar el guard INV-INV-001 de stock disponible aunque juntas
    excedieran el stock real -- encontrado con una prueba de concurrencia
    real (`tests/test_concurrency.py`), no en teoría. `pg_advisory_xact_lock`
    es reentrante dentro de la misma transacción, así que llamarlo más de
    una vez para la misma clave (p.ej. `transfer_stock` bloqueando ambos
    warehouses por adelantado y luego `_issue`/`_receive_stock_entry`
    bloqueando de nuevo internamente) es un no-op seguro, nunca un
    auto-deadlock."""
    key = f"stock_position:{company_id}:{item_id}:{warehouse_id}"
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


def _current_position(
    db: Session, *, company_id: uuid.UUID, item_id: uuid.UUID, warehouse_id: uuid.UUID
) -> tuple[Decimal, Decimal]:
    _lock_stock_position(db, company_id=company_id, item_id=item_id, warehouse_id=warehouse_id)
    last = inventory_repository.get_last_ledger_entry(
        db, company_id=company_id, item_id=item_id, warehouse_id=warehouse_id
    )
    if last is None:
        return Decimal("0"), Decimal("0")
    return last.resulting_qty_on_hand, last.resulting_avg_cost


def _receive_stock_entry(
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
    if quantity <= 0:
        raise InsufficientStockError("La cantidad recibida debe ser positiva")
    qty_before, avg_cost_before = _current_position(
        db, company_id=company_id, item_id=item_id, warehouse_id=warehouse_id
    )
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
    return entry


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
    commit: bool = True,
) -> StockLedgerEntry:
    """RECEIPT. Actualiza el costo promedio ponderado (moving average)."""
    entry = _receive_stock_entry(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        unit_cost=unit_cost,
        source_type=source_type,
        source_id=source_id,
    )
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
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
    qty_before, avg_cost = _current_position(
        db, company_id=company_id, item_id=item_id, warehouse_id=warehouse_id
    )
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
    return entry


def issue_to_project(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    project_id: uuid.UUID,
    quantity: Decimal,
    commit: bool = True,
) -> StockLedgerEntry:
    """INV-INV-002: reduce warehouse stock y reconoce el costo (al costo
    promedio) sobre el project_id indicado. El posting contable real (débito
    a costo de proyecto) lo conecta Track B/A cuando integren este track --
    ver docs/INVENTORY.md contrato de integración; aquí se deja el registro
    de consumo con project_id explícito, listo para ese posting."""
    entry = _issue(
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
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def return_to_supplier(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    supplier_id: uuid.UUID,
    quantity: Decimal,
    notes: str | None = None,
    commit: bool = True,
) -> StockLedgerEntry:
    """RETURN (devolución a proveedor, docs/INVENTORY.md deuda intencional
    ahora resuelta): reduce stock exactamente igual que un ISSUE -- mismo
    costo promedio vigente, mismo guard INV-INV-001 de stock insuficiente
    -- pero con su propio `movement_type` y `source_type="supplier_return"`
    apuntando al proveedor, para que nunca se confunda con un consumo real
    de proyecto en el ledger."""
    entry = _issue(
        db,
        company_id=company_id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        movement_type="RETURN",
        project_id=None,
        source_type="supplier_return",
        source_id=supplier_id,
        notes=notes,
    )
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def transfer_stock(
    db: Session,
    *,
    company_id: uuid.UUID,
    item_id: uuid.UUID,
    from_warehouse_id: uuid.UUID,
    to_warehouse_id: uuid.UUID,
    quantity: Decimal,
    commit: bool = True,
) -> tuple[StockLedgerEntry, StockLedgerEntry]:
    """Move stock in one database transaction or leave neither ledger leg."""
    # Bloquea AMBAS posiciones por adelantado, en orden canónico (nunca en
    # el orden from->to del parámetro), antes de tocar cualquiera de las
    # dos -- una transferencia concurrente en dirección opuesta (to->from)
    # para el mismo item/par de warehouses adquiriría las mismas dos claves
    # en orden inverso si cada lado bloqueara solo la suya según su propio
    # from/to; con orden canónico ambas transacciones piden las claves en
    # la misma secuencia y ninguna puede quedar en deadlock esperando a la
    # otra (pg_advisory_xact_lock es reentrante, así que _issue/
    # _receive_stock_entry pueden volver a pedir la misma clave después
    # sin bloquearse a sí mismos).
    for warehouse_id in sorted((from_warehouse_id, to_warehouse_id), key=str):
        _lock_stock_position(db, company_id=company_id, item_id=item_id, warehouse_id=warehouse_id)

    _, avg_cost = _current_position(
        db, company_id=company_id, item_id=item_id, warehouse_id=from_warehouse_id
    )
    try:
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
        incoming = _receive_stock_entry(
            db,
            company_id=company_id,
            item_id=item_id,
            warehouse_id=to_warehouse_id,
            quantity=quantity,
            unit_cost=avg_cost,
            source_type="transfer_from",
            source_id=from_warehouse_id,
        )
        if commit:
            db.commit()
        else:
            db.flush()
    except Exception:
        db.rollback()
        raise
    db.refresh(outgoing)
    db.refresh(incoming)
    return outgoing, incoming


def apply_physical_count(
    db: Session,
    *,
    physical_count_id: uuid.UUID,
    approved_by_id: uuid.UUID,
    commit: bool = True,
) -> PhysicalCount:
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
        qty_before, avg_cost = _current_position(
            db, company_id=count.company_id, item_id=line.item_id, warehouse_id=count.warehouse_id
        )
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
    if commit:
        db.commit()
        db.refresh(count)
    else:
        db.flush()
    return count
