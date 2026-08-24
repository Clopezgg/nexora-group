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

Última actualización: integración de Track 1 (Foundation) + Track F
(Experience) en `feat/nexora-greenfield`.

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
| NXR-REQ-0015 | Posting engine (PostingRule/PostingService) | ✅·✅·✅·➖·➖·➖·➖·✅·➖ | IMPLEMENTED | `posting_service.post_manual`/`reverse_document`, `PostingRule` (modelo, sin resolver automático todavía — ver docs/ACCOUNTING.md); contrato documentado para que otros tracks lo consuman |
| NXR-REQ-0016 | Financial statements (TB, GL, BS, P&L, Cash Flow) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track G (Reporting), sobre los datos que ya deja el GL de este track |
| NXR-REQ-0017 | Treasury (accounts, position) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A |
| NXR-REQ-0018 | Remittances (scope=CENTRAL) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A — puede consumir `posting_service` + OperationScope ya construidos |
| NXR-REQ-0019 | Transfers (bank/cash) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A |
| NXR-REQ-0020 | Cash (closing, position) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A |
| NXR-REQ-0021 | Bank reconciliation | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A |
| NXR-REQ-0022 | Fund restrictions | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A |
| NXR-REQ-0023 | Accounts Payable | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A |
| NXR-REQ-0024 | Accounts Receivable | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track E |
| NXR-REQ-0025 | Corrections (posted docs) | 🔶·✅·✅·➖·➖·➖·⬜·✅·➖ | IN_PROGRESS | Mecanismo de reversal cubre el caso general (INV-ACC-002); falta un flujo de "correction" distinto al reversal simple si algún dominio lo necesita — dueño: track que lo requiera |
| NXR-REQ-0026 | Annulments (reversal, no delete) | ✅·✅·✅·✅·⬜·➖·⬜·✅·⬜ | IMPLEMENTED | `posting_service.reverse_document`, endpoint `POST /api/accounting/journal-entries/{id}/reverse`, documento tipo `ANU`; falta UI |
| NXR-REQ-0027 | Idempotency (Idempotency-Key) | ✅·✅·✅·⬜·➖·➖·⬜·✅·➖ | IMPLEMENTED | `idempotency_service.begin/complete`, `IdempotencyRecord`; sin middleware HTTP que lea el header `Idempotency-Key` automáticamente todavía — cada dominio lo invoca explícitamente por ahora |

## PROJECT CONTROL

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0028 | Projects | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Track B: modelo completo (§37), `GET/POST /api/projects`, `ProjectsPage` real (crea compañía/proyecto), test `test_project_has_no_money_column` (INV-TRE-002) |
| NXR-REQ-0029 | WBS (jerárquico) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `WBSNode` con parent/level, `WBSPage` real, test de jerarquía 2 niveles |
| NXR-REQ-0030 | Planning (tasks/milestones/deps) | ✅·✅·✅·✅·⬜·⬜·⬜·✅·⬜ | IMPLEMENTED | `Task`/`Milestone` + API; sin pantalla dedicada todavía (`/proyectos/planeacion` sigue en EmptyState del bootstrap) |
| NXR-REQ-0031 | Budgets | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `Budget`/`BudgetLine`, `budget_service.compute_summary`, `BudgetPage` con AUTHORIZED/COMMITTED/ACCRUED/PAID/AVAILABLE reales |
| NXR-REQ-0032 | Budget versions (baseline/revised) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | BASELINE inmutable (`NXR-BUDGET-001` si se repite), REVISED generado por ChangeOrder aprobada, historial preservado — test dedicado |
| NXR-REQ-0033 | Commitments | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track C (Procurement) — `budget_service.compute_summary` ya tiene el punto de integración documentado en docs/BUDGET_CONTROLLING.md |
| NXR-REQ-0034 | Accruals | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A (AP) — mismo contrato de integración |
| NXR-REQ-0035 | Payments (project attribution) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | Dueño: Track A (AP) |
| NXR-REQ-0036 | Forecast (BAC/PV/EV/AC/CPI/SPI/ETC/EAC/VAC) | ✅·➖·✅·✅·✅·➖·➖·✅·⬜ | IMPLEMENTED | `forecast_service.compute_forecast`; valores no calculables devuelven `null` real, nunca 0 falso — test dedicado |
| NXR-REQ-0037 | Earned Value | ✅·➖·✅·✅·✅·➖·➖·✅·⬜ | IMPLEMENTED | PV/EV derivados del `ProgressRecord` más reciente contra BAC — simplificación documentada en docs/BUDGET_CONTROLLING.md |
| NXR-REQ-0038 | Change Orders | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | Lifecycle DRAFT→SUBMITTED→APPROVED real, `ChangeOrdersPage`, test de transición inválida (`NXR-PROJECT-001`) |
| NXR-REQ-0039 | Progress (ProgressRecord) | ✅·✅·✅·✅·✅·⬜·⬜·✅·⬜ | IMPLEMENTED | `ProgressRecord` (planned%/actual%/evidence_ref libre), `ProgressPage`, alimenta Forecast |

## PROCUREMENT

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0040 | Purchase Requisition | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0041 | Approval workflow (PR) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0042 | RFQ | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0043 | Supplier Quotations | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0044 | Bid Comparison | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0045 | Purchase Order | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0046 | Goods Receipt | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0047 | Service Entry | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0048 | Three-Way Match | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |

## SUPPLY CHAIN

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0049 | Items | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0050 | Warehouses | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0051 | Stock Ledger (append-only) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0052 | Inventory Transfers | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0053 | Project Issues | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0054 | Returns | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0055 | Physical Counts | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0056 | Valuation (moving average) | ⬜⬜⬜⬜➖⬜⬜⬜➖ | NOT_STARTED | — |

## SUPPLIERS / CONTRACTS

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0057 | Supplier Master | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0058 | Supplier Performance | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0059 | Supplier Contracts | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0060 | Subcontracts | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |

## COMMERCIAL

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0061 | Leads | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0062 | Opportunities | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0063 | Customers | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0064 | Sales Quotations | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0065 | Sales Contracts | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0066 | Customer Invoices | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0067 | Collections | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |

## RESOURCES

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0068 | Fixed Assets | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0069 | Depreciation (straight-line) | ⬜⬜⬜⬜➖⬜⬜⬜➖ | NOT_STARTED | — |
| NXR-REQ-0070 | Equipment | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0071 | Fuel log | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0072 | Maintenance (plan/order) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0073 | Employees | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0074 | Crews | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0075 | Time Entries | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0076 | Labor Cost (rate × hours) | ⬜⬜⬜⬜➖⬜⬜⬜➖ | NOT_STARTED | — |

## CONSTRUCTION CONTROL

| ID | Requirement | Trazabilidad | Status | Evidence |
|---|---|---|---|---|
| NXR-REQ-0077 | Documents (enterprise entity + Blob) | ⬜·⬜·🔶·⬜·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | cliente Azure Blob (`azure_blob.py`) listo, falta entidad `Document`/API/UI |
| NXR-REQ-0078 | Document Versioning | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
| NXR-REQ-0079 | Evidence (PDF/JPEG/PNG/WEBP validado) | ⬜·⬜·🔶·⬜·⬜·⬜·⬜·⬜·⬜ | IN_PROGRESS | backend de storage listo, falta validación MIME/tamaño + endpoints |
| NXR-REQ-0080 | Vouchers / comprobantes (PDF profesional) | ⬜⬜⬜⬜⬜⬜⬜⬜⬜ | NOT_STARTED | — |
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
| NXR-REQ-0110 | Unit tests | ➖➖✅➖✅➖➖✅➖ | IN_PROGRESS | 15/15 backend, 5/5 frontend — crecerá con cada módulo |
| NXR-REQ-0111 | Integration tests (PostgreSQL) | ➖➖⬜➖➖➖➖⬜➖ | NOT_STARTED | — |
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

Recontado tras Track B (Project Control), pendiente de integración por el
coordinador, sobre la base de Track F + Track 1 ya integrados:

- **VERIFIED:** 0 / 124 (reservado para cuando el coordinador confirme
  comportamiento end-to-end en `feat/nexora-greenfield` — ningún track se
  autootorga `VERIFIED`)
- **IMPLEMENTED:** 30 / 124 — Track 1: NXR-REQ-0002/0003/0004/0005/0007/
  0010/0011/0012/0013/0014/0015/0026/0027. Track F: NXR-REQ-0097 a 0104.
  Track B: NXR-REQ-0028/0029/0030/0031/0032/0036/0037/0038/0039.
- **IN_PROGRESS:** 20 / 124
- **NOT_STARTED:** 72 / 124
- **BLOCKED_EXTERNAL:** 2 / 124 (ambos por la excepción de despliegue
  real, no por incapacidad técnica)

Suma verificada: 30+20+72+2 = 124.

Este resumen se actualiza en cada integración de track. Ver progreso vivo
en `docs/PROGRESS.md`.
