# Procurement — Track C (Supply Chain)

Flujo end-to-end (orden maestra §44-51): **PR → approval → RFQ → Supplier
Quotations → Bid Comparison (manual, sin auto-aprobación por IA) → PO →
Goods Receipt / Service Entry → Three-Way Match**. Cada etapa es un
documento independiente — nunca un "mega documento".

## Entidades (`app/models/procurement.py`)

`PurchaseRequisition` (+`PurchaseRequisitionLine`), `RequestForQuotation`
(+`RfqSupplier`), `SupplierQuotation` (+`SupplierQuotationLine`),
`PurchaseOrder` (+`PurchaseOrderLine`, con `quantity_received` acumulado),
`GoodsReceipt` (+`GoodsReceiptLine`), `ServiceEntry`,
`ThreeWayMatchResult`.

Numeración (vía `numbering_service`, la misma infraestructura
concurrency-safe de Track 1): `PR-YYYY-NNNNNN`, `RFQ-YYYY-NNNNNN`,
`PO-YYYY-NNNNNN`, `GR-YYYY-NNNNNN`, `SIN-YYYY-NNNNNN` (Service Entry).

## Servicio (`app/services/procurement_service.py`)

Orquesta cada transición de estado (`PurchaseRequisition`: `SUBMITTED →
APPROVED`; `PurchaseOrder`: `DRAFT → APPROVED → SENT →
PARTIALLY_RECEIVED/RECEIVED`) y llama a `inventory_service.receive_stock`
en cada línea de Goods Receipt con `item_id` — nunca inserta en el Stock
Ledger a mano.

## INV-PROC-001 — Three-Way Match

`run_three_way_match()` compara:
- `ordered_amount` = suma de `PurchaseOrderLine.quantity * unit_price +
  tax_amount`.
- `received_quantity` = suma de `PurchaseOrderLine.quantity_received`
  (agregado real de todos los Goods Receipt de esa PO).
- `supplier_invoice_amount` / `supplier_invoice_quantity`: parámetros de
  entrada del caller.

Si la variación porcentual excede la tolerancia configurada
(`amount_tolerance_pct` / `quantity_tolerance_pct`, default 0%), el
resultado queda `EXCEPTION` con el detalle en `exceptions` (JSONB) — **el
registro siempre se persiste**, tanto si hay match como si hay excepción;
nunca se descarta una diferencia silenciosamente.

## Contrato de integración con Track A (Accounts Payable)

Track A construye `SupplierInvoice` con un **placeholder de Supplier**
(por id/nombre libre) porque este track corría en paralelo. Al integrar:

1. `SupplierInvoice.supplier_id` de Track A debe apuntar a
   `procurement.suppliers.id` (esta tabla, la real).
2. `run_three_way_match(purchase_order_id, supplier_invoice_id,
   supplier_invoice_amount, supplier_invoice_quantity, ...)` ya acepta
   `supplier_invoice_id` como columna libre (`UUID` sin FK todavía) — al
   integrar, agregar la FK real a `supplier_invoices.id` una vez que esa
   tabla exista en la rama fusionada (migración de ajuste, no de
   reconstrucción).
3. El pago de la `SupplierInvoice` (Track A) es el que finalmente impacta
   Treasury/GL — este track no contabiliza el three-way match en sí mismo,
   solo lo certifica.

## Contrato de integración con Track B (Budget/Project Control)

`PurchaseOrder.project_id` (cuando la PO es atribuible a un proyecto) es
el punto de entrada para que `budget_service.compute_summary` (Track B)
obtenga `COMMITTED`. La fuente certificada es
`procurement_repository.project_commitment_total(db, company_id, project_id)`,
que devuelve el total `Decimal` del proyecto solicitado para POs en
`APPROVED/SENT/PARTIALLY_RECEIVED/RECEIVED`; una PO `DRAFT` no aporta nada.
Hasta que exista una política FX fechada y autoritativa, una PO ligada a
proyecto solo puede aprobarse si su `currency_code` coincide con
`Company.functional_currency_code`; el rechazo explícito usa
`NXR-PROCUREMENT-002`. La agregación se filtra por `project_id`, conserva la
moneda en su `GROUP BY` y repite la validación para bloquear datos aprobados
preexistentes solo en su proyecto propietario; nunca los omite, suma importes
nominales incompatibles ni contamina otro proyecto de la company.

Goods Receipt y Service Entry registran avance físico/documental, pero no
crean por sí mismos actual de proyecto ni efectivo. Los actuals de material
de este track se derivan exclusivamente de Project Issues posteados en el
Stock Ledger; ver `docs/INVENTORY.md`. Track B consume ambos agregados sin
que los servicios se importen entre sí, evitando una dependencia circular y
sin almacenar efectivo en Project.

## Permisos

Resources: `procurement.supplier`, `procurement.contract`,
`procurement.requisition`, `procurement.rfq`, `procurement.quotation`,
`procurement.purchase_order`, `procurement.goods_receipt`,
`procurement.service_entry`, `procurement.three_way_match`. Roles con
grants: `Administrator` (ANY, automático), `Procurement Manager`, `Buyer`,
`Warehouse Manager` (solo lo relevante a recepciones/inventario),
`Auditor` (solo lectura, ANY).

## Pendiente / deuda intencional

- `PurchaseOrderFromQuotationRequest` no valida que la cotización
  pertenezca al RFQ correcto de la company indicada (se confía en que el
  caller ya hizo Bid Comparison correctamente) — reforzar cuando se
  construya la pantalla de comparación real.
- No hay endpoint de "Bid Comparison" dedicado que calcule el cuadro
  comparativo — hoy se calcula ad-hoc con `quotation_total()` por
  cotización; construir un endpoint agregado si el frontend de
  comparación se prioriza.
- Supplier Performance permanece `NOT_STARTED`: faltan datos históricos
  suficientes para métricas reales de entrega, calidad y variación de
  precio. Supplier Contracts/Subcontracts permanecen `IN_PROGRESS`: existe
  el modelo y API base, pero faltan pruebas dedicadas, UI y una distinción
  formal para reporting de subcontratos.
