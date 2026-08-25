# NEXORA GROUP — Requirements Traceability Matrix

Cada capacidad de la ORDEN MAESTRA (sección "Definición de NEXORA 100%")
tiene un `NXR-REQ-XXXX` estable. Un requisito es `VERIFIED` únicamente
cuando **todas** las piezas aplicables existen: dominio, base de datos,
backend, API, frontend (si aplica), autorización, audit, tests — con
evidencia real (comando/test/commit), nunca por scaffold, TODO, mock o
placeholder.

**Leyenda de piezas** (columna "Trazabilidad", orden fijo:
`Dom·DB·BE·API·FE·Perm·Audit·Test·E2E`):
✅ implementado y verificado · 🔶 parcial/en progreso · ⬜ no iniciado ·
➖ no aplica a este requisito.

**Estados:** `NOT_STARTED` · `IN_PROGRESS` · `IMPLEMENTED` ·
`VERIFIED` · `BLOCKED_EXTERNAL`.

Última actualización: Track D (Enterprise Resources — Assets/Equipment/
Maintenance/Workforce) construido en `track/d-enterprise-resources` sobre
la integración completa de Track 1+F+B+C+A, pendiente de integración
coordinada. Documents/Site/Quality (bloque CONSTRUCTION CONTROL,
NXR-REQ-0077-0086) sigue `NOT_STARTED`/`IN_PROGRESS` sin cambios — Track D
priorizó completar Assets y Equipment/Maintenance honestamente en vez de
tocar las cuatro áreas superficialmente (ver task-5-report.md).

## CORE

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0001 | Core platform | 🔶·🔶·🔶·🔶·🔶·➖·➖·🔶·⬜ | IN_PROGRESS | `62c56eb` monorepo, settings, healthz/readyz (sin cambios en este track) |
| NXR-REQ-0002 | Multi-company | ✅·✅·✅·✅·⬜·➖·⬜·✅·⬜ | IMPLEMENTED | Track 1: Company con code/legal_name/functional_currency/country/fiscal_id, ChartOfAccount 1:1 por company, API `/api/master-data/companies`; falta UI (Track F) |
| NXR-REQ-0003 | Master Data | ✅·✅·🔶·🔶·⬜·➖·⬜·✅·⬜ | IMPLEMENTED | Track 1: BusinessUnit, FiscalYear/FiscalPeriod, Currency/ExchangeRate, TaxCode, ChartOfAccount/Account, CostCenter/EconomicCategory, DocumentType, NumberSequence, ApprovalPolicy(skeleton). API solo para companies/accounts; el resto solo tiene repositorio/modelo. Falta UI |
| NXR-REQ-0004 | Fiscal periods | ✅·✅·✅·⬜·⬜·➖·⬜·✅·⬜ | IMPLEMENTED | Track 1: FiscalYear/FiscalPeriod OPEN/SOFT_CLOSED/CLOSED, enforcement real en `posting_service` (INV-ACC-003); sin API dedicada todavía |
| NXR-REQ-0005 | Currency / exchange rates | ✅·✅·✅·⬜·⬜·➖·⬜·🔶·⬜ | IMPLEMENTED | Track 1: Currency/ExchangeRate + seed HNL/USD; sin API ni test de conversión FX todavía |
| NXR-REQ-0006 | Tax architecture | ✅·✅·⬜·⬜·⬜·➖·⬜·⬜·⬜ | IN_PROGRESS | Track 1: TaxCode + TaxLine (modelo, usado por posting_service.post_manual vía tax_lines) — sin servicio de cálculo de impuestos ni API |
| NXR-REQ-0007 | Number sequences (concurrency-safe) | ✅·✅·✅·➖·➖·➖·➖·✅·⬜ | IMPLEMENTED | Track 1: `numbering_service.next_document_number` con `SELECT...FOR UPDATE`, nunca MAX()+1; probado indirectamente vía todos los tests de posting (documentNumber JRN-YYYY-NNNNNN) |

## IDENTITY

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0008 | Authentication | ➖·✅·✅·✅·✅·➖·⬜·✅·⬜ | IN_PROGRESS | Sin cambios en este track — sigue faltando CSRF/rate-limit/lockout |
| NXR-REQ-0009 | Sessions (PostgreSQL) | ➖·✅·✅·✅·➖·➖·⬜·✅·⬜ | IN_PROGRESS | Sin cambios en este track |
| NXR-REQ-0010 | RBAC | ✅·✅·✅·➖·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | Track 1: 14 roles (§87), motor central `Permission`/`RolePermission` con `company_scope`, `require_permission`/`assert_company_access` autoritativos en backend; matriz de permisos cubre solo `core.company`/`accounting.*` (lo que existe hoy); falta UI para administrar roles/accesos |
| NXR-REQ-0011 | Permission scopes (resource/action/company/project) | ✅·✅·✅·➖·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | Track 1: `company_scope` (ANY/OWN) aplicado y probado (INV-COMP-001, 4 tests); `project_scope` existe en el modelo pero **no se aplica aún** en ningún endpoint (documentado en docs/RBAC.md) |
| NXR-REQ-0012 | User / ActiveUIContext | ✅·✅·✅·✅·✅·➖·⬜·✅·⬜ | IMPLEMENTED | Track 1 agregó `test_active_context_independence.py` probando INV-CTX-001 (operación CENTRAL no muta el contexto activo) |

## FINANCE

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0013 | General Ledger | ✅·✅·✅·✅·⬜·➖·⬜·✅·⬜ | IMPLEMENTED | Track 1: `AccountingDocument`/`JournalLine`, API `/api/accounting/journal-entries` (crear/leer/revertir); falta pantalla de consulta GL (Track F) y reportes (Track G) |
| NXR-REQ-0014 | Double-entry (debit=credit invariant) | ✅·✅·✅·➖·➖·➖·➖·✅·➖ | IMPLEMENTED | INV-ACC-001 con test real, ver docs/ACCOUNTING.md |
| NXR-REQ-0015 | Posting engine (PostingRule/PostingService) | ✅·✅·✅·➖·➖·➖·➖·✅·➖ | IMPLEMENTED | `posting_service.post_manual`/`reverse_document`, `PostingRule` (modelo, sin resolver automático todavía — ver docs/ACCOUNTING.md); valida centralmente que Project, cuentas y dimensiones pertenezcan a la company |
| NXR-REQ-0016 | Financial statements (TB, GL, BS, P&L, Cash Flow) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track G (Reporting), sobre los datos que ya deja el GL de este track |
| NXR-REQ-0017 | Treasury (accounts, position) | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: cuentas BANK/CASH/OTHER, posición derivada del GL, API y pantalla reales; ownership por company y relación TreasuryAccount↔GL uno-a-uno |
| NXR-REQ-0018 | Remittances (scope=CENTRAL) | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: remesa CENTRAL cash-in, posting atómico e idempotente y formulario Treasury |
| NXR-REQ-0019 | Transfers (bank/cash) | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: transferencia entre activos de Treasury, sin Revenue/Expense, idempotente; FX entre cuentas diferido explícitamente |
| NXR-REQ-0020 | Cash (closing, position) | ✅·✅·✅·✅·⬜·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: cierre de caja DRAFT→APPROVED con ajuste atómico/idempotente; sin pantalla específica de cierres |
| NXR-REQ-0021 | Bank reconciliation | ✅·✅·✅·✅·⬜·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: statement/lines append-only, matches acumulativos con `FOR UPDATE`; valida company, GL, signo, capacidad/asignación del documento y transiciones; sin UI específica |
| NXR-REQ-0022 | Fund restrictions | ✅·✅·✅·✅·⬜·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: restricción etiqueta uso sin transferir propiedad del efectivo al Project; validación company/project |
| NXR-REQ-0023 | Accounts Payable | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: invoices/accrual/aprobación/pagos parciales, GET persistido por company, UI y pagos idempotentes |
| NXR-REQ-0024 | Accounts Receivable | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track A retiene AR como Financial Core: invoices/receipts, GET persistido, UI e idempotencia. `CustomerInvoice.customer_id` es ahora FK real a `Customer` (Track E, antes texto libre) — Track E posee el workflow comercial y llama `ar_service.create_customer_invoice` directo, nunca duplica receivables (ver NXR-REQ-0066) |
| NXR-REQ-0025 | Corrections (posted docs) | 🔶·✅·✅·➖·➖·➖·⬜·✅·➖ | IN_PROGRESS | Mecanismo de reversal cubre el caso general (INV-ACC-002); falta un flujo de "correction" distinto al reversal simple si algún dominio lo necesita — dueño: track que lo requiera |
| NXR-REQ-0026 | Annulments (reversal, no delete) | ✅·✅·✅·✅·⬜·➖·⬜·✅·⬜ | IMPLEMENTED | `posting_service.reverse_document`, endpoint `POST /api/accounting/journal-entries/{id}/reverse`, documento tipo `ANU`; falta UI |
| NXR-REQ-0027 | Idempotency (Idempotency-Key) | ✅·✅·✅·✅·➖·➖·⬜·✅·➖ | IMPLEMENTED | Track A consume el header persistido en remesas, transferencias, gastos, cierres, pagos y cobros; UI genera una key por intención y la conserva en variables de retry; posting + operación + resultado se confirman en una transacción |

## PROJECT CONTROL

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0028 | Projects | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Track B: modelo completo (§37), `GET/POST /api/projects`, `ProjectsPage` real (crea compañía/proyecto), test `test_project_has_no_money_column` (INV-TRE-002) |
| NXR-REQ-0029 | WBS (jerárquico) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `WBSNode` con parent/level, `WBSPage` real, test de jerarquía 2 niveles |
| NXR-REQ-0030 | Planning (tasks/milestones/deps) | ✅·✅·✅·✅·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | `Task`/`Milestone` + API; sin pantalla dedicada todavía (`/proyectos/planeacion` sigue en EmptyState del bootstrap) |
| NXR-REQ-0031 | Budgets | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `Budget`/`BudgetLine`, `budget_service.compute_summary`, `BudgetPage` con AUTHORIZED/COMMITTED/ACCRUED/PAID/AVAILABLE reales |
| NXR-REQ-0032 | Budget versions (baseline/revised) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | BASELINE inmutable (`NXR-BUDGET-001` si se repite) y obligado a moneda funcional (`NXR-BUDGET-002` antes de persistir); REVISED generado por ChangeOrder aprobada, historial preservado |
| NXR-REQ-0033 | Commitments | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Track C integrado: POs aprobadas en moneda funcional alimentan el summary del proyecto solicitado; draft, moneda incompatible y aislamiento entre proyectos cubiertos por integración |
| NXR-REQ-0034 | Accruals | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A (AP) — mismo contrato de integración |
| NXR-REQ-0035 | Payments (project attribution) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A (AP) |
| NXR-REQ-0036 | Forecast (BAC/PV/EV/AC/CPI/SPI/ETC/EAC/VAC) | ✅·➖·✅·✅·✅·➖·➖·✅·⬜ | IMPLEMENTED | `forecast_service.compute_forecast`; valores no calculables devuelven `null` real, nunca 0 falso — test dedicado |
| NXR-REQ-0037 | Earned Value | ✅·➖·✅·✅·✅·➖·➖·✅·⬜ | IMPLEMENTED | PV/EV derivados del `ProgressRecord` más reciente contra BAC — simplificación documentada en docs/BUDGET_CONTROLLING.md |
| NXR-REQ-0038 | Change Orders | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Lifecycle DRAFT→SUBMITTED→APPROVED real, `ChangeOrdersPage`, test de transición inválida (`NXR-PROJECT-001`) |
| NXR-REQ-0039 | Progress (ProgressRecord) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `ProgressRecord` (planned%/actual%/evidence_ref libre), `ProgressPage`, alimenta Forecast |

## PROCUREMENT

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0040 | Purchase Requisition | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Track C: `PurchaseRequisition`+líneas, `RequisitionsPage`, numeración `PR-YYYY-NNNNNN`; falta permiso granular por prioridad/monto |
| NXR-REQ-0041 | Approval workflow (PR) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `approve_requisition` (SUBMITTED→APPROVED), botón "Aprobar" en UI, test de doble-aprobación rechazada (`NXR-PROCUREMENT-001`) |
| NXR-REQ-0042 | RFQ | ✅·✅·✅·✅·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | `RequestForQuotation`+`RfqSupplier` (multi-supplier), numeración `RFQ-YYYY-NNNNNN`; sin pantalla dedicada (backend-only, como se acordó en el alcance) |
| NXR-REQ-0043 | Supplier Quotations | ✅·✅·✅·✅·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | `SupplierQuotation`+líneas, `quotation_total()`; sin pantalla dedicada |
| NXR-REQ-0044 | Bid Comparison | 🔶·➖·✅·✅·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | `quotation_total()` por cotización permite comparar manualmente; no hay endpoint agregado de comparación ni pantalla — ver `docs/PROCUREMENT.md` pendiente |
| NXR-REQ-0045 | Purchase Order | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Lifecycle completo `DRAFT→APPROVED→SENT→PARTIALLY_RECEIVED/RECEIVED`; PO de proyecto rechaza moneda no funcional (`NXR-PROCUREMENT-002`); UI, numeración y tests reales |
| NXR-REQ-0046 | Goods Receipt | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Recepción parcial y completa, actualiza `quantity_received` + status de PO + Stock Ledger real, `GoodsReceiptsPage`, test de sobre-recepción rechazada |
| NXR-REQ-0047 | Service Entry | ✅·✅·✅·✅·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | `ServiceEntry` con período/avance/valor aceptado, numeración `SEN-YYYY-NNNNNN`; sin pantalla dedicada (no estaba en el alcance de frontend acordado) |
| NXR-REQ-0048 | Three-Way Match | ✅·✅·✅·✅·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | `run_three_way_match` (INV-PROC-001): diferencias fuera de tolerancia nunca se descartan, siempre quedan en `exceptions`; test MATCHED y EXCEPTION reales |

## SUPPLY CHAIN

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0049 | Items | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `Item` (SKU único por company, tipo, UOM), `InventoryPage` real |
| NXR-REQ-0050 | Warehouses | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `Warehouse` (company + project opcional), `WarehousesPage` real |
| NXR-REQ-0051 | Stock Ledger (append-only) | ✅·✅·✅·✅·➖·⬜·⬜·✅·➖ | IMPLEMENTED | `StockLedgerEntry`, nunca UPDATE/DELETE, moving average real, test de doble receipt calculando promedio correcto |
| NXR-REQ-0052 | Inventory Transfers | ✅·✅·✅·✅·➖·⬜·⬜·✅·➖ | IMPLEMENTED | `transfer_stock` (par RECEIPT/TRANSFER atómico), test real de movimiento entre almacenes |
| NXR-REQ-0053 | Project Issues | ✅·✅·✅·✅·➖·⬜·⬜·✅·➖ | IMPLEMENTED | `issue_to_project` (INV-INV-002), test real de reducción de stock con `project_id`; posting contable del consumo queda documentado como contrato pendiente en `docs/INVENTORY.md` |
| NXR-REQ-0054 | Returns | 🔶·✅·⬜·⬜·⬜·⬜·⬜·⬜·➖ | NOT_STARTED | `movement_type="RETURN"` existe en el modelo, sin service function ni endpoint dedicado — documentado como deuda intencional en `docs/INVENTORY.md` |
| NXR-REQ-0055 | Physical Counts | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `PhysicalCount`+líneas, `apply_physical_count` genera ADJUSTMENT real por variance, test end-to-end (crear conteo → aprobar → verificar posición) |
| NXR-REQ-0056 | Valuation (moving average) | ✅·✅·✅·➖·➖·➖·➖·✅·➖ | IMPLEMENTED | Fórmula de costo promedio ponderado en `inventory_service`, test con dos recepciones a costos distintos verificando el promedio exacto |

## SUPPLIERS / CONTRACTS

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0057 | Supplier Master | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Track C: `Supplier` (legal_name/trade_name/tax_id/banking_details JSONB, distinto de `TreasuryAccount`), `SuppliersPage` real |
| NXR-REQ-0058 | Supplier Performance | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Sin datos históricos suficientes todavía para calcular métricas reales (delivery/quality/price variance) sin fabricarlas — deferred hasta tener volumen de PO/GR real |
| NXR-REQ-0059 | Supplier Contracts | ✅·✅·✅·✅·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | `SupplierContract` (value/currency/advance/retention %), repositorio + endpoint create/list; sin pantalla ni test dedicado todavía |
| NXR-REQ-0060 | Subcontracts | 🔶·✅·✅·✅·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | Mismo modelo `SupplierContract` cubre subcontratos (no hay campo distintivo `is_subcontract` — se distingue por convención de scope_description hoy; formalizar si se necesita reporting separado) |

## COMMERCIAL

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0061 | Leads | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track E: `Lead` (company/contact/source/status), `POST/GET /api/crm/leads`, permiso `crm.lead`, `LeadsPage` (crear + convertir), tests company isolation incluidos |
| NXR-REQ-0062 | Opportunities | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track E: `Opportunity` se crea SIEMPRE junto al `Customer` al convertir un `Lead` (`crm_service.convert_lead`, nunca manual); `GET /api/crm/opportunities`, permiso `crm.opportunity`, `OpportunitiesPage` (solo lectura, por diseño) |
| NXR-REQ-0063 | Customers | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track E: entidad `Customer` real (antes texto libre en `CustomerInvoice.customer_name`, ver NXR-REQ-0024); `POST/GET /api/crm/customers`, permiso `crm.customer`, `CustomersPage`. Conversión de lead idempotente verificada (RED/GREEN): convertir el mismo lead dos veces devuelve el mismo `Customer` y crea exactamente una fila |
| NXR-REQ-0064 | Sales Quotations | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track E: `Quotation` (DRAFT→SENT→ACCEPTED/REJECTED), `customer_id` debe coincidir con el de su `Opportunity` (validado en servicio); `POST/GET/accept /api/crm/quotations`, permiso `crm.quotation`, `QuotationsPage` |
| NXR-REQ-0065 | Sales Contracts | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track E: solo una `Quotation` ACCEPTED convierte a `SalesContract` (`NXR-CRM-001` si no), preserva amount/company/customer/project tal cual; `scope` (CENTRAL/GENERAL/PROJECT) derivado de `project_id`; `POST /api/crm/quotations/{id}/convert`, `SalesContractsPage`. RED/GREEN real: conversión rechazada antes de ACCEPTED, aceptada después |
| NXR-REQ-0066 | Customer Invoices (desde Commercial) | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track E factura un `SalesContract` llamando DIRECTO a `ar_service.create_customer_invoice` (Track A, `commit=False` para composición atómica con el cambio de estado del contrato) — NUNCA una segunda tabla de receivables. `POST /api/crm/sales-contracts/{id}/bill` crea exactamente una `CustomerInvoice` real y rechaza un segundo intento de facturar el mismo contrato (`NXR-CRM-001`). El motor de AR en sí (invoices/receipts/aprobación) sigue siendo Track A — ver NXR-REQ-0024 |
| NXR-REQ-0067 | Collections (desde Commercial) | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | El cobro de una factura AR generada desde un `SalesContract` usa el mismo `POST /api/ar/customer-invoices/{id}/receipts` de Track A (NXR-REQ-0024) — Track E no duplica esta pieza; verificado que facturar un contrato NO produce ningún movimiento de tesorería hasta que se cobra vía AR |

## RESOURCES

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0068 | Fixed Assets | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track D: `FixedAsset` (scope/project/cost_center + cuentas de depreciación propias, `ck_fixed_assets_*`), `FixedAssetsPage`, permisos `asset.fixed_asset`, 7 tests (incluye constraint DB directo) |
| NXR-REQ-0069 | Depreciation (straight-line) | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track D: `(cost-salvage)/useful_life_months`, posting DEP real vía `posting_service.post_manual` (nunca hardcodeado), INV-AST-001 doble garantía (service + `uq_depreciation_entries_asset_period`), RED/GREEN evidence real (ver task-5-report.md) |
| NXR-REQ-0070 | Equipment | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track D: `Equipment` (asset_id opcional), `EquipmentPage` tab "Equipos", permisos `equipment.equipment` |
| NXR-REQ-0071 | Fuel log | ✅·✅·✅·✅·✅·✅·⬜·✅·⬜ | IMPLEMENTED | Track D: `FuelLog` (total_cost calculado server-side, nunca del cliente), scope GENERAL/PROJECT con `ck_fuel_logs_operation_scope` (INV real a nivel DB, test directo), `EquipmentPage` tab "Combustible" |
| NXR-REQ-0072 | Maintenance (plan/order) | ✅·✅·✅·✅·🔶·✅·⬜·✅·⬜ | IMPLEMENTED | Track D: `MaintenancePlan`/`MaintenanceOrder`, INV-EQP-001 (CLOSED/CANCELLED inmutable, RED/GREEN evidence real), `EquipmentPage` tab "Mantenimiento" cubre creación/cierre de órdenes; falta UI de `MaintenancePlan` (API existe, sin pantalla dedicada) |
| NXR-REQ-0073 | Employees | ✅·✅·✅·✅·⬜·✅·⬜·✅·⬜ | IN_PROGRESS | Track D: `Worker` (nombre/rol/tarifa estándar) cubre lo mínimo que `TimeEntry` necesita — no es un módulo de RRHH completo (sin expediente, documentos, contratos); sin pantalla dedicada todavía |
| NXR-REQ-0074 | Crews | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0075 | Time Entries | ✅·✅·✅·✅·⬜·✅·⬜·✅·⬜ | IN_PROGRESS | Track D: `TimeEntry` (SUBMITTED→APPROVED/REJECTED, decisión terminal), API `/api/workforce/time-entries`; sin pantalla dedicada todavía |
| NXR-REQ-0076 | Labor Cost (rate × hours) | ✅·✅·✅·✅·⬜·✅·⬜·✅·⬜ | IN_PROGRESS | Track D: INV-WFC-001, `labor_cost = hourly_rate * approved_hours` calculado SIEMPRE en el servidor al aprobar (RED/GREEN evidence real: rate 125.50 × 8h = 1004.00); posting hacia el GL queda deuda intencional documentada (docs/ENTERPRISE_RESOURCES.md), sin pantalla dedicada |

## CONSTRUCTION CONTROL

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0077 | Documents (enterprise entity + Blob) | ⬜·⬜·🔶·⬜·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | cliente Azure Blob (`azure_blob.py`) listo, falta entidad `Document`/API/UI |
| NXR-REQ-0078 | Document Versioning | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0079 | Evidence (PDF/JPEG/PNG/WEBP validado) | ⬜·⬜·🔶·⬜·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | backend de storage listo, falta validación MIME/tamaño + endpoints |
| NXR-REQ-0080 | Vouchers / comprobantes (PDF profesional) | ✅·➖·✅·✅·⬜·✅·⬜·✅·⬜ | IMPLEMENTED | Track A: PDF vectorial generado desde AccountingDocument real con ReportLab; endpoint protegido por company; falta UI dedicada |
| NXR-REQ-0081 | Daily Site Reports | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0082 | Quality (Inspection/Checklist) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0083 | Non-Conformance / Corrective Action | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0084 | Safety (Incident/Observation/Checklist) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0085 | RFI | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0086 | Submittals | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |

## PLATFORM

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0087 | Workflow engine central | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0088 | Approval Inbox | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0089 | Segregation of Duties | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0090 | Audit (append-only) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0091 | Notifications | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0092 | Global Search (Cmd/Ctrl+K) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0093 | Reporting (por dominio) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0094 | Export (CSV/XLSX/PDF) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0095 | Settings | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0096 | Integration architecture (SAP/AI adapters) | ⬜⬜⬜⬜➖⬜⬜⬜➖ | NOT_STARTED | — |

## EXPERIENCE

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0097 | Login | ➖·➖·✅·✅·✅·➖·⬜·✅·⬜ | IMPLEMENTED | rediseñado: sin campo Project, split desktop con ilustración, mobile centrado, forgot-password honesto, loading/invalid/server-error/network-error distinguidos — falta reset real (backend) |
| NXR-REQ-0098 | Role-based Home | ➖·➖·🔶·✅·✅·➖·⬜·✅·⬜ | IMPLEMENTED | `HomePage` + `resolveHomeConfig` por rol (finance/project/procurement/warehouse/auditor/default); cards reales solo donde hay backend, EmptyState honesto en el resto |
| NXR-REQ-0099 | Enterprise Navigation | ➖·➖·➖·➖·✅·⬜·➖·✅·⬜ | IMPLEMENTED | sidebar agrupado (Inicio/Finanzas/Proyectos/Abastecimiento/Comercial/Recursos/Control, ~50 rutas), drawer mobile, CommandPalette Cmd/Ctrl+K real |
| NXR-REQ-0100 | Design System | ➖·➖·➖·➖·✅·➖·➖·✅·⬜ | IMPLEMENTED | ~33 componentes (12 base + IconButton, Textarea, SearchInput, DatePicker, MoneyInput, CurrencyInput, Combobox, EntitySelector+7 dominios, StatCard, Metric, ChartCard, DataGrid, FilterBar, Tooltip, Popover, Drawer, Sheet, Toast+Alert, Breadcrumb, Stepper, Timeline, Tabs, Skeleton, CommandPalette) + tokens de motion/z-index/breakpoints |
| NXR-REQ-0101 | Responsive Desktop | ➖➖➖➖✅➖➖⬜⬜ | IMPLEMENTED | revisado por código contra 1440/1280/1024 (sin browser real disponible en este entorno, ver nota de verificación) |
| NXR-REQ-0102 | Tablet | ➖➖➖➖✅➖➖⬜⬜ | IMPLEMENTED | sidebar→drawer en ≤1024px, revisado por código contra 768 (sin browser real disponible) |
| NXR-REQ-0103 | Mobile | ➖➖➖➖✅➖➖⬜⬜ | IMPLEMENTED | revisado por código contra 430/390/360, touch targets ≥44px vía token `--nx-touch-target` (sin browser real disponible) |
| NXR-REQ-0104 | PWA | ➖➖➖➖✅➖➖⬜⬜ | IMPLEMENTED | manifest con iconos reales (antes `icons: []`), `NetworkOnly` forzado en `/api/*` (sin caché de datos financieros/sensibles ni mutación offline) |
| NXR-REQ-0105 | Accessibility (WCAG AA) | ➖➖➖➖🔶➖➖⬜⬜ | IN_PROGRESS | foco visible, labels, `role`/`aria-*` en overlays y estados, touch target ≥44px aplicado; falta auditoría de contraste real con herramienta y lector de pantalla |

## ENGINEERING

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0106 | Migrations (Alembic) | ➖·✅·✅·➖·➖·➖·➖·🔶·⬜ | IN_PROGRESS | `alembic upgrade head` aplicado; falta certificar fresh-install + upgrade matrix |
| NXR-REQ-0107 | Security (CSRF/rate-limit/lockout/headers) | ➖➖🔶➖➖➖➖⬜⬜ | IN_PROGRESS | Argon2id + HttpOnly + Secure-en-prod; falta el resto de §121 |
| NXR-REQ-0108 | Observability | ➖➖🔶➖➖➖➖⬜⬜ | IN_PROGRESS | App Insights opcional wired; falta logging estructurado con correlation_id |
| NXR-REQ-0109 | Backup / Restore | ⬜⬜⬜⬜➖⬜➖⬜➖ | NOT_STARTED | — |
| NXR-REQ-0110 | Unit tests | ➖➖✅➖✅➖➖✅➖ | IN_PROGRESS | Track A: suite combinada 81 backend + 24 frontend; crecerá con los tracks restantes |
| NXR-REQ-0111 | Integration tests (PostgreSQL) | ➖➖✅➖➖➖➖✅➖ | IMPLEMENTED | Track A: pruebas reales contra PostgreSQL para lifecycle, aislamiento, constraints, postings, idempotencia y conciliación |
| NXR-REQ-0112 | E2E (Playwright) | ➖➖➖➖➖➖➖➖⬜ | NOT_STARTED | — |
| NXR-REQ-0113 | Critical User Journey | ➖➖➖➖➖➖➖➖⬜ | NOT_STARTED | — |
| NXR-REQ-0114 | CI/CD | ➖➖🔶➖➖➖➖🔶➖ | IN_PROGRESS | workflows build+test+bicep-what-if existen; falta gate completo §118-119 |

## AZURE

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0115 | Bicep (IaC) | ➖➖➖➖➖➖➖✅⬜ | IN_PROGRESS | `az bicep build` 7/7 OK, `what-if` Succeeded contra sub UNAH; sin deploy real |
| NXR-REQ-0116 | Static Web Apps | ➖➖➖➖➖➖➖⬜⬜ | IN_PROGRESS | módulo Bicep escrito, sin desplegar |
| NXR-REQ-0117 | Container Apps | ➖➖➖➖➖➖➖⬜⬜ | IN_PROGRESS | módulo Bicep escrito, sin desplegar |
| NXR-REQ-0118 | Azure Database for PostgreSQL | ➖➖➖➖➖➖➖⬜⬜ | IN_PROGRESS | módulo Bicep escrito, sin desplegar |
| NXR-REQ-0119 | Blob Storage | ➖➖🔶➖➖➖➖⬜⬜ | IN_PROGRESS | módulo Bicep + cliente `azure_blob.py`, sin desplegar |
| NXR-REQ-0120 | Key Vault | ➖➖🔶➖➖➖➖⬜⬜ | IN_PROGRESS | módulo Bicep + cliente `azure_keyvault.py`, sin desplegar |
| NXR-REQ-0121 | Monitor / Application Insights | ➖➖🔶➖➖➖➖⬜⬜ | IN_PROGRESS | módulo Bicep + wiring opcional en `main.py`, sin desplegar |
| NXR-REQ-0122 | OIDC deployment (federated credentials) | ➖➖⬜➖➖➖➖⬜⬜ | NOT_STARTED | workflow escrito, falta configurar credenciales federadas en GitHub |
| NXR-REQ-0123 | Production smoke | ⬜ | BLOCKED_EXTERNAL | requiere confirmación puntual de despliegue real (`CLAUDE.md` §11.1) |
| NXR-REQ-0124 | Production E2E | ⬜ | BLOCKED_EXTERNAL | requiere confirmación puntual de despliegue real (`CLAUDE.md` §11.1) |

## Resumen

Recontado tras Track E (Commercial), pendiente de integración por el
coordinador, sobre la base de Track 1+F+B+C+A+D ya integrados:

- **VERIFIED:** 0 / 124 (reservado para cuando el coordinador confirme
  comportamiento end-to-end en `feat/nexora-greenfield` — ningún track se
  autootorga `VERIFIED`)
- **IMPLEMENTED:** 68 / 124 — Track 1: NXR-REQ-0002/0003/0004/0005/0007/
  0010/0011/0012/0013/0014/0015/0026/0027 (13). Track A: NXR-REQ-0017 a
  0024, 0080 y 0111 (10). Track F: NXR-REQ-0097 a 0104 (8). Track B:
  NXR-REQ-0028/0029/0030/0031/0032/0036/0037/0038/0039 (9). Track C:
  NXR-REQ-0040/0041/0042/0043/0045/0046/0047/0048/0049/0050/0051/0052/
  0053/0055/0056/0057 (16). Track D: NXR-REQ-0068/0069/0070/0071/0072 —
  Fixed Assets/Depreciation/Equipment/Fuel log/Maintenance (5). Track E:
  NXR-REQ-0061/0062/0063/0064/0065/0066/0067 — Leads/Opportunities/
  Customers/Sales Quotations/Sales Contracts/Customer Invoices (desde
  Commercial)/Collections (desde Commercial) (7).
- **IN_PROGRESS:** 26 / 124 (20 previos + 3 de Track C: 0044 Bid
  Comparison, 0059/0060 Contracts/Subcontracts + 3 de Track D: 0073/0075/
  0076 — Employees/Time Entries/Labor Cost, backend+API+tests completos,
  sin pantalla dedicada todavía)
- **NOT_STARTED:** 28 / 124 (incluye 0054 Returns y 0058 Supplier
  Performance de Track C — deuda intencional documentada en
  `docs/PROCUREMENT.md`/`docs/INVENTORY.md`; incluye 0074 Crews y todo el
  bloque CONSTRUCTION CONTROL — Documents/Site/Quality, 0077-0079/0081-
  0086 — que Track D no tocó en este corte, ver task-5-report.md)
- **BLOCKED_EXTERNAL:** 2 / 124 (ambos por la excepción de despliegue
  real, no por incapacidad técnica)

Suma verificada: 0+68+26+28+2 = 124.

Este resumen se actualiza en cada integración de track. Ver progreso vivo
en `docs/PROGRESS.md`. Recontado durante la construcción de Track E
(Commercial) sobre Track 1+F+B+C+A+D ya integrados (Task 6 de
`2026-08-24-interrupted-tracks-recovery`); sigue sujeto a una pasada final
de verificación end-to-end antes de certificar cualquier `VERIFIED`.
