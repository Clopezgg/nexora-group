# Enterprise Resources — Track D

Fixed Assets/Depreciación, Equipment/Fuel/Maintenance y Workforce/Time
(orden maestra §62-66). Documents/Site/Quality (§62/§66, bloque "Documents /
Evidence / Progress / Site / Quality" en `docs/MASTER_PLAN.md`) **NOT_STARTED**
en este track — ver `docs/PROGRESS.md` y `docs/REQUIREMENTS_TRACEABILITY.md`
para el estado honesto, no se reporta como implementado.

## Fixed Assets / Depreciación straight-line (INV-AST-001)

`FixedAsset` reusa el mismo patrón de atribución que AP (`scope` +
`project_id` + `cost_center_id`, ver `app/models/ap.py`) — el activo nunca
custodia dinero, solo atribuye costo de depreciación (CLAUDE.md §1/§7).
Cada activo declara sus propias cuentas contables
(`depreciation_expense_account_id`/`accumulated_depreciation_account_id`),
nunca hardcodeadas en el servicio.

Depreciación:

```
monthly_amount = (cost - salvage_value) / useful_life_months
```

Redondeado a 2 decimales (`ROUND_HALF_UP`). `asset_service.generate_depreciation_entry`
pasa siempre por `posting_service.post_manual` (documento tipo `DEP`,
débito a `depreciation_expense_account_id`, crédito a
`accumulated_depreciation_account_id`), nunca construye `JournalLine` a
mano.

**INV-AST-001**: un mismo `(asset_id, period_start)` nunca genera dos
`DepreciationEntry`/postings DEP. Doble garantía:
- Servicio: `asset_repository.get_depreciation_entry_for_period` antes de
  crear la entry (mensaje de dominio claro, `NXR-ASSET-002`, HTTP 409).
- DB: `uq_depreciation_entries_asset_period` (constraint real de
  PostgreSQL) — la garantía última bajo escritura concurrente.

Un activo `DISPOSED`/`RETIRED` es terminal: no admite más depreciación ni
más transiciones de estado (`NXR-ASSET-001`).

## Equipment / Fuel / Maintenance

`Equipment.asset_id` es opcional (no todo equipo se capitaliza como Fixed
Asset). `FuelLog` reusa OperationScope pero solo admite `GENERAL`/`PROJECT`
(nunca `CENTRAL` — un consumo físico de combustible no es un gasto de
holding). `total_cost` se calcula SIEMPRE server-side
(`quantity * unit_cost`), nunca se acepta del cliente.

**Deuda intencional documentada**: `FuelLog`/`MaintenanceOrder.parts_cost`/
`labor_cost` no pasan por el Posting Engine todavía — a diferencia de
`FixedAsset`, no existe hoy un mecanismo para que cada `Equipment`/company
declare su propia cuenta de gasto de combustible/mantenimiento. El costo
queda registrado con `project_id`/`scope` explícitos, listo para que un
track de Hardening posterior conecte `posting_service.post_manual` con esos
datos (mismo contrato documentado por Track C en `docs/INVENTORY.md`
INV-INV-002 para `issue_to_project`).

**INV-EQP-001**: un `MaintenanceOrder` `CLOSED`/`CANCELLED` es terminal.
`equipment_service.update_maintenance_order` rechaza CUALQUIER mutación
(incluso volver a "cerrarlo") antes de tocar un solo campo —
`ImmutableMaintenanceOrderError`, `NXR-EQUIPMENT-001`, HTTP 409. Crear una
`MaintenanceOrder` mueve el `Equipment` a `UNDER_MAINTENANCE`; cerrarla lo
regresa a `AVAILABLE` si seguía en ese estado.

## Workforce / Time (INV-WFC-001)

`TimeEntry` captura `hourly_rate` como snapshot al momento de someter la
hora (no una referencia viva a `Worker.standard_hourly_rate`, para que un
cambio de tarifa futuro no reescriba el costo histórico). `scope`/
`project_id` reusan el mismo patrón CENTRAL/GENERAL/PROJECT que AP/Assets.

**INV-WFC-001**: `labor_cost` se calcula SIEMPRE en el servidor al aprobar:

```
labor_cost = hourly_rate * approved_hours
```

Nunca se acepta como input del cliente (CLAUDE.md: no hardcoded financial
data). `approved_hours` puede diferir de `hours_worked` (el aprobador
ajusta), y el costo usa siempre las horas aprobadas. Un `TimeEntry` solo
puede aprobarse/rechazarse una vez (`SUBMITTED` → `APPROVED`/`REJECTED`,
decisión terminal, `NXR-WORKFORCE-001` si se reintenta).

**Deuda intencional documentada**: el pago real del trabajador (nómina) y
la contabilización del costo de mano de obra hacia el Posting Engine
quedan fuera de alcance de este track — mismo patrón de "costo registrado,
posting pendiente" que Fuel/Maintenance arriba. `labor_cost` queda
disponible para que Project Control (Track B) o un track de Hardening lo
sume al costo real del proyecto.

## RBAC

`Equipment Manager` (custodia física de activos/equipos/mantenimiento) y
`Operations User` (combustible/órdenes de mantenimiento/horas de campo,
sin permisos de aprobación) ya estaban pre-sembrados en `ROLE_NAMES`
(`app/models/role.py`) anticipando este track — se les otorgaron permisos
en `permission_repository.py` en vez de inventar roles nuevos.
`asset.depreciation` (contabilización) es exclusivo de
`Finance Manager`/`Accountant`/`Administrator`/`Auditor`, nunca de
`Equipment Manager` (custodia física ≠ contabilización).

## Frontend

Implementado para Assets (`FixedAssetsPage`) y Equipment/Maintenance
(`EquipmentPage`). Workforce/Time backend-only en este corte — ver
`docs/PROGRESS.md`.
