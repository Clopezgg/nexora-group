# Inventory — Track C (Supply Chain)

Stock Ledger append-only (orden maestra §54). **Nunca** se guarda "la
cantidad actual" en una columna mutable de `Item`/`Warehouse` — el estado
se deriva siempre de la última fila de `stock_ledger_entries` para ese
`(item_id, warehouse_id)` (`inventory_repository.get_last_ledger_entry`,
con `SELECT ... FOR UPDATE` para que dos movimientos concurrentes sobre el
mismo ítem/almacén no pisen el cálculo de moving average).

## Movement types

`RECEIPT` (recepción de PO o entrada manual), `TRANSFER` (par de
entradas: `TRANSFER` saliente + `RECEIPT` entrante con el mismo costo,
generadas atómicamente por `inventory_service.transfer_stock`), `ISSUE`
(consumo, incluye `issue_to_project`), `RETURN` (no implementado en este
track — el modelo lo soporta como movement_type pero no hay caso de uso
todavía; usar el mismo patrón de `_issue`/`receive_stock` cuando se
necesite), `ADJUSTMENT` (no usado directamente, `PHYSICAL_COUNT` cubre el
caso de ajuste por conteo), `PHYSICAL_COUNT` (generado por
`apply_physical_count` para cada línea con variance != 0).

## Valuación — Moving Average

```
new_avg_cost = (qty_before * avg_cost_before + qty_received * unit_cost)
               / (qty_before + qty_received)
```

Un `ISSUE`/`TRANSFER` sale siempre al costo promedio vigente (nunca
recalcula el promedio hacia abajo). Ver `inventory_service._issue` /
`receive_stock`.

## INV-INV-001 — sin stock negativo silencioso

`_issue()` lanza `InsufficientStockError` (`NXR-INVENTORY-001`, HTTP 409)
si `quantity > qty_before`. No existe ningún camino en el código que
permita `resulting_qty_on_hand < 0`.

## INV-INV-002 — Issue to Project

`issue_to_project()` reduce el stock del warehouse y registra
`project_id` en la entrada del ledger. **El posting contable real
(débito a costo de proyecto / crédito a inventario) no lo hace este
track** — se deja el registro de consumo con `project_id` explícito y
`unit_cost` = costo promedio en el momento del consumo, listo para que
quien conecte el lado contable (Track A/B, o un track de Hardening) llame
a `posting_service.post_manual` con esos datos. Contrato: multiplicar
`quantity * unit_cost` de la entrada `ISSUE` resultante = costo a
reconocer contra el proyecto.

## Contrato de integración con Track B (Budget/Project Control)

`StockLedgerEntry` con `movement_type='ISSUE'`,
`source_type='project_issue'` y `project_id` no nulo es la única fuente de
actuales de proyecto de este track. La query certificada
`inventory_repository.project_actuals_by_project(db, company_id)` devuelve
`Decimal(quantity * unit_cost)` por `project_id`; una transferencia de
almacén nunca aporta actual porque solamente relocaliza stock.

Track B consume esos totales para el componente de materiales de
`budget_service.compute_summary` y los puede mapear al WBS correspondiente.
Este ledger no crea efectivo, pagos ni caja de proyecto: esas capacidades
siguen siendo de los tracks de AP/Treasury.

## Permisos

Resources: `inventory.item`, `inventory.warehouse`, `inventory.stock`
(acciones `read`/`move`), `inventory.physical_count` (`create`/`approve`).
`Warehouse Manager` tiene el grant más amplio (crea ítems/almacenes,
mueve stock, aprueba conteos); `Buyer`/`Procurement Manager` solo lectura;
`Auditor` solo lectura (ANY).

## Pendiente / deuda intencional

- `RETURN` (devolución a proveedor) no tiene service function dedicada —
  se puede modelar como un `_issue` con `movement_type="RETURN"` cuando se
  necesite; el modelo ya soporta el valor.
- No hay endpoint de "stock ledger history" (listar todos los movimientos
  de un ítem/almacén) — solo la posición actual
  (`GET /inventory/stock/position`). Agregar cuando el reporte "Stock
  Ledger" (orden maestra §102, Inventory reports) se construya.
