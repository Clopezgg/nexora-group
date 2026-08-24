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
| `COMMITTED` | Suma de Purchase Orders aprobadas del proyecto en la moneda funcional de su company (Track C) | (ya es real) |
| `ACCRUED` | `0` (stub honesto) | Track A (AP) — Supplier Invoices no pagadas |
| `PAID` | `0` (stub honesto) | Track A (AP) — pagos ejecutados |
| `AVAILABLE` | `AUTHORIZED - COMMITTED - ACCRUED` | mismo cálculo, con datos reales |

`budget_service.compute_summary` es el ÚNICO lugar que calcula estos
números. Track C se integra mediante `procurement_repository.
project_commitments_by_project`; cuando aterrice AP/Track A, ACCRUED y PAID
deben conectarse a sus fuentes reales sin cambiar la forma de
`BudgetSummary`. Sin una política FX autoritativa, una PO de proyecto en una
moneda distinta de `Company.functional_currency_code` se rechaza al aprobar
y también durante la agregación defensiva (`NXR-PROCUREMENT-002`); nunca se
convierte, omite ni resta como si fuera moneda funcional.

## Forecast (`GET /api/projects/{id}/forecast`)

`BAC = AUTHORIZED`. `PV`/`EV` se derivan del `ProgressRecord` más reciente
(`planned_percent`/`actual_percent` × BAC) — es una simplificación honesta
porque todavía no existe un motor de scheduling con distribución de $ por
fecha. `AC` es el costo de emisiones de inventario posteadas al proyecto,
obtenido de `inventory_repository.project_actuals_by_project`; no se
reclasifica ese consumo como `ACCRUED`, `PAID` ni efectivo.
`CPI/SPI/ETC/EAC/VAC` son
`None` cuando no son calculables (p.ej. sin `ProgressRecord`, o `AC=0` para
`CPI`) — **nunca 0 falso ni valor inventado**, ver orden maestra §42 y
`tests/test_project_control.py::test_forecast_without_progress_returns_none_not_fake_values`.

## Change Orders

Lifecycle: `DRAFT → SUBMITTED → APPROVED` (o `REJECTED`/`CANCELLED`).
`IMPLEMENTED` queda como estado disponible para cuando el track de
ejecución de obra lo necesite marcar — este track no lo usa todavía.
Solo se puede aprobar desde `SUBMITTED` (`InvalidChangeOrderStateError` /
`NXR-PROJECT-001` en cualquier otro caso).
