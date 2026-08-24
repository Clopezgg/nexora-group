# Budget / Controlling — contrato (Track B)

## Versionado

- `Budget.version = BASELINE`: se crea **una sola vez** por proyecto
  (`budget_service.create_baseline`, rechaza un segundo intento con
  `BudgetBaselineExistsError` / `NXR-BUDGET-001`). Sus `BudgetLine` nunca se
  editan ni eliminan.
- `Budget.version = REVISED`: se crea automáticamente cuando una
  `ChangeOrder` en estado `SUBMITTED` se aprueba
  (`budget_service.approve_change_order`). Copia las líneas del budget
  activo anterior y agrega una línea adicional con el
  `budget_change_amount` de la ChangeOrder (puede ser negativo). El budget
  anterior pasa a `status=SUPERSEDED` — **nunca se borra**, queda como
  historial completo y consultable vía `GET /api/projects/{id}/budgets`
  (todas las versiones) vs `.../budgets/active` (solo la vigente).

**Simplificación deliberada**: la ChangeOrder tiene un monto de impacto
agregado, no un desglose línea por línea del presupuesto completo. Si en el
futuro se necesita reasignar presupuesto entre WBS/categorías dentro de una
misma ChangeOrder, hay que extender `ChangeOrder` con líneas propias — hoy
no existe esa necesidad real, así que no se construyó especulativamente.

## Métricas (`GET /api/projects/{id}/budgets/summary`)

| Métrica | Fuente real hoy | Fuente cuando aterricen los tracks dueños |
|---|---|---|
| `AUTHORIZED` | `SUM(BudgetLine.authorized_amount)` del budget activo | (ya es real) |
| `COMMITTED` | `0` (stub honesto) | Track C (Procurement) — Purchase Orders aprobadas y no facturadas |
| `ACCRUED` | `0` (stub honesto) | Track A (AP) — Supplier Invoices no pagadas |
| `PAID` | `0` (stub honesto) | Track A (AP) — pagos ejecutados |
| `AVAILABLE` | `AUTHORIZED - COMMITTED - ACCRUED` | mismo cálculo, con datos reales |

**Contrato para el coordinador al integrar Track A/C**: `budget_service.
compute_summary` es el ÚNICO lugar que calcula estos números — cuando las
tablas de AP/Procurement existan, sustituir las líneas marcadas
`# Stubs honestos` por queries reales contra esas tablas, sin cambiar la
forma de `BudgetSummary` (así ningún consumidor de la API se rompe).

## Forecast (`GET /api/projects/{id}/forecast`)

`BAC = AUTHORIZED`. `PV`/`EV` se derivan del `ProgressRecord` más reciente
(`planned_percent`/`actual_percent` × BAC) — es una simplificación honesta
porque todavía no existe un motor de scheduling con distribución de $ por
fecha. `AC = ACCRUED + PAID` (0 hasta Track A). `CPI/SPI/ETC/EAC/VAC` son
`None` cuando no son calculables (p.ej. sin `ProgressRecord`, o `AC=0` para
`CPI`) — **nunca 0 falso ni valor inventado**, ver orden maestra §42 y
`tests/test_project_control.py::test_forecast_without_progress_returns_none_not_fake_values`.

## Change Orders

Lifecycle: `DRAFT → SUBMITTED → APPROVED` (o `REJECTED`/`CANCELLED`).
`IMPLEMENTED` queda como estado disponible para cuando el track de
ejecución de obra lo necesite marcar — este track no lo usa todavía.
Solo se puede aprobar desde `SUBMITTED` (`InvalidChangeOrderStateError` /
`NXR-PROJECT-001` en cualquier otro caso).
