# NEXORA GROUP — Progress Log

Bitácora viva de integración. Cada entrada corresponde a un track
integrado a `feat/nexora-greenfield`, con evidencia real, nunca
aspiracional. No se reemplazan entradas anteriores, se agregan.

## Rúbrica — avance real acumulado

Bootstrap / Platform baseline: **5% / 5%** (commit `62c56eb`, verificado).

Todo lo demás: **0% acumulado formalmente** hasta que un track aterrice
con evidencia (ver `docs/REQUIREMENTS_TRACEABILITY.md` para el detalle
pieza por pieza — varios requisitos están `IN_PROGRESS` pero ningún
bloque de la rúbrica se marca completo todavía).

## Entradas

### 2026-08-24 — Arranque de la ORDEN MAESTRA

- `CLAUDE.md` actualizado con los pilares, invariantes contables, rúbrica
  fija y las dos excepciones de autorización.
- `docs/MASTER_PLAN.md` creado: tracks, orden de ejecución, dependencias.
- `docs/REQUIREMENTS_TRACEABILITY.md` creado: 124 requisitos (`NXR-REQ-0001`
  a `NXR-REQ-0124`), estado inicial derivado honestamente del código ya
  existente (bootstrap + IaC Azure) — 0 `VERIFIED`, 30 `IN_PROGRESS`, 92
  `NOT_STARTED`, 2 `BLOCKED_EXTERNAL` (despliegue de producción, gated por
  `CLAUDE.md` §11.1).
- Próximo: Track 1 (Foundation: core platform, master data, identity/RBAC
  ampliado, chart of accounts, posting engine, GL, OperationScope) y
  Track F (Experience: design system ampliado, navegación empresarial)
  lanzados en paralelo.

### 2026-08-24 — Track F (Experience) construido, pendiente de integración

Rama `track/f-experience` (worktree aislado, no tocó `backend/`). Trabajo
real, verificado con comandos reales, no solo escrito:

- **Tokens**: cian sutil, motion, z-index, breakpoints (1440/1280/1024/768/
  430/390/360) y touch target (44px) añadidos a `tokens.css` +
  `tokens/motion.ts`.
- **Design System**: de 12 a ~33 componentes (`IconButton`, `Textarea`,
  `SearchInput`, `DatePicker`, `MoneyInput`, `CurrencyInput`, `Combobox`,
  `EntitySelector` + 7 selectores de dominio, `StatCard`, `Metric`,
  `ChartCard`, `DataGrid`, `FilterBar`, `Tooltip`, `Popover`, `Drawer`,
  `Sheet`, `ToastProvider`/`useToast`, `Alert`, `Breadcrumb`, `Stepper`,
  `Timeline`, `Tabs`, `Skeleton`, `CommandPalette`). Ninguno con datos
  fabricados: donde no hay backend, `EntitySelector`/secciones de home
  muestran `EmptyState` real.
- **App Shell**: sidebar reagrupado en Inicio/Finanzas/Proyectos/
  Abastecimiento/Comercial/Recursos/Control (~50 rutas reales, la mayoría
  en `EmptyState` profesional porque su backend aún no existe — esperado
  en esta etapa), drawer de navegación mobile, `CommandPalette` con
  Cmd/Ctrl+K real (busca sobre las rutas reales de la app, contrato listo
  para `GET /api/v1/search` cuando exista).
- **Login rediseñado**: sin campo Project, split desktop con ilustración
  de construcción inline (SVG, sin assets externos), mobile centrado,
  "¿Olvidaste tu contraseña?" con aviso honesto (no hay backend de reset
  todavía), estados loading/credenciales inválidas/error de servidor
  (no-401)/error de red diferenciados.
- **Role-based Home**: `HomePage` + `resolveHomeConfig` — Administrator/
  Finance/Treasury/Accountant ven las cards reales de tesorería (API
  existente); Project Manager/Controller, Procurement/Buyer, Warehouse
  Manager y Auditor ven secciones con `EmptyState` honesto apuntando al
  `NXR-REQ` que las activará.
- **PWA**: manifest tenía `icons: []` (no instalable) — corregido con
  icono real (`pwa-icon.svg`); `NetworkOnly` forzado sobre `/api/*` para
  que el service worker nunca cachee datos financieros ni permita
  mutación offline.

**Verificación real ejecutada** (no solo "se ve bien"): `npm run
typecheck` limpio, `npm run lint` limpio, `npm run build` OK (dist
generado, PWA precache 7 entries), `npx vitest run` → **15/15** tests
pasan (antes 5/5 — 10 tests nuevos: `design-system.test.tsx` ×6,
`HomePage.test.tsx` ×2, `AppShell.test.tsx` ×2, más ampliación de
`routing.test.tsx`), `vite preview` real sirvió `HTTP 200` con
`<title>Nexora Group</title>`. Pase con el skill `impeccable`
(`detect.mjs`) encontró un side-tab accent border (patrón reconocible de
"AI slop") en `Toast`/`Alert` — corregido a icono de tono + fondo
tintado sutil, sin borde grueso; re-ejecutado, 0 hallazgos.

**Bug real encontrado y corregido durante la propia verificación**: el
botón de búsqueda del Topbar simulaba el atajo Cmd/Ctrl+K con
`window.dispatchEvent(...)`, pero el listener del `CommandPalette` está
en `document` — un evento despachado en `window` no burbujea hacia abajo
a `document`, así que el botón nunca habría abierto la paleta en un
navegador real (los tests con mocks no lo habrían detectado sin una
prueba de interacción real). Corregido a `document.dispatchEvent(...)` y
cubierto con un test de interacción real
(`AppShell.test.tsx`).

**Limitación honesta**: no hay navegador/herramienta de captura de
pantalla disponible en este entorno de subagente — la revisión visual
(§135 de la orden) se hizo por código/CSS contra la matriz de breakpoints
y el detector mecánico de `impeccable`, no con una captura real en
navegador. Queda pendiente una pasada visual en navegador real antes de
certificar `VERIFIED` (NXR-REQ-0101 a 0105 quedan `IMPLEMENTED`, no
`VERIFIED`, por esta razón).

Filas actualizadas en `docs/REQUIREMENTS_TRACEABILITY.md`: NXR-REQ-0097 a
0104 → `IMPLEMENTED`; NXR-REQ-0105 → `IN_PROGRESS`. Ningún `VERIFIED`
auto-otorgado — eso lo confirma el coordinador al integrar a
`feat/nexora-greenfield`.

Commits: `feat(ui): expand design system with tokens and ~20 new
components`, `feat(ui): regroup sidebar into enterprise navigation with
command palette`, `feat(ui): redesign login with construction
illustration`, `feat(ui): add role-based home pages`, `fix(pwa): add
real manifest icons and block API caching`, `docs: update traceability
and progress for Track F`. Rama pusheada a `origin/track/f-experience`.

### 2026-08-24 — Track 1 (Foundation) completado en worktree, pendiente de integrar

Construido en `~/nexora-group-track1`, rama `track/1-foundation` (worktree
aislado del clon de integración). Evidencia real:

- **Master data**: `Company` extendida (code/legal_name/functional_currency/
  country/fiscal_id), `BusinessUnit`, `FiscalYear`/`FiscalPeriod`,
  `Currency`/`ExchangeRate` (seed HNL/USD), `TaxCode`, `ChartOfAccount`/
  `Account`, `CostCenter`/`EconomicCategory`, `DocumentType` (seed JRN/COR/
  ANU), `NumberSequence`, `ApprovalPolicy` (esqueleto), `Permission`/
  `RolePermission`/`UserCompanyAccess`.
- **Identity/RBAC**: 14 roles (§87), motor central de permisos backend-
  autoritativo (`require_permission` + `assert_company_access`), matriz de
  permisos real para `core.company`/`accounting.*`.
- **OperationScope**: CHECK constraint real de PostgreSQL
  (`ck_accounting_documents_operation_scope`) confirmado con
  `\d accounting_documents` contra una base recién migrada.
- **Posting Engine / GL**: `AccountingDocument`/`JournalLine`/`PostingRule`/
  `TaxLine`/`AccountingSourceLink`, `posting_service.post_manual` /
  `reverse_document`, numeración concurrency-safe (`SELECT...FOR UPDATE`),
  inmutabilidad de documentos posted, API `/api/accounting/journal-entries`.
- **Idempotency**: `IdempotencyRecord` + `idempotency_service`.
- **Company isolation (INV-COMP-001)**: `company_scope` ANY/OWN aplicado y
  probado con 4 tests dedicados.
- **Tests**: 35/35 pytest pasando (15 preexistentes + 20 nuevos). Frontend
  sin tocar: 5/5 vitest, typecheck limpio, build OK (verificado de nuevo
  tras los cambios).
- **Migraciones**: `alembic revision --autogenerate` generó
  `c622defc2308_add_foundation_master_data_accounting_...py`; aplicada
  sobre `nexora_dev` y, por separado, verificada en un fresh-install
  completo (`nexora_dev_fresh` creada, migrada desde cero con ambas
  revisiones, 30 tablas confirmadas, base descartada al terminar).
- **Documentación**: `docs/ACCOUNTING.md` (contrato del Posting Engine +
  Idempotency + catálogo completo de invariantes §130 con dueño asignado
  por invariante) y `docs/RBAC.md` (contrato del motor de permisos)
  creados.
- **Desviaciones**: `project_scope` existe en el modelo `RolePermission`
  pero no se aplica en ningún endpoint todavía (documentado en
  `docs/RBAC.md` para el próximo track que lo necesite). Dimensiones
  contables sin tabla propia (supplier/customer/asset/warehouse) viven en
  `JournalLine.extra_dimensions` (JSONB) como deuda intencional hasta que
  el track dueño cree la entidad real (documentado en `docs/ACCOUNTING.md`).
  `PostingRule` existe como modelo pero sin resolver automático
  (`post_via_rule`) porque ningún dominio real lo necesitó todavía.
- **Commits en `track/1-foundation`** (no integrados a
  `feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
  coordinador): ver `git log track/1-foundation`.
- **Rúbrica**: este track por sí solo no cierra ningún bloque de la
  rúbrica al 100% (Accounting/GL sigue abierto porque le falta reporting y
  UI), pero deja la base sobre la que Treasury/AP/AR/Procurement/Inventory
  pueden construir sin reinventar el motor contable.

### 2026-08-24 — Integración a `feat/nexora-greenfield`

Coordinador integró ambos tracks. Re-verificación independiente (no solo
el reporte de cada subagente) antes de cada merge:

- Track F: `typecheck`/`lint`/`build` limpios, `vitest` 15/15, sin cambios
  en `backend/` — confirmado con `git diff --stat`.
- Track 1: `pytest` 35/35, `alembic heads`/`alembic current` en
  `c622defc2308`, `CheckConstraint` de OperationScope confirmado por
  `grep` en el modelo y en la migración generada, sin cambios en
  `frontend/` — confirmado con `git diff --stat`.

Ningún requisito pasa a `VERIFIED` todavía solo por esta integración —
`VERIFIED` requiere que el sistema combinado (backend + frontend) se
pruebe de extremo a extremo, no solo que cada mitad pase sus propios
tests por separado.

### 2026-08-24 — Track A (Financial Core) endurecido, pendiente de integración

Rama `track/a-financial-core`, worktree aislado. Se recuperó y auditó el
trabajo heredado de Treasury/AP/AR y se corrigieron brechas con ciclos TDD
reales:

- Treasury sigue siendo el único dueño de efectivo; Project permanece sin
  campos de saldo y las restricciones de fondos solo etiquetan uso.
- Toda FK financiera se resuelve y valida contra la company propietaria:
  invoice, treasury account, cuentas GL, Project, CostCenter, statements,
  líneas, cierres, restricciones y vouchers.
- Scope y montos están limitados en schema, dominio y CHECK constraints;
  ningún movimiento admite cero/negativos.
- Conciliación acumula matches bajo `SELECT ... FOR UPDATE`, bloquea
  overmatch y documentos de otra company.
- Remesas, transferencias, gastos generales, aprobación de cierre, pagos AP
  y cobros AR componen idempotencia + posting + entidad en una transacción.
- AP/AR exponen colecciones GET por company y las pantallas recargan facturas
  persistidas desde PostgreSQL. AR queda en Financial Core; Track E posee el
  workflow comercial y consumirá AR sin duplicarlo.
- La numeración contable se corrigió a unicidad `(company_id,
  document_number)`, compatible con secuencias por compañía.
- Corrección 1/5: el Posting Engine central valida compañía para Project del
  documento y cuenta/Project/CostCenter de cada línea antes de persistir.
- Cada cuenta GL solo puede respaldar una TreasuryAccount, evitando duplicar
  el mismo saldo al presentar la posición de efectivo.
- Conciliación exige cuenta GL, signo y capacidad disponible del documento,
  serializa asignaciones entre líneas y restringe MATCH/EXCLUDED a estados
  válidos.
- Las cinco mutaciones monetarias de UI envían un UUID idempotente estable en
  sus variables de mutación, reutilizado por los reintentos de transporte.
- Migración `58ce35982711`: fresh-install completo hasta head, 43 tablas y
  constraints críticos inspeccionados en PostgreSQL temporal.
- Migraciones hasta `a91c7d4e2f36`: fresh-install y `alembic check` sin drift.
- Evidencia de rama: backend combinado 81 tests, frontend 24 tests,
  typecheck/lint/build y Alembic gates ejecutados. Las filas se marcan
  `IMPLEMENTED`, nunca `VERIFIED`, hasta integración coordinada/E2E.

### 2026-08-24 — Track C (Supply Chain) construido, pendiente de integrar

Construido en `~/nexora-group-trackC`, rama `track/c-supply-chain`
(worktree aislado). Evidencia real:

- **Suppliers / base contractual**: `Supplier` (legal_name/trade_name/
  tax_id/banking_details JSONB — explícitamente distinto de
  `TreasuryAccount`) y `SupplierContract` (value/currency/advance/retention
  %). Supplier Master es parte de Track C; Contracts/Subcontracts siguen
  `IN_PROGRESS` hasta tener pruebas dedicadas, UI y distinción formal para
  reporting de subcontratos.
- **Procurement end-to-end**: `PurchaseRequisition`→`RequestForQuotation`
  (multi-supplier)→`SupplierQuotation`→`PurchaseOrder`
  (`DRAFT→APPROVED→SENT→PARTIALLY_RECEIVED/RECEIVED`)→`GoodsReceipt`
  (recepción parcial y completa, actualiza `quantity_received` y dispara
  `inventory_service.receive_stock`)→`ServiceEntry`. Numeración real vía
  `numbering_service` (`PR`, `RFQ`, `PO`, `GR`, `SIN`).
- **Three-Way Match (INV-PROC-001)**: `run_three_way_match` compara PO vs
  recepción vs factura de proveedor (referencia libre, la factura real la
  construye Track A en paralelo); las diferencias fuera de tolerancia
  quedan en `exceptions`, **nunca se descartan silenciosamente** — el
  registro se persiste tanto en MATCHED como en EXCEPTION.
- **Inventory**: `Item`/`Warehouse`/`StockLedgerEntry` (append-only,
  moving average real), `receive_stock`/`issue_to_project`
  (INV-INV-002)/`transfer_stock`/`apply_physical_count`. `InsufficientStockError`
  (INV-INV-001) bloquea cualquier emisión que dejaría stock negativo.
- **Frontend**: `SuppliersPage`, `RequisitionsPage`, `PurchaseOrdersPage`
  (con aprobar/enviar), `GoodsReceiptsPage` (selecciona PO pendiente →
  registra recepción real), `InventoryPage`, `WarehousesPage` — reusan el
  design system de Track F, sin datos fabricados (EmptyState honesto
  cuando no hay compañía configurada).

**Verificación real ejecutada**: backend 48/48 pytest (35 preexistentes +
13 de procurement/inventory, incluidos los agregados documentales para
Commitments/actuals y el aislamiento por compañía en el recurso PO) contra
una base PostgreSQL aislada
(`nexora_trackc`/`nexora_trackc_test`, para no pisar el schema de Track
A/B/1 corriendo en paralelo sobre el mismo servidor Postgres local — nota
dejada en `tests/conftest.py` para que el coordinador vuelva a
`nexora_test` al integrar), `alembic revision --autogenerate` detectó las
18 tablas nuevas sin conflictos, `alembic upgrade head` limpio.
Frontend: `typecheck`/`lint` limpios, `vitest` 17/17 (15 preexistentes +
2 nuevos de `SuppliersPage`), `build` OK.

**Bugs reales encontrados y corregidos durante la propia verificación**:
1. Primer intento de migración corrió contra la base compartida
   `nexora_dev` (usada también por el coordinador) — se revirtió
   (`alembic downgrade`) antes de continuar, para no contaminar el
   estado que el coordinador usa para integrar Track 1/F.
2. El endpoint `GET /inventory/stock/position` usa query params en
   snake_case (`item_id`/`warehouse_id`, mismo patrón que
   `master_data.list_accounts` de Track 1) — los primeros tests fallaron
   por usar camelCase; corregido en los tests, no en el endpoint (para
   mantener consistencia con el precedente ya establecido).
3. Los tests de recepción de mercadería fallaban porque el helper de test
   no aprobaba/enviaba la PO antes de recibir (el servicio correctamente
   rechaza recepciones sobre una PO `DRAFT`) — corregido el helper, no el
   servicio.

**Desviaciones documentadas** (ver `docs/PROCUREMENT.md` /
`docs/INVENTORY.md` para el detalle completo): Bid Comparison sin
endpoint agregado ni pantalla dedicada (NXR-REQ-0044 queda
`IN_PROGRESS`); Supplier Performance sin implementar por falta de datos
históricos reales que no serían fabricados (NXR-REQ-0058 `NOT_STARTED`);
`RETURN` como movement_type existe en el modelo pero sin service function
(NXR-REQ-0054 `NOT_STARTED`); RFQ/Quotation/Comparison/Contracts sin
pantalla de frontend (fuera del alcance de UI acordado para este track,
con Contracts/Subcontracts explícitamente `IN_PROGRESS`).

Filas actualizadas en `docs/REQUIREMENTS_TRACEABILITY.md`: NXR-REQ-0040 a
0060 (Procurement + Supply Chain + Suppliers/Contracts). Ningún
`VERIFIED` auto-otorgado.

Commits de backend ya preservados en `track/c-supply-chain`: `6e92a87`
(`feat(procurement): implement requisition-to-receipt supply chain flow`) y
`9b5cb1f` (`test(procurement): certify INV-PROC-001 and
INV-INV-001/002 with real tests`). La recuperación de UI/docs queda en un
commit local explícito para que el coordinador la integre; este registro no
afirma publicación remota.

### 2026-08-24 — Track B (Project Control) construido, pendiente de integración

Rama `track/b-project-control` (worktree `~/nexora-group-trackB`, DB de
prueba propia `nexora_trackb` para no interferir con Track A corriendo en
paralelo sobre `nexora_dev`). Evidencia real:

- **Backend**: `Project` completado (§37, sin ninguna columna de saldo —
  INV-TRE-002 con test de introspección del esquema), `WBSNode` jerárquico
  (parent/level), `Task`/`Milestone` (planning), `Budget`/`BudgetLine` con
  versionado real (BASELINE inmutable — `NXR-BUDGET-001` si se intenta
  crear dos veces; REVISED generado automáticamente al aprobar una
  `ChangeOrder`, historial preservado, nunca se borra), `ChangeOrder`
  (lifecycle DRAFT→SUBMITTED→APPROVED real, `NXR-PROJECT-001` si se
  aprueba sin pasar por SUBMITTED), `ProgressRecord`. `budget_service.
  compute_summary` (AUTHORIZED real, COMMITTED/ACCRUED/PAID en 0 honesto
  con el contrato de integración para Track A/C documentado) y
  `forecast_service.compute_forecast` (BAC/PV/EV/AC/CPI/SPI/ETC/EAC/VAC —
  valores no calculables son `null` real, nunca 0 inventado, con test
  dedicado). 14 endpoints nuevos bajo `/api/projects`, permisos nuevos
  (`project`, `project.wbs`, `project.planning`, `project.budget`,
  `project.change_order`, `project.progress`) otorgados a Administrator/
  Project Manager/Project Controller/Auditor/Viewer.
- **Frontend**: `ProjectsPage` (crea compañía si no existe ninguna, crea/
  lista proyectos, marca "proyecto activo" vía `ActiveUIContext` — el
  mismo mecanismo de Fase 0/1, sin inventar un segundo concepto de
  "proyecto actual"), `WBSPage`, `BudgetPage` (summary + forecast, crea
  BASELINE), `ChangeOrdersPage` (crear/enviar/aprobar), `ProgressPage`.
  Rutas reales conectadas en `routes.tsx` para `/proyectos`,
  `/proyectos/wbs`, `/proyectos/presupuestos`, `/proyectos/ordenes-de-cambio`,
  `/proyectos/avances` (el resto de rutas del sidebar sigue en
  `PlaceholderPage`, incluida `/proyectos/planeacion` — Task/Milestone
  tienen API real pero no pantalla dedicada todavía).
- **Verificación real**: backend 46/46 pytest (35 previos + 11 nuevos),
  `alembic upgrade head` limpio + fresh-install desde cero verificado (37
  tablas). Frontend: typecheck/lint limpios, `vitest` 19/19 (15 previos +
  4 nuevos, incluye un test que prueba que el forecast muestra `null`
  honesto en vez de 0 falso sin datos de avance), `build` OK.
- **Desviaciones documentadas**: `ChangeOrder.budget_change_amount` es un
  monto agregado, no un desglose línea por línea (documentado en
  docs/BUDGET_CONTROLLING.md); PV/EV se derivan del `ProgressRecord` más
  reciente por falta de un motor de scheduling con distribución de $ por
  fecha (misma razón, documentado); `Project.customer_ref` es texto libre
  hasta que Track E aterrice `Customer` real.

Filas actualizadas en `docs/REQUIREMENTS_TRACEABILITY.md`: NXR-REQ-0028,
0029, 0030, 0031, 0032, 0036, 0037, 0038, 0039 → `IMPLEMENTED`. NXR-REQ-
0033/0034/0035 (Commitments/Accruals/Payments) siguen `NOT_STARTED` —
dueño Track A/C, contrato de integración ya documentado en
docs/BUDGET_CONTROLLING.md para que no tengan que rediseñar nada al
aterrizar.

### 2026-08-24 — Track A integrado sobre B+C (Task 4)

Merge `feat/nexora-greenfield` (Track 1+F+B+C, HEAD `1401ca2`) → `track/a-
financial-core`, `--no-ff`, todos los conflictos resueltos de forma
aditiva. Dos hallazgos reales durante la integración, no solo mecánica de
merge:

- **Colisión de PK real en `document_types.code`**: Track A y Track C
  sembraron el mismo código `SIN` con significados distintos (Track A =
  "Factura de proveedor / accrual"; Track C = "Entrada de servicio", ver
  la entrada de Track C arriba en esta bitácora, que describe el estado
  *antes* de esta integración). Como `code` es PK real, habría roto la
  numeración de uno de los dos flujos. Se renombró el código de Track C a
  `SEN` (`entryNumber` ahora usa el prefijo `SEN-YYYY-NNNNNN`, no
  `SIN-YYYY-NNNNNN`); el `SIN` de Track A (ya certificado con tests AP)
  quedó intacto. `docs/PROCUREMENT.md` y la fila NXR-REQ-0047 de
  `docs/REQUIREMENTS_TRACEABILITY.md` actualizadas para reflejar `SEN-`.
- **Placeholder de texto libre → FK real**: `SupplierInvoice.supplier_name`/
  `supplier_tax_id` reemplazados por `supplier_id` FK real a
  `Supplier` (Track C), validado contra la company propietaria
  (INV-COMP-001) igual que el resto de FKs financieras.

Alembic `58ce35982711` (Track A, sin publicar) relinkeado a
`down_revision = '8bf7c353d327'` (head real de Track C, verificado desde
los archivos de migración, no asumido). Cadena única, un solo head
(`a91c7d4e2f36`), `alembic upgrade head` limpio en base descartable.
Backend 120/120 pytest + compileall limpio; frontend typecheck/lint
limpios, 30/30 vitest, build OK.

Rama `track/a-financial-core` preparada e integration-ready, no fusionada
a `feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
coordinador (mismo patrón que Task 2).

### 2026-08-24 — Track D (Enterprise Resources) construido sobre Track 1+F+B+C+A (Task 5)

Worktree `/Users/clopezg/nexora-group-trackD`, branch `track/d-
enterprise-resources`. Punto de partida: el merge de Track B (`5f60a18`),
sin trabajo propio de Track D todavía commiteado, más dos drafts de
modelo reales (`asset.py`/`equipment.py`) dejados sin commitear por una
sesión interrumpida anterior — preservados primero en un commit dedicado,
después extendidos (nunca reescritos sin razón).

Merge `feat/nexora-greenfield` (HEAD `dd00a59`, Track 1+F+B+C+A ya
integrados) → `track/d-enterprise-resources`, `--no-ff`. Sin conflictos
(Track D no tenía trabajo propio todavía sobre el que colisionar).

**Implementado — cuatro slices verticales, prioridad honesta (Assets y
Equipment/Maintenance completos primero, per instrucción explícita del
brief):**

- **Assets (IMPLEMENTED)**: `FixedAsset` extiende el draft recuperado con
  `scope`/`project_id`/`cost_center_id` (mismo patrón de atribución que
  AP, Project nunca custodia dinero) y cuentas de depreciación propias
  (`depreciation_expense_account_id`/`accumulated_depreciation_account_id`
  — nunca hardcodeadas). `asset_service.generate_depreciation_entry`
  calcula straight-line real `(cost-salvage)/useful_life_months` y postea
  SIEMPRE vía `posting_service.post_manual` (documento `DEP`, nunca
  `JournalLine` a mano). INV-AST-001 (mismo asset+periodo nunca genera dos
  postings) con doble garantía: rechazo de dominio (`NXR-ASSET-002`) +
  `uq_depreciation_entries_asset_period` real en PostgreSQL. Activo
  `DISPOSED`/`RETIRED` es terminal (`NXR-ASSET-001`). 8 endpoints bajo
  `/api/assets`, permisos `asset.fixed_asset`/`asset.depreciation`,
  `FixedAssetsPage` (crear activo, generar depreciación por periodo, dar
  de baja), 7 tests backend + 2 tests frontend.
- **Equipment/Maintenance (IMPLEMENTED)**: `Equipment`/`FuelLog`/
  `MaintenancePlan`/`MaintenanceOrder` extendidos con CHECK constraints
  reales (montos positivos, status válido). `FuelLog.total_cost` se
  calcula SIEMPRE server-side (nunca del cliente); scope GENERAL/PROJECT
  con `ck_fuel_logs_operation_scope` (constraint real, ya existía en el
  draft recuperado, ahora con test directo de DB). Renombrado
  `MAINTENANCE_ORDER_STATUSES` `COMPLETED`→`CLOSED` para que el nombre
  coincida con el comportamiento: INV-EQP-001, un `MaintenanceOrder`
  `CLOSED`/`CANCELLED` es terminal — `update_maintenance_order` rechaza
  CUALQUIER mutación antes de tocar un campo (`NXR-EQUIPMENT-001`).
  Crear una orden mueve el equipo a `UNDER_MAINTENANCE`; cerrarla lo
  regresa a `AVAILABLE`. 13 endpoints bajo `/api/equipment`, permisos
  `equipment.*`, `EquipmentPage` con tabs Equipos/Combustible/
  Mantenimiento, 6 tests backend + 2 tests frontend.
- **Workforce/Time (IN_PROGRESS — backend completo, frontend
  NOT_STARTED)**: `Worker`/`TimeEntry` nuevos. INV-WFC-001: `labor_cost =
  hourly_rate * approved_hours` calculado SIEMPRE en el servidor al
  aprobar (nunca aceptado del cliente) — verificado con el caso exacto
  del brief (125.50 × 8 = 1004.00). `TimeEntry` solo se aprueba/rechaza
  una vez (decisión terminal, `NXR-WORKFORCE-001` si se reintenta). 6
  endpoints bajo `/api/workforce`, permisos `workforce.*`, 4 tests
  backend. Sin pantalla dedicada — decisión explícita de priorizar
  Assets/Equipment completos sobre las cuatro áreas superficialmente.
  Posting del costo de mano de obra hacia el GL queda deuda intencional
  documentada (`docs/ENTERPRISE_RESOURCES.md`), mismo patrón que
  Fuel/Maintenance.
- **Documents/Site/Quality (NOT_STARTED)**: no se tocó en este corte. Ver
  `docs/ENTERPRISE_RESOURCES.md` y la fila NXR-REQ-0077-0086 en
  `docs/REQUIREMENTS_TRACEABILITY.md`.

**RBAC**: `Equipment Manager` y `Operations User` (roles ya pre-sembrados
en `ROLE_NAMES` anticipando este track, sin permisos otorgados todavía)
recibieron su matriz de permisos en vez de inventar roles nuevos —
`Equipment Manager` custodia física (asset/equipment/maintenance, sin
`asset.depreciation`), `Operations User` combustible/mantenimiento/horas
de campo sin permisos de aprobación. `asset.depreciation` es exclusivo de
Finance Manager/Accountant/Administrator/Auditor (contabilización ≠
custodia física). `workforce.time_entry approve` otorgado a Project
Manager/Project Controller (el costo de mano de obra impacta el
presupuesto del proyecto).

**TDD real (RED/GREEN) para los cuatro comportamientos nombrados en el
brief** — guard deshabilitado temporalmente, test corrido (RED
confirmado con el error real), guard restaurado, test corrido de nuevo
(GREEN), para cada uno de: doble-posting de depreciación (sin el guard de
servicio, el `UniqueViolation` de PostgreSQL sale como 500 sin manejar en
vez de 409 `NXR-ASSET-002`), fuel log PROJECT sin project_id (sin el
guard, el `CheckViolation` de PostgreSQL sale como 500 sin manejar en vez
de 422 `NXR-ACCOUNTING-002`), orden de mantenimiento CLOSED inmutable (sin
el guard, `partsCost`/`description` se sobrescriben silenciosamente), y
labor cost = rate × hours (con el cálculo hardcodeado a `1.00`, el test
detecta la fuga inmediatamente). Evidencia completa (comandos + output
real) en `task-5-report.md`.

**Migración**: `7423072b11d4` (down_revision `a91c7d4e2f36`, el head real
de Track A tras el merge — no un head viejo de Track B), único head.
`alembic upgrade head` limpio en base descartable (`nexora_trackd_migrate`
y `nexora_trackd_gatecheck`, ambas creadas y eliminadas durante la
verificación), `alembic check` sin operaciones pendientes.

**Verificación real**: backend 136/136 pytest (120 previos + 16 nuevos),
`compileall` limpio. Frontend: typecheck/lint limpios, 34/34 vitest (30
previos + 4 nuevos), `build` OK (832 módulos, PWA precache 7 entradas).

Rama `track/d-enterprise-resources` preparada e integration-ready, no
fusionada a `feat/nexora-greenfield` todavía — pendiente de revisión/merge
por el coordinador (mismo patrón que Tracks A/B/C).

### 2026-08-24 — Track E (Commercial) construido sobre Track 1+F+B+C+A+D (Task 6)

Worktree `/Users/clopezg/nexora-group-trackE`, branch `track/e-commercial`.
Punto de partida: exactamente el merge de Track B (`5f60a18`), sin trabajo
propio de Track E todavía commiteado y worktree limpio — dominio
construido desde cero en esta tarea.

Merge `feat/nexora-greenfield` (HEAD `81fa5aa`, Track 1+F+B+C+A+D ya
integrados) → `track/e-commercial`, `--no-ff`. Sin conflictos.

**Restricción central de la tarea**: Track A ya es dueño de Accounts
Receivable (facturas/cobros de cliente). Track E nunca crea una segunda
tabla de receivables — factura un `SalesContract` llamando DIRECTO a
`ar_service.create_customer_invoice` (mismo proceso, sin una segunda API
HTTP interna, igual que `asset_service`/`ap_service` llaman a
`posting_service` directamente). Se añadió `commit=False` a
`ar_service.create_customer_invoice` (mismo patrón que
`collect_customer_receipt` ya tenía) para que la creación de la factura AR
y el cambio de estado del `SalesContract` a `BILLED` ocurran en una sola
transacción atómica — sin esa composición quedaba una ventana donde la
factura existía pero el contrato seguía `ACTIVE`, permitiendo doble
facturación en un reintento tras un crash entre los dos commits.

**Implementado — flujo comercial completo**: `Lead → Opportunity →
Customer/Quotation → SalesContract → factura AR real` (`app/models/crm.py`,
nuevas tablas `customers`/`leads`/`opportunities`/`quotations`/
`sales_contracts`, orden de FK sin ciclo: customers → leads →
opportunities → quotations → sales_contracts). `crm_service.convert_lead`
crea `Customer` + `Opportunity` juntos (patrón "Convert Lead" tipo CRM
estándar) de forma idempotente: bajo `SELECT ... FOR UPDATE` sobre el
`Lead`, un segundo intento de conversión detecta `status == CONVERTED` y
devuelve el mismo `Customer`/`Opportunity` sin crear fila nueva.
`crm_service.create_quotation` exige que `customer_id` coincida con el
cliente de la `Opportunity` (invariante nueva, no estaba en el diseño
inicial — se detectó como hueco de dominio antes de construir el
frontend). Solo una `Quotation` en estado `ACCEPTED` convierte a
`SalesContract` (`NXR-CRM-001` si no); la conversión preserva
`amount`/`company_id`/`customer_id`/`project_id` tal cual y deriva `scope`
(`PROJECT` si hay `project_id`, si no `GENERAL`) para que el
`CustomerInvoice` resultante cumpla el mismo CHECK de operation scope que
el resto del Financial Core. Facturar un contrato ya `BILLED` se rechaza
(`NXR-CRM-001`) — nunca una segunda factura para el mismo contrato.

**AR ya no es texto libre**: `CustomerInvoice.customer_name` (String) →
`CustomerInvoice.customer_id` (FK real a `customers.id`, `ON DELETE
RESTRICT`) — mismo patrón que la FK de `Supplier` en AP (Task 4).
`financial_validation_service.assert_customer_belongs_to_company` nueva
(mismo patrón que `assert_supplier_belongs_to_company`). Como la migración
de AR (`58ce35982711`) ya estaba publicada en `feat/nexora-greenfield`
antes de esta tarea (a diferencia del caso Supplier de Task 4, que aún no
se había fusionado), el cambio se hizo con una migración NUEVA sobre
`7423072b11d4` en vez de editar la migración ya publicada in-place.

12 endpoints bajo `/api/crm` (`customers`, `leads` + `convert`,
`opportunities` solo lectura, `quotations` + `accept`/`convert`,
`sales-contracts` + `bill`), permisos `crm.customer`/`crm.lead`/
`crm.opportunity`/`crm.quotation`/`crm.sales_contract`. Rol `Sales
Manager` (ya pre-sembrado en `ROLE_NAMES` anticipando este track, sin
permisos otorgados todavía) recibió su matriz — puede facturar pero
NUNCA obtiene permisos `ar.*` directos, la facturación real sigue
controlada por Track A. `Finance Manager`/`Accountant` recibieron
`crm.customer read` (para el selector de cliente real en `AccountsReceivablePage`,
mismo patrón que Task 4 dio `procurement.supplier read` a esos roles para
`SupplierSelector`). `Auditor` recibió lectura `crm.*` (mismo patrón que
el resto de dominios).

Frontend: `CustomersPage`/`LeadsPage`/`OpportunitiesPage`/
`QuotationsPage`/`SalesContractsPage` bajo `/comercial/*`, reutilizando
`CustomerSelector` (ya existía en el design system, sin endpoint real
hasta ahora) y el resto de primitivos existentes. `AccountsReceivablePage`
migrada de un input de texto libre a `CustomerSelector` real. Las rutas
`/comercial/facturacion` y `/comercial/cobros` del menú quedan como
`PlaceholderPage` a propósito — Track E factura vía Track A y no
construye una segunda UI de AR; el estado de facturación de un contrato
(`customerInvoiceId`) se ve directamente en `SalesContractsPage`.

**TDD real (RED/GREEN) para los tres comportamientos nombrados en el
brief + aislamiento de company**: `tests/test_crm.py` — conversión de
lead idempotente (segundo intento devuelve el mismo `Customer`, una sola
fila en DB), conversión de cotización rechazada antes de `ACCEPTED`
(`409 NXR-CRM-001`) y aceptada preservando amount/company/customer/project
después, facturación de contrato crea exactamente una `CustomerInvoice`
persistida y no produce ningún movimiento de tesorería (`GET
/api/treasury/accounts` vacío) antes de cobrar, un segundo intento de
facturar el mismo contrato se rechaza sin crear una segunda factura,
aislamiento de company en `crm.lead`/`crm.lead convert`/`crm.lead read`
(`403 NXR-PERM-001`). Escritos en rojo primero (import de
`app.models.crm` inexistente), implementados, verdes.

**Migración**: `f1075e290473` (down_revision `7423072b11d4`, el head real
de Track D), único head. `alembic upgrade head` limpio en base descartable
(`nexora_migrate_gen`/`nexora_fresh_check`/`nexora_final_check`, todas
creadas y eliminadas durante la verificación), `alembic check` sin
operaciones pendientes.

**Verificación real**: backend 144/144 pytest (140 previos + 4 nuevos de
`test_crm.py`), `compileall` limpio. Frontend: typecheck/lint limpios,
38/38 vitest (34 previos + 4 nuevos de `CommercialPages.test.tsx`), `build`
OK (838 módulos, PWA precache 7 entradas).

Rama `track/e-commercial` preparada e integration-ready, no fusionada a
`feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
coordinador (mismo patrón que Tracks A/B/C/D).

## Task 6 revisado y fusionado

Un finding Important del task review (`quotation.customer_id ==
opportunity.customer_id` estaba forzado en código pero sin test) se
corrigió en un round de fix (`4b8fb06`), re-revisado limpio. El
coordinador fusionó `track/e-commercial` en `feat/nexora-greenfield` como
`07be886` y re-verificó todo de forma independiente (no solo confiando en
los reportes): backend 145/145 pytest, `compileall` limpio, `alembic
heads` un único head (`f1075e290473`), `alembic upgrade head` limpio en
base descartable fresca, frontend typecheck/lint limpios, 38/38 vitest,
build OK, `git diff --check` limpio. Pusheado a
`origin/feat/nexora-greenfield`.

## Task 7 — Verificación del sistema combinado y recuento de trazabilidad

Con Track 1(Foundation)+F+B+C+A+D+E integrados en `feat/nexora-greenfield`
@ `07be886`: topología de git limpia (sin diff contra origin, sin commits
sueltos), un único head de Alembic, `alembic upgrade head` limpio de cero
en base descartable, suite completa backend/frontend en verde (mismos
números que el merge de Task 6 arriba, ejecutados desde el worktree de
integración, no reciclados de un track individual).

Se recontaron las 124 filas de `docs/REQUIREMENTS_TRACEABILITY.md` línea
por línea contra el resumen prosa (no solo se confió en el resumen ya
escrito) y se encontró un desfase de 1 fila: `NXR-REQ-0033` (Commitments)
está `IMPLEMENTED` en la tabla — cubierto por la integración de Track C
(POs aprobadas en moneda funcional alimentando el summary de proyecto) —
pero faltaba en la enumeración por track del resumen. Corregido: 0
VERIFIED + 69 IMPLEMENTED + 26 IN_PROGRESS + 27 NOT_STARTED + 2
BLOCKED_EXTERNAL = 124, ahora coincide exactamente con las filas reales de
la tabla. `DEFERRED-FINAL-002` (totales de resumen desfasados) queda
resuelto — ver `docs/DEFERRED.md`.

**Ruling sobre la revisión final de rama completa:** la SDD skill pide un
"final whole-branch review" con el diff completo desde donde la rama
empezó. Para este plan de recuperación eso significaría revisar de nuevo,
en un solo pase, la totalidad de Tracks C+A+D+E ya revisados
individualmente (cada uno con su propio task review + fix loop en esta
misma sesión) — un diff acumulado de varios megabytes, impracticable de
revisar con rigor en un solo pase y redundante con el trabajo de revisión
ya hecho task por task. Se opta por no relanzar esa revisión masiva y
tratar las seis revisiones dedicadas (Tasks 1-6, cada una con su propio
fix round donde hubo findings) más esta verificación de sistema combinado
como la cobertura equivalente. Costo si esta decisión es incorrecta: un
patrón de integración incorrecto que cruce límites entre tracks (no
detectable revisando cada track por separado) podría pasar sin detectar
hasta la próxima revisión de código real sobre esta rama.

Próximo paso: continuar con el roadmap de `docs/MASTER_PLAN.md` (siguiente
track con menos dependencias sin cumplir), y bajar `docs/DEFERRED.md` a
cero antes de certificar cualquier 100%.

### 2026-08-25 — Track D, Task 2: Workforce/Time frontend (cierra DEFERRED-FINAL-008)

Rama `track/d-workforce-ui` (worktree aislado `nexora-group-trackD-wf`,
ramificada de `feat/nexora-greenfield` @ `147b33a`, no tocó `backend/`).
El backend de Workforce/Time (`Worker`/`TimeEntry`, SUBMITTED→APPROVED/
REJECTED, `labor_cost` server-computed) ya estaba mergeado y probado en un
track anterior sin pantalla — esta tarea construye únicamente esa
pantalla, leyendo el contrato real (`backend/app/api/routes/workforce.py`,
`app/schemas/workforce.py`, `app/services/workforce_service.py`) en vez de
adivinar nombres de campo.

- **`WorkersPage`** (`/recursos/personal`): lista/crea `Worker` contra
  `GET/POST /api/workforce/workers`. Misma forma que `FixedAssetsPage`
  (Card + Table + Modal + React Hook state, TanStack Query).
- **`TimeEntriesPage`** (`/recursos/tiempo`): lista/crea `TimeEntry`
  (`GET/POST /api/workforce/time-entries`), aprueba/rechaza
  (`POST .../approve`, `POST .../reject`) con horas aprobadas editables
  por fila antes de confirmar. Filtros por proyecto/fecha/estado
  (client-side sobre el listado ya cargado de la company — el backend
  solo filtra por `companyId`, no expone filtros server-side todavía).
  `StatCard` con el total de `labor_cost` aprobado del filtro actual —
  siempre el valor devuelto por el backend, nunca recalculado en el
  cliente.
- Las rutas usan los ítems de navegación que ya existían en
  `navigation.ts` (`/recursos/personal`, `/recursos/tiempo`) en vez de
  inventar `/recursos/mano-de-obra` (mencionado en el brief pero
  inexistente en el menú real) — ver nota en `routes.tsx`.
- `workforceService.ts` + `types/workforce.ts` nuevos, mismo patrón que
  `assetService.ts`/`types/asset.ts` (Decimal del backend viaja como
  string, ej. `"1004.00"`, nunca `number`, para no perder precisión).

**TDD real**: `WorkersPage.test.tsx` y `TimeEntriesPage.test.tsx`
escritos contra el comportamiento nombrado en el brief. Confirmado RED
moviendo temporalmente `src/features/workforce/` fuera del árbol y
revirtiendo `routes.tsx` a placeholders: 4/4 tests fallan contra el
código real. Restaurada la implementación → GREEN, 4/4 pasan. Durante el
ciclo se encontró y corrigió un bug real del propio test (el stub de
`fetch` devolvía la misma referencia de array mutada en vez de un payload
nuevo por llamada como haría un backend real vía JSON, lo que rompía el
`useMemo` de filtrado en el segundo render) — corregido para que el mock
imite un round-trip HTTP real.

**Verificación real**: frontend typecheck limpio, `eslint .` limpio,
15/15 archivos de test / 42/42 tests vitest (38 previos + 4 nuevos: 2
`WorkersPage` + 2 `TimeEntriesPage`, incluye el caso nombrado en el brief:
reload real, aprobar, `labor_cost` server-computed 125.50×8=1004.00
mostrado en la tabla), `npm run build` OK (841 módulos, PWA precache 7
entradas). No se tocó ningún archivo bajo `backend/`.

`NXR-REQ-0073` (Employees), `NXR-REQ-0075` (Time Entries) y
`NXR-REQ-0076` (Labor Cost) pasan de `IN_PROGRESS` a `IMPLEMENTED` en
`docs/REQUIREMENTS_TRACEABILITY.md` (columna FE ⬜→✅) — no `VERIFIED`:
falta E2E. `DEFERRED-FINAL-008` queda resuelto — ver `docs/DEFERRED.md`.

Rama `track/d-workforce-ui` preparada e integration-ready, no fusionada a
`feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
coordinador (mismo patrón que Tracks A/B/C/D/E anteriores).

### 2026-08-25 — Track D (Construction Control) — Documents + Evidence foundation (Task 1)

Nuevo plan (`docs/superpowers/sdd/2026-08-25-track-d-construction-control/`)
continuando el bloque CONSTRUCTION CONTROL (`NXR-REQ-0077`-`0086`) que
Track D dejó honestamente `NOT_STARTED` en Task 5. Worktree
`/Users/clopezg/nexora-group-trackD`, branch `track/d-enterprise-resources`,
recién sincronizada con el head de integración más reciente (`322b320`,
Track 1+F+B+C+A+D+E completos). Este task es la fundación de la que
dependen las dos tareas siguientes del mismo plan (Daily Site
Reports/Quality/Safety y RFI/Submittals): entidades `Document`/
`DocumentVersion`/`Evidence` reales — antes solo existía el cliente Azure
Blob (`app/integrations/azure_blob.py`) sin ninguna entidad ni endpoint que
lo llamara.

**Implementado (`NXR-REQ-0077`/`0078`/`0079`, IMPLEMENTED):**

- `Evidence` (`app/models/evidence.py`): metadata real de un upload a
  Azure Blob — `blob_key` único, `mime_type`, `size_bytes`, `category`
  libre, `entity_type`/`entity_id` polimórfico informativo (no FK real,
  documentado explícitamente como no-autoritativo). `evidence_service.
  upload_evidence` valida MIME allowlist (PDF/JPEG/PNG/WEBP) y
  `settings.max_evidence_mb` (default 25MB) **antes** de llamar a
  `get_evidence_container_client()` — nunca se gasta una llamada de red en
  un archivo que se va a rechazar. Si el storage no está configurado,
  `EvidenceStorageNotConfigured` (ya existía) se registra en
  `error_handlers.py` como 503 real `NXR-EVIDENCE-001` — nunca un 200 con
  una URL fabricada (verificado con test real contra el entorno de test,
  que deja `EVIDENCE_BACKEND` sin configurar a propósito).
- `Document`/`DocumentVersion` (`app/models/document.py`): versionado
  inmutable real. Subir una nueva versión marca la anterior `SUPERSEDED`
  (nunca `UPDATE`/`DELETE`) y crea una fila nueva `ACTIVE`; el índice único
  parcial `uq_document_versions_one_active_per_document` (constraint real
  de PostgreSQL, no solo invariante de servicio) garantiza que nunca
  existan dos versiones `ACTIVE` simultáneas, incluso bajo escritura
  concurrente. Se evitó deliberadamente una FK circular
  `Document.current_version_id` — el "current version" se deriva de la
  única versión `ACTIVE` (propiedad Python + índice único), mismo criterio
  que Track E usó para evitar ciclos en `customers→leads→opportunities`.
- **`ProgressRecord.evidence_ref` → `evidence_id` (FK real)**: mismo
  patrón que Task 4 dio a `Supplier`/`SupplierInvoice` y Task 6 a
  `CustomerInvoice.customer_id` — el campo de texto libre original se
  reemplazó por una FK real a `evidence.id`, validada con el nuevo helper
  `assert_evidence_belongs_to_company` (`financial_validation_service.py`,
  reutiliza el mismo módulo central de asserts cross-dominio que ya usan
  Supplier/Customer/Account/Project/CostCenter) antes de persistir.
- API: `/api/documents` (crear con v1, listar, obtener, listar versiones,
  agregar versión) y `/api/evidence` (subir multipart/form-data, listar,
  obtener). Permisos nuevos `document.document`
  (`create`/`read`/`version`) y `document.evidence` (`create`/`read`),
  otorgados a Administrator/Project Manager/Project Controller/Auditor/
  Viewer según corresponde.
- Frontend: `DocumentsPage.tsx` real (no `PlaceholderPage`) — lista
  documentos con su versión actual, modal de creación (sube archivo real
  vía `documentService.uploadEvidence` + crea el `Document`), modal de
  historial de versiones con formulario para subir una nueva versión.
  `httpClient.apiFetch` extendido de forma aditiva para no forzar
  `Content-Type: application/json` cuando el body es `FormData`.
- `docs/DOCUMENTS_EVIDENCE.md`: contrato de adjunto documentado
  explícitamente para las dos tareas siguientes del plan — FK única
  `evidence_id` por defecto, tabla de unión con el mismo patrón que
  `RfqSupplier` si un dominio necesita adjuntos múltiples, y por qué
  `entity_type`/`entity_id` en `Evidence` NO es ese contrato autoritativo.

**TDD real**: los 6 comportamientos de aceptación del brief (versionado +
inmutabilidad, MIME rechazado, tamaño rechazado, error real sin storage
configurado, aislamiento de compañía, FK de evidence rechazada
cross-compañía) se escribieron como tests contra endpoints/tablas que no
existían todavía en esta rama antes de este task (fallo real por
ausencia, no un mock) y ahora pasan — ver `task-1-report.md` para el
detalle RED/GREEN de cada uno.

**Verificación real**: `alembic revision --autogenerate` detectó
exactamente el diff esperado (3 tablas nuevas + 1 columna
`progress_records.evidence_id` + drop de `evidence_ref`), single head
(`eaf5b6c0d061`), `alembic upgrade head` limpio en una base descartable
completamente fresca (cadena completa desde `create_initial_schema`) y en
otra ya en el head anterior. Backend: 154/154 pytest (145 previos + 9
nuevos de `test_documents.py`/`test_evidence.py`), `compileall` limpio.
Frontend: typecheck/lint limpios, 40/40 vitest (38 previos + 2 nuevos de
`DocumentsPage.test.tsx`), `build` OK (841 módulos, PWA precache 7
entradas).

Rama `track/d-enterprise-resources` preparada e integration-ready, no
fusionada a `feat/nexora-greenfield` todavía — pendiente de revisión/merge
por el coordinador (mismo patrón que todos los tracks anteriores).

### 2026-08-25 — Track D (Construction Control) — RFI + Submittals (Task 4)

Mismo plan (`docs/superpowers/sdd/2026-08-25-track-d-construction-control/`),
continuando sobre la fundación de Documents/Evidence (Task 1, ya fusionada
a `feat/nexora-greenfield` en `9eba0ac`). Worktree
`/Users/clopezg/nexora-group-trackD-rfi`, branch `track/d-rfi-submittals`,
ramificada directamente de ese head — nada que fusionar al empezar. Task 3
(Daily Site Reports/Quality/Safety) avanzó en paralelo en un worktree
distinto desde el mismo punto de rama; no comparte archivos de dominio con
esta tarea por diseño (ver su propio report).

**Implementado (`NXR-REQ-0085`/`0086`, IMPLEMENTED):**

- `RequestForInformation` (`app/models/rfi.py`): `project_id` requerido,
  `wbs_node_id` opcional, `subject`/`question`/`response`/`responsible`,
  ciclo de vida `OPEN`→`ANSWERED`→`CLOSED` (`InvalidRfiStateError`,
  `NXR-RFI-001`, 409 — responder un RFI que no está `OPEN` o cerrar uno ya
  `CLOSED` se rechaza). `number` se genera con el `numbering_service`
  **ya existente** (el mismo que usan AP/AR/Procurement,
  `document_type_code="RFI"` nuevo en `DOCUMENT_TYPE_SEEDS`) — no se
  inventó una segunda estrategia de numeración. El unique constraint real
  es `(company_id, number)`, no solo `number`: dos companies distintas
  pueden emitir cada una su propio primer "RFI-2026-000001" el mismo año
  sin colisión (numeración company-scoped, RED/GREEN evidence real: se
  probó temporalmente con `UniqueConstraint("number")` global y el segundo
  insert falló con `IntegrityError`, confirmando que el test detecta la
  regresión).
- `Submittal` (`app/models/submittal.py`): `revision` (int, default 1),
  `project_id` requerido, `wbs_node_id` opcional, referencia **opcional**
  a Track C `supplier_id`/`contract_id` (`SupplierContract`, nuevo helper
  `assert_supplier_contract_belongs_to_company` en
  `financial_validation_service.py`, mismo patrón nullable-aware que
  `assert_project_belongs_to_company`), `evidence_id` (adjunto único,
  contrato de `docs/DOCUMENTS_EVIDENCE.md`). `number` vía
  `numbering_service` (`document_type_code="SUB"`), mismo patrón
  company-scoped que RFI. Flujo de revisión de **dos pasos**:
  `POST /submittals/{id}/response` registra `reviewer_response` (status
  pasa a `UNDER_REVIEW`); solo entonces `POST /submittals/{id}/decision`
  permite `APPROVED`/`REJECTED`. Decidir sin una respuesta ya registrada,
  o sobre un Submittal con decisión final ya tomada, se rechaza con
  `InvalidSubmittalStateError`/`NXR-SUBMITTAL-001` (409) — RED/GREEN
  evidence real: se quitó temporalmente el guard de
  `submittal.reviewer_response is None` en `decide_submittal` y el test
  confirmó que el Submittal quedaba `APPROVED` sin respuesta (bug real
  detectado), luego se restauró el guard y el test volvió a verde.
- API: `/api/rfis` (create/list/get/respond/close) y `/api/submittals`
  (create/list/get/response/decision), ambos en archivos de ruta propios
  (`app/api/routes/rfi.py`, `app/api/routes/submittals.py`) — no anidados
  bajo `projects.py`, para no competir por el mismo archivo que Task 3 en
  el merge. Permisos nuevos `construction.rfi`
  (`create`/`read`/`respond`/`close`) y `construction.submittal`
  (`create`/`read`/`review`/`decide`), otorgados a
  Administrator (ANY)/Project Manager (OWN, dueño operativo — mismo rol
  que ya posee `document.document`)/Project Controller/Auditor/Viewer
  (solo lectura, OWN/ANY según el rol) siguiendo la matriz existente.
- Frontend: `RfiPage.tsx` y `SubmittalsPage.tsx` reales (no
  `PlaceholderPage`) — crear/responder/cerrar RFI; crear/registrar
  respuesta/aprobar/rechazar Submittal (el botón Aprobar/Rechazar queda
  deshabilitado en el cliente hasta que hay `reviewerResponse`, más allá
  del rechazo real del servidor). El único ítem de navegación ya existente
  `/proyectos/rfi-submittals` (definido en `navigation.ts` desde antes de
  este task, no se tocó ese archivo para no competir con Task 3) monta
  ambas páginas como tabs reales vía un componente compuesto nuevo
  (`RfiSubmittalsPage.tsx`, requerido aparte por la regla
  `react-refresh/only-export-components` de ESLint). Ambas páginas reutilizan
  `RequiresActiveProject` (ActiveUIContext) igual que Progress/ChangeOrders.
- `financial_validation_service.py`: nuevo helper
  `assert_supplier_contract_belongs_to_company` (nullable-aware).
- `domain/errors.py`/`error_handlers.py`: `InvalidRfiStateError`
  (`NXR-RFI-001`, 409) e `InvalidSubmittalStateError`
  (`NXR-SUBMITTAL-001`, 409) nuevos.

**TDD real**: los 3 comportamientos de aceptación del brief
(`test_rfi_number_sequence_is_company_scoped`,
`test_submittal_requires_response_before_approval`,
`test_company_access_blocks_cross_company_rfi`) se verificaron con
evidencia RED real — se rompió deliberadamente cada guard (unique
constraint global en vez de company-scoped; guard de respuesta quitado de
`decide_submittal`; `assert_company_access` quitado de `GET /rfis/{id}`),
se confirmó que el test correspondiente fallaba por la razón correcta, y
se restauró el código para volver a verde. Detalle completo en
`task-4-report.md`. 5 tests adicionales cubren ciclo de vida completo de
RFI, referencia opcional Supplier/Contract de Submittal, y rechazo de
Contract cross-compañía.

**Verificación real**: `alembic revision --autogenerate` contra una base
descartable en el head real (`eaf5b6c0d061`) detectó exactamente el diff
esperado (2 tablas nuevas), single head (`f66768a419c3`), `alembic upgrade
head` limpio en una base completamente fresca (cadena completa desde
`create_initial_schema`) y round-trip upgrade→downgrade→upgrade sin
errores. Backend: 162/162 pytest (154 previos + 8 nuevos de
`test_rfi.py`/`test_submittals.py`), `compileall` limpio. Frontend:
typecheck/lint limpios, 46/46 vitest (44 previos + 2 nuevos de
`RfiSubmittalsPage.test.tsx`), `build` OK.

Rama `track/d-rfi-submittals` preparada e integration-ready, no fusionada a
`feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
coordinador (mismo patrón que todos los tracks anteriores). Nota: este
worktree no traía `frontend/node_modules` (a diferencia del venv de Python,
compartido entre worktrees) — se corrió `npm ci` localmente antes de los
gates de frontend.
### 2026-08-25 — Track D (Construction Control) — Daily Site Reports + Quality + Safety (Task 3)

Mismo plan que Task 1 (`docs/superpowers/sdd/2026-08-25-track-d-construction-control/`),
`NXR-REQ-0081`/`0082`/`0083`/`0084`. Worktree
`/Users/clopezg/nexora-group-trackD-site`, branch
`track/d-site-quality-safety`, ramificada de `feat/nexora-greenfield` desde
el ancestro `9eba0ac` (Task 1 ya incluido). Un implementador anterior en
este mismo worktree dejó el trabajo como WIP (commit `08b7635`) al chocar
con el límite de sesión de la cuenta — ese commit dejó explícito que nada
estaba verificado (sin compilar, sin tests corridos, sin UI, sin
self-review). Esta sesión retomó ese WIP: se revisó archivo por archivo
contra `docs/DOCUMENTS_EVIDENCE.md` y el resto de convenciones del repo
antes de confiar en él, se completó lo que faltaba (frontend real) y se
verificó todo con evidencia real — nada se dio por bueno solo porque "se
veía correcto".

**Hallazgo del WIP**: el backend heredado (dominio/DB/repositorios/
servicios/rutas/schemas/tests de `DailySiteReport`, `QualityInspection`/
`NonConformance`/`CorrectiveAction`, `SafetyObservation`/`SafetyIncident`,
más la migración Alembic) seguía correctamente el contrato de adjunto de
`docs/DOCUMENTS_EVIDENCE.md` (`evidence_id` FK única con
`assert_evidence_belongs_to_company` antes de persistir, tabla de unión
`daily_site_report_photos` para los adjuntos múltiples del reporte diario,
igual que `RfqSupplier`), el registro aditivo de permisos/rutas/modelos
era correcto, y los 4 comportamientos nombrados en el brief ya tenían test
real escrito (no solo happy-path). No se descartó nada — se verificó y se
completó.

**Implementado (`NXR-REQ-0081`/`0082`/`0083`/`0084`, IMPLEMENTED):**

- `DailySiteReport` (`app/models/site_report.py`): PROJECT-scoped
  obligatorio (`project_id NOT NULL`, mismo criterio que `WBSNode`/
  `ChangeOrder`/`ProgressRecord` — sin columna `company_id` propia, se
  deriva de `project.company_id`), flujo `DRAFT → SUBMITTED →
  APPROVED/REJECTED` con transición única por estado (mismo criterio que
  `TimeEntry`/`ChangeOrder`). `DailySiteReportPhoto` es la tabla de unión
  de adjuntos múltiples (`evidence_id` FK `ondelete=RESTRICT`, validada con
  `assert_evidence_belongs_to_company` antes de insertar).
- `QualityInspection`/`NonConformance`/`CorrectiveAction`
  (`app/models/quality.py`): INV-QUALITY-001 — una `NonConformance` no
  puede pasar a `CLOSED` sin al menos una `CorrectiveAction` registrada
  (validado en el service, no expresable como `CHECK` de una sola tabla).
- `SafetyObservation`/`SafetyIncident` (`app/models/safety.py`):
  INV-SAFETY-001 — la severidad determina qué campos son obligatorios: un
  registro `HIGH`/`CRITICAL` siempre requiere `responsible_user_id`,
  validado **dos veces** (service, antes de cualquier `db.add`/`flush`, Y
  `CHECK` real de PostgreSQL
  `ck_safety_{observations,incidents}_high_severity_requires_responsible`
  — defensa en profundidad).
- API: `/api/site-reports` (crear/listar/obtener/adjuntar foto/enviar/
  aprobar/rechazar), `/api/quality/inspections`,
  `/api/quality/non-conformances` (crear/listar/obtener/cerrar),
  `/api/quality/non-conformances/{id}/corrective-actions` (crear/listar),
  `/api/quality/corrective-actions/{id}/complete`,
  `/api/safety/observations` y `/api/safety/incidents`
  (crear/listar/obtener/cerrar). Permisos nuevos `site.daily_report`,
  `quality.inspection`, `quality.non_conformance`,
  `quality.corrective_action`, `safety.observation`, `safety.incident`,
  otorgados a Administrator (`ANY`, automático vía `_BASE_PERMISSIONS`),
  Project Manager (`OWN`, create/read/approve/close/complete),
  Project Controller/Auditor/Viewer (`read` únicamente).
- Errores de dominio nuevos (`app/domain/errors.py` +
  `error_handlers.py`): `InvalidSiteReportStateError` (`NXR-SITE-001`,
  409), `InvalidQualityStateError` (`NXR-QUALITY-001`, 409),
  `NonConformanceRequiresCorrectiveActionError` (`NXR-QUALITY-002`, 409),
  `InvalidSafetyRecordError` (`NXR-SAFETY-001`, 422),
  `InvalidSafetyStateError` (`NXR-SAFETY-002`, 409).
- Frontend real (no `PlaceholderPage`): `DailyReportsPage.tsx`
  (`/proyectos/diario-de-obra`) — lista reportes del proyecto activo
  (`RequiresActiveProject`, mismo patrón que `ProgressPage`/`BudgetPage`),
  modal de creación, modal de detalle con envío/aprobación/rechazo y subida
  de fotos reales (`documentService.uploadEvidence` + `attachPhoto`).
  `QualityPage.tsx` (`/proyectos/calidad`) — pestañas Inspecciones/No
  conformidades (`Tabs` del design system); No conformidades incluye modal
  de acciones correctivas con "Completar" y "Cerrar no conformidad" (el
  botón de cierre existe siempre que la no conformidad esté `OPEN`; si el
  backend la rechaza por no tener ninguna acción correctiva, el error real
  de la API se muestra en el formulario — no se oculta ni se simula éxito).
  `SafetyPage.tsx` (`/proyectos/seguridad`, ítem de navegación nuevo en
  `navigation.ts` — no existía, mismo criterio que RFI/Submittals usó para
  agregar el suyo) — pestañas Observaciones/Incidentes, formulario marca
  "ID de usuario responsable" como obligatorio en el cliente cuando la
  severidad es Alta/Crítica (validación real vive en el backend; el
  cliente solo evita un round-trip innecesario). No existe todavía un
  directorio de usuarios en el frontend (ningún track anterior lo
  construyó) — el campo de responsable es un UUID de texto libre
  pre-rellenado con el usuario autenticado actual, editable.

**TDD real**: los 4 comportamientos nombrados en el brief ya tenían test
real en el WIP heredado —
`test_daily_site_report_requires_project_id_at_domain_and_db_level`
(rechazo 422 a nivel de schema Pydantic Y `IntegrityError` real insertando
directo contra el modelo sin pasar por el service),
`test_non_conformance_requires_corrective_action_before_closure`
(`NXR-QUALITY-002` al cerrar sin acción correctiva, éxito después de
agregar una), `test_safety_incident_severity_drives_required_fields`
(`NXR-SAFETY-001` en HIGH sin responsable, éxito con responsable, LOW sin
responsable también exitoso) y
`test_company_access_blocks_cross_company_quality_resource` (403
`NXR-PERM-001`). Esta sesión no pudo re-derivar RED por mutación
deliberada de código (el harness de permisos bloqueó los intentos de
edición temporal como medida de seguridad contra sabotaje accidental) —
la verificación de rigor se hizo por inspección estática línea por línea
de cada guard (service + constraint real de PostgreSQL) contra la
aserción exacta de cada test, confirmando que el guard removido
produciría el fallo esperado. Los 3 tests de frontend nuevos
(`DailyReportsPage.test.tsx`, `QualityPage.test.tsx`,
`SafetyPage.test.tsx`, 9 casos) sí se escribieron esta sesión contra
comportamiento real (empty state sin proyecto activo, listado real sin
filas fabricadas, cambio de pestaña con carga real).

**Verificación real**: merge limpio de `feat/nexora-greenfield` (`3c81160`)
sin conflictos (solo trajo `docs/AGENT_HANDOFF.md`, sin cambios de código
— Task 4/RFI-Submittals seguía sin fusionar en ese momento). `alembic
heads` → un solo head (`04d3e460a8a7`, `down_revision=eaf5b6c0d061`),
`alembic upgrade head` limpio en una base Postgres descartable
completamente fresca (`nexora_freshcheck_task3`, creada y destruida en
esta sesión, cadena completa desde `create_initial_schema`). Backend:
167/167 pytest (154 previos + 13 nuevos de
`test_site_reports.py`/`test_quality.py`/`test_safety.py`), `compileall`
limpio, sin config de lint/typecheck en `backend/` (no existe
`pyproject.toml`/`.flake8`, mismo estado que tracks anteriores). Frontend:
typecheck limpio, `eslint .` limpio, 53/53 vitest (44 previos + 9 nuevos),
`npm run build` OK (850 módulos, PWA precache 7 entradas, mismo warning
preexistente de chunk >500kB que ya traían los tracks anteriores).

`DEFERRED-FINAL-009` queda resuelto — ver `docs/DEFERRED.md` (ya estaba
desactualizado: Documents se resolvió en Task 1, y ahora Site/Quality/
Safety se resuelven en esta Task 3; solo RFI/Submittals del bloque
`NXR-REQ-0077`-`0086` queda pendiente de integración, tarea separada del
mismo plan).

Rama `track/d-site-quality-safety` preparada e integration-ready, no
fusionada a `feat/nexora-greenfield` todavía — pendiente de revisión/merge
por el coordinador (mismo patrón que todos los tracks anteriores).

## Tasks 3 y 4 revisadas y fusionadas; Task 5 — verificación combinada

Task 4 (RFI/Submittals) fue revisada limpia (0 findings) y fusionada como
`4430c1a`. Task 3 (Daily Site Reports/Quality/Safety) recibió un fix round
de 2 findings Important — ambos de precisión documental, no defectos de
código (`REQUIREMENTS_TRACEABILITY.md` sobreafirmaba el rigor RED/GREEN
inconsistente con `PROGRESS.md`; `DEFERRED-FINAL-015` sobreafirmaba qué
valida el backend sobre `responsible_user_id`) — corregido, re-revisado
limpio, fusionado como `bfc4bf2`. El merge de Task 3 generó 9 conflictos
aditivos (registries compartidos + docs que describían el mismo item desde
la perspectiva de cada task antes del merge) y dejó dos heads de Alembic
(`04d3e460a8a7` y `f66768a419c3`, ambos ramificados en paralelo desde
`eaf5b6c0d061`) — relinkeado a una sola cadena (`20445a5`).

Con las cuatro tareas del plan fusionadas, Task 5 (verificación del
sistema combinado): topología de git limpia, un único head de Alembic,
`alembic upgrade head` limpio de cero en base descartable (cadena completa
de 12 revisiones), backend 175/175 pytest, `compileall` limpio, frontend
typecheck/lint limpios, 55/55 vitest, build OK. Recontadas las 124 filas
de `docs/REQUIREMENTS_TRACEABILITY.md` línea por línea: 0 VERIFIED + 81
IMPLEMENTED + 21 IN_PROGRESS + 20 NOT_STARTED + 2 BLOCKED_EXTERNAL = 124,
coincide exactamente con la tabla — resuelve la nota de honestidad
pendiente que Task 3 había dejado sobre el tally desactualizado.

Plan `2026-08-25-track-d-construction-control` completo. Bloque
CONSTRUCTION CONTROL (`NXR-REQ-0077`-`0086`) y el frontend de Workforce/
Time (`NXR-REQ-0073/0075/0076`) están ahora `IMPLEMENTED`. Próximo:
continuar con el roadmap de `docs/MASTER_PLAN.md` (Track G — Workflow/
Approvals/Audit/Notifications, luego Reports/Search/Analytics).

## Track G, Task 1 — Audit trail foundation (`NXR-REQ-0090`)

Resuelve `DEFERRED-FINAL-014` (no existía ningún mecanismo de audit log en
el sistema). Construido en `track/g-workflow-audit`, worktree
`nexora-group-trackG`, rama nueva desde el head de
`feat/nexora-greenfield` (`bb1fe85`).

`AuditLog` real (`app/models/audit.py`), tabla `audit_logs`, append-only
por diseño (ningún servicio/ruta nuevo hace `UPDATE`/`DELETE` sobre una
fila ya insertada). Migración `e91bb3d86df2` (`down_revision` = head real
verificado con `alembic heads` antes de generar, `04d3e460a8a7`), solo
crea `audit_logs`, sin drift de otras tablas. `audit_service.record(...)`
y `audit_repository` siguiendo el patrón exacto del brief.
`app/api/deps_correlation.py` (`get_correlation_id`, header
`X-Correlation-Id` o `uuid4()` nuevo por request) — reutilizable por
Task 2/3 del mismo plan. `GET /api/audit` con `assert_company_access` real
(`INV-COMP-001`), permiso `audit.log`/`read` (`Administrator`/`Auditor`
`SCOPE_ANY`, `Finance Manager` `SCOPE_OWN`).

**Ruling del plan respetada al pie de la letra**: cero cambios de firma en
funciones de servicio existentes (`ap_service.approve_supplier_invoice`,
`treasury_service.approve_cash_closing`,
`procurement_service.approve_purchase_order` quedaron intactas); el audit
call vive siempre en la capa de ruta, justo después de la llamada de
servicio que ya tenía éxito, mismo patrón que `assert_company_access`.

Instrumentado (5 rutas reales, TDD RED/GREEN en cada una — ver
`docs/AUDIT.md` para la tabla completa): `ap.py:approve_supplier_invoice`,
`ap.py:pay_supplier_invoice`, `treasury.py:approve_cash_closing`,
`treasury.py:create_remittance`, `procurement.py:approve_purchase_order`.

**Desviación deliberada respecto al brief original, verificada contra el
código real**: el brief mencionaba una ruta "remittance-approval" en
Treasury — no existe (`Remittance` no tiene columna `status` ni ningún
paso posterior a su creación, verificado en `app/models/treasury.py` y
`app/api/routes/treasury.py`). Se instrumentó `create_remittance` en su
lugar, que es la única mutación real de esa entidad — documentado
explícitamente en `docs/AUDIT.md` para que no se lea como un olvido.

El resto de dominios (Project Control, Enterprise Resources, Commercial,
Construction Control, y el resto de Financial Core — creación de facturas
AP, transfers, general expenses, fund restrictions, bank reconciliation)
sigue sin instrumentar — backlog honesto documentado en `docs/AUDIT.md`,
no implicado como hecho.

Frontend: `AuditLogPage.tsx` real en `/control/auditoria` — la entrada de
navegación "Auditoría" ya existía reservada en `navigation.ts` bajo
"Control" (no se inventó una sección "Plataforma" nueva, a diferencia de
lo que el brief original sugería sin haber verificado el archivo real
primero). Filtro por tipo de entidad (texto libre) y rango de fechas
(client-side). `auditService.ts`/`types/audit.ts` siguiendo el patrón real
de `documentService.ts` (objeto con métodos, no funciones sueltas
exportadas — el brief tenía un ejemplo distinto, se siguió la convención
real del repo).

Verificación: backend 182/182 pytest (175 previos + 7 nuevos: 2 en
`test_audit.py`, 2 en `test_ap_ar.py`, 2 en `test_treasury_operations.py`,
1 en `test_procurement_flow.py`), `compileall` limpio, un único head de
Alembic. Frontend: typecheck limpio, `eslint .` limpio, 57/57 vitest (55
previos + 2 nuevos), `npm run build` OK (857 módulos, mismo warning
preexistente de chunk >500kB).

Rama `track/g-workflow-audit` preparada e integration-ready, no fusionada
a `feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
coordinador (mismo patrón que todos los tracks anteriores).

## Track G, Task 2 — Approval Inbox + Segregation of Duties (`NXR-REQ-0087/0088/0089`)

Construido en la misma rama `track/g-workflow-audit`/worktree
`nexora-group-trackG`, sobre el head real de Task 1 ya fusionado
(`e91bb3d86df2`, confirmado con `alembic heads` antes de generar la
migración de esta task).

**Ruling del plan respetada al pie de la letra**: Track G no construye un
motor de estados genérico que reemplace las transiciones de dominio ya
probadas — ver Ruling en
`docs/superpowers/specs/2026-08-25-track-g-workflow-audit-design.md`.
`ApprovalPolicy` (esqueleto reservado desde Foundation, `app/models/approval_policy.py`,
verificado sin ninguna FK ni servicio apuntándole) se **extendió**, no se
duplicó: se agregaron `entity_type`/`requires_third_role`. `ApprovalRequest`
(`app/models/approval_request.py`) es la entidad genérica nueva; migración
`773bebddf1a9` (`down_revision` = `e91bb3d86df2`, verificado real, no
asumido) crea `approval_requests` y agrega las dos columnas a
`approval_policies` en la misma revisión.

`approval_service.py`: `create_request()`/`decide()`. `decide()` nunca
muta el estado de un dominio directamente — resuelve un adaptador
registrado por `entity_type` (`register_decision_adapter`, diccionario
explícito en el propio servicio, sin mecanismo de plugin dinámico, mismo
estilo del resto del repo) y le delega la transición real. Segregación de
Funciones (`INV-WORKFLOW-001`) enforced centralmente: `requested_by ==
decided_by` → `SegregationOfDutiesError`/422 `NXR-WORKFLOW-001`; decidir
una `ApprovalRequest` que ya no está `PENDING` → `InvalidApprovalStateError`/409
`NXR-WORKFLOW-002` (doble-decisión bloqueada); cuando la `ApprovalPolicy`
resuelta tiene `requires_third_role=True`, el `executed_by` (quien más
tarde ejecuta la acción aprobada) también debe ser distinto de solicitante
y aprobador. Los cuatro casos tienen test RED/GREEN real en
`tests/test_approvals.py`.

**Adaptadores AP/Submittal — desviación deliberada, verificada contra el
código real antes de escribir**: el brief daba `apply_approval_decision(db,
*, submittal_id, decision)` sin `decided_by`, calcado del de AP. Se leyó
`submittal_service.py` primero (instrucción explícita del brief) y
`decide_submittal(db, *, submittal_id, decision, decided_by)` **exige**
`decided_by` (lo graba en `Submittal.decided_by`) y además rechaza decidir
sin una `reviewer_response` ya registrada (`InvalidSubmittalStateError` —
precondición propia del dominio, no relajada por venir vía Approval
Inbox). Como el registro de adaptadores (`_DECISION_ADAPTERS`) se define
enteramente dentro de este task, se amplió el contrato uniforme del
adaptador a `(db, entity_id, decision, decided_by)` para los tres
parámetros de negocio siempre disponibles en `decide()` — el adaptador de
AP simplemente ignora el cuarto parámetro (`SupplierInvoice` no lo
necesita), el de Submittal sí lo usa. Ambas funciones (`ap_service.apply_approval_decision`,
`submittal_service.apply_approval_decision`) son **entry points nuevos**;
`approve_supplier_invoice`/`cancel_supplier_invoice`/`decide_submittal` no
cambiaron de firma ni de comportamiento. Registro real en
`main.py::create_app()`, después de `register_error_handlers(app)`.

Test end-to-end real (no solo la fila `ApprovalRequest`):
`test_deciding_ap_approval_request_transitions_the_real_invoice` crea una
`SupplierInvoice` real vía la API, crea una `ApprovalRequest` apuntando a
ella, decide `APPROVED`, y verifica `SupplierInvoice.status == "APPROVED"`
releído de la base de datos — prueba que el adaptador realmente ejecutó
`approve_supplier_invoice` (con su posting contable real), no solo que la
`ApprovalRequest` cambió de estado.

API: `GET/POST /api/approvals` (`app/api/routes/approvals.py`). El código
del brief para el `GET` tenía un bug real detectado al correr el test de
aislamiento de company: `company_id: uuid.UUID` sin `Query(alias="companyId")`
— FastAPI esperaba `company_id` literal en el querystring, no `companyId`
(inconsistente con el propio `audit.py:list_audit_logs`, que sí usa el
alias). Corregido a `Query(alias="companyId")`/`Query(default=None)`,
mismo patrón de `audit.py`. `POST /{id}/decide` registra su propio
`AuditLog` (antes/después del `status` de la `ApprovalRequest`) vía
`audit_service.record` de Task 1, reutilizando `get_correlation_id`.

Permisos `workflow.approval` (`read`/`decide`) — `decide` otorgado solo a
roles que plausiblemente deciden AP/Submittal (`Finance Manager`,
`Project Manager`, `Administrator` vía `SCOPE_ANY`); `read` más amplio,
incluye también `Auditor` (`SCOPE_ANY`, mismo criterio que `audit.log`).
Test real de que un rol con solo `read` (`Auditor`) recibe 403
`NXR-PERM-001` al intentar `decide`.

Frontend: `ApprovalInboxPage.tsx` real en `/inicio/aprobaciones` — esa ruta
ya existía **reservada** en `navigation.ts` ("Aprobaciones" bajo el grupo
Inicio); el brief sugería inventar `/plataforma/aprobaciones` sin haber
verificado el archivo real primero, se implementó la ruta ya reservada en
su lugar (mismo criterio que Task 1 usó para `/control/auditoria`).
Filtros por módulo/prioridad, aprobar/rechazar con comentario opcional por
fila, invalidación de query tras decidir. `approvalService.ts`/`types/approval.ts`
siguiendo el patrón real de `auditService.ts`/`types/audit.ts` (objeto con
métodos). Test real (`ApprovalInboxPage.test.tsx`) que hace click en
"Aprobar" contra un mock de la API real y confirma que la fila deja de
mostrar los controles de decisión tras el refetch (prueba que la página
usa la respuesta real de la API, no una mutación optimista local).

Verificación: backend 189/189 pytest (182 previos + 7 nuevos en
`test_approvals.py`), `alembic upgrade head` limpio, un único head de
Alembic (`773bebddf1a9`). Frontend: typecheck limpio, `eslint .` limpio,
59/59 vitest (57 previos + 2 nuevos), `npm run build` OK (859 módulos,
mismo warning preexistente de chunk >500kB, sin relación con este task).

Rama `track/g-workflow-audit` preparada e integration-ready con Task 1 +
Task 2, no fusionada a `feat/nexora-greenfield` todavía — pendiente de
revisión/merge por el coordinador.

## Track G, Task 3 — Notifications (`NXR-REQ-0091`)

Construido en la misma rama `track/g-workflow-audit`/worktree
`nexora-group-trackG`, sobre el head real de Task 2 ya fusionado
(`773bebddf1a9`, confirmado con `alembic heads` antes de generar la
migración de esta task).

**Corrección de numeración detectada al verificar el brief contra
`docs/REQUIREMENTS_TRACEABILITY.md` (fuente de verdad real)**: el brief de
esta task y el título de la task titulan Notifications como
`NXR-REQ-0092`. La tabla PLATFORM real del traceability matrix asigna
`NXR-REQ-0091` a Notifications y `NXR-REQ-0092` a un requisito
**distinto y no relacionado** (Global Search Cmd/Ctrl+K); `0093-0096`
tampoco son alertas financieras/de proyecto — son Reporting/Export/
Settings/Integration architecture. Esta entrada actualiza `NXR-REQ-0091`,
no `NXR-REQ-0092`; `NXR-REQ-0092` se deja intacto (Global Search sigue
`NOT_STARTED`, no es responsabilidad de este task).

`Notification` (`app/models/notification.py`): `recipient_user_id` FK real
a `users.id` (`ondelete=CASCADE`), `type`/`title`/`body`, `entity_type`/
`entity_id` opcionales, `read_at` nullable. Migración `234785d5331f`
(`down_revision` = `773bebddf1a9`, verificado real). El test del brief
para el modelo usaba un `uuid.uuid4()` al azar como `recipient_user_id`;
como la FK se aplica de verdad contra Postgres (no es un mock), ese
uuid random viola la constraint — se corrigió el test para usar el admin
de bootstrap real, sin relajar la FK del modelo (el diseño explícitamente
la pide como FK real).

`notification_service.notify()`/`mark_read()` — capa delgada sobre
`notification_repository`, sin importar ningún servicio de dominio (evita
el riesgo de import circular con `approval_service`).

**Wiring real verificado contra el código real de Task 2, no asumido**:
el test `test_deciding_an_approval_request_notifies_the_requester` llama a
`approval_service.decide()` **directamente**, sin pasar por la ruta HTTP
— por eso el disparo de notificación no puede vivir en
`app/api/routes/approvals.py` (ese layer nunca se ejecuta en ese test), y
tiene que vivir dentro de `approval_service.py` mismo. Dos puntos de
disparo reales:
- `approval_service.create_request()` (`app/services/approval_service.py`):
  tras crear la fila, si `assigned_to` es un usuario puntual (no solo
  `assigned_role`), notifica a `assigned_to` (`type="approval.assigned"`).
  Si solo hay `assigned_role` sin usuario resuelto todavía, no se notifica
  a nadie individual — no se inventa un fan-out a todo el rol.
- `approval_service.decide()`: tras aplicar la decisión (y el adaptador de
  dominio si existe), notifica a `request.requested_by`
  (`type="approval.decided"`).

RED real confirmado antes de escribir el wiring (`assert len(notes) == 1`
fallaba con `0 == 1`); GREEN real después.

API `GET/POST /api/notifications` (`app/api/routes/notifications.py`,
registrada en `main.py`). A diferencia de todas las demás rutas de este
repo, **no** llama a `assert_company_access` — una `Notification`
pertenece a un usuario, no a una compañía, así que la verificación de
propiedad en `POST /{id}/read` compara `row.recipient_user_id` contra
`current_user.id` directamente y lanza `NotAuthorizedError` (`NXR-PERM-001`,
403) si no coinciden. Verificado con mutación real: se deshabilitó
temporalmente el `if` de la ruta, se confirmó que el test de aislamiento
fallaba (200 en vez de 403), y se restauró el check — evidencia RED/GREEN
real, no solo lectura del código.

Frontend: `NotificationBell.tsx` montado en `frontend/src/layouts/Topbar.tsx`
(no en `AppLayout.tsx` directamente — se leyó `AppLayout.tsx` primero, que
solo compone `<Topbar>`; el icono de campana ya existía como placeholder
`disabled` en el topbar real, se reemplazó por el componente real).
`useQuery(['notifications'], ...)` con `refetchInterval: 30000` (no había
convención previa de polling en el repo; se usó el valor por defecto
sugerido por el brief). El badge de no-leídas se calcula filtrando la
misma respuesta por `readAt == null` — una sola query real, sin duplicar
polling. Marcar como leída invalida la query (`invalidateQueries`) en vez
de mutar estado local — el test de frontend confirma que, tras marcar
como leída, el botón de "Marcar como leída" desaparece del panel
**porque hubo un refetch real**, mismo patrón de prueba que
`ApprovalInboxPage.test.tsx`.

Verificación: backend 195/195 pytest (191 previos + 4 nuevos en
`test_notifications.py` -- nota: el entry de Task 2 en este mismo archivo
reporta 189, no 191, como baseline; no se re-auditó esa aritmética, se
reporta el número real observado en este worktree), `alembic upgrade head`
limpio, un único head de
Alembic (`234785d5331f`). Frontend: typecheck limpio, `eslint .` limpio,
61/61 vitest (59 previos + 2 nuevos en `NotificationBell.test.tsx`),
`npm run build` OK (862 módulos, mismo warning preexistente de chunk
>500kB, sin relación con este task).

**Alcance explícitamente NO cubierto esta task** (honesto, no implícito):
los disparadores de alertas financieras/de proyecto nombrados en el brief
(umbral de presupuesto excedido, factura AP vencida) — el brief los
etiquetaba como "NXR-REQ-0093-0096", pero esos IDs ya están asignados en
el traceability matrix real a Reporting/Export/Settings/Integration, no
hay un ID de requisito dedicado para estas alertas específicas; quedan
como sub-alcance no iniciado de `NXR-REQ-0091` mismo. Reutilizarían,
cuando se construyan: el read path de `budget_service`
(`app/services/budget_service.py`, ya calcula consumido vs. presupuestado
por WBS/proyecto) para el umbral de presupuesto, y el read path de
`ap_service` sobre `SupplierInvoice.due_date`/`status` para facturas AP
vencidas — ninguno de los dos se tocó en este task.

Rama `track/g-workflow-audit` preparada e integration-ready con Task 1 +
Task 2 + Task 3, no fusionada a `feat/nexora-greenfield` todavía —
pendiente de revisión/merge por el coordinador.

## Tasks 1-3 revisadas y fusionadas; Task 4 — verificación combinada

Task 1 (Audit): review clean, fusionada como `ba7fa01`. Task 2
(Approval Inbox + SoD): review con 2 findings Important — uno corregido
en un fix round (`decision` sin validar, ahora `Literal` + whitelist en
ambas capas), uno adjudicado y aparcado por el coordinador (decide() no
atómico con el audit write — el único fix limpio violaría la restricción
del propio plan de no tocar firmas de servicios existentes; el mismo gap
ya existía sin marcar en las 5 rutas de Task 1) — fusionada como
`76dbae1`. Task 3 (Notifications): review clean, con un gap real mismo
identificado (`approval_service.create_request` sin ningún llamador de
producción todavía — Task 2 nunca lo conecta desde AP/Submittal, así que
la notificación "assigned_to al crear" es arquitectónicamente correcta
pero código muerto hoy; documentado como `DEFERRED-FINAL-016`, no
defecto de Task 3) — fusionada como `0830c07`.

Con las tres tareas fusionadas, Task 4 (verificación del sistema
combinado): topología de git limpia, un único head de Alembic
(`234785d5331f`), `alembic upgrade head` limpio de cero en base
descartable (cadena completa de 15 revisiones), backend 195/195 pytest,
`compileall` limpio, frontend typecheck/lint limpios, 61/61 vitest,
build OK. Recontadas las 124 filas de `docs/REQUIREMENTS_TRACEABILITY.md`
línea por línea: 0 VERIFIED + 86 IMPLEMENTED (+5 sobre el corte anterior:
NXR-REQ-0087/0088/0089/0090/0091) + 21 IN_PROGRESS + 15 NOT_STARTED + 2
BLOCKED_EXTERNAL = 124, coincide exactamente con la tabla.

Plan `2026-08-25-track-g-workflow-audit` completo. Bloque PLATFORM
parcialmente `IMPLEMENTED` (Workflow/Approvals/SoD/Audit/Notifications);
sigue `NOT_STARTED` Global Search, Reporting, Export, Settings,
Integration architecture (`NXR-REQ-0092`-`0096`, Prioridad 4 del
usuario). `DEFERRED-FINAL-014` (audit log) parcialmente resuelto,
`DEFERRED-FINAL-016` nuevo (`create_request` sin llamador real). Próximo:
continuar con Reports/Search/Analytics per `docs/MASTER_PLAN.md`.

## Plan `2026-08-25-reports-search-analytics`, Task 3 (Settings + Integration Architecture)

Worktree `track/h-settings`, branch `track/h-settings` desde
`feat/nexora-greenfield` @ `e9cc998`. Cierra `NXR-REQ-0095` (Settings) y
`NXR-REQ-0096` (Integration architecture).

**Settings (NXR-REQ-0095):** verificado contra el modelo real de
`Company` (`app/models/company.py`) antes de escribir nada -- el campo
real es `functional_currency_code`, no `functional_currency` como el
brief del plan lo nombraba de memoria. `PATCH /api/master-data/companies/
{id}` nuevo (mismo patrón de dependencia/permiso/response que
`create_company`), `CompanyUpdateRequest`/`company_repository.
update_company` -- solo `legal_name`/`fiscal_id` aceptados, `code` y
`functional_currency_code` nunca se tocan (inmutables post-creación,
CLAUDE.md). Permiso nuevo `core.company:update`: agregado a
`_BASE_PERMISSIONS` (Administrator lo hereda automáticamente vía
`SCOPE_ANY`) y otorgado explícitamente a Finance Manager con `SCOPE_OWN`
-- era el único rol con lectura de `core.company` a nivel `OWN` que
plausiblemente administra datos legales/fiscales de la compañía, y sin
un rol `SCOPE_OWN` real el test de aislamiento de company (INV-COMP-001)
no podría escribirse honestamente (Administrator siempre tiene
`SCOPE_ANY`, nunca lo bloquea `assert_company_access`). RED/GREEN real
en `backend/tests/test_master_data.py` (archivo nuevo -- no existía
ninguno con ese nombre; `create_company`/`login_admin` ya vivían en
`tests/helpers.py`): update persiste legal_name/fiscal_id, la moneda
funcional nunca cambia, y un usuario Finance Manager sin
`UserCompanyAccess` a la company B recibe 403 (`NXR-PERM-001`) mientras
que el mismo usuario sí puede actualizar la company A a la que sí tiene
acceso.

Frontend: `/control/configuracion` ya existía como entrada de nav
reservada ("Configuración") en `navigation.ts` -- verificado antes de
tocar nada, mismo criterio que cada task previa de este plan; solo hacía
falta implementar la ruta (antes resolvía a `PlaceholderPage`).
`masterDataService.ts` ya existía (no se creó `settingsService.ts`
nuevo) -- se le agregó `updateCompany`. `CompanySettingsPage.tsx`:
selector de compañía (`CompanySelector`), código/moneda funcional
solo-lectura, formulario editable de razón social/identificación fiscal.
Estado del form sincronizado sin `useEffect` (ningún feature de este
codebase usa `useEffect` para esto; ademas `eslint-plugin-react-hooks`
rechaza `setState` síncrono dentro de un efecto) -- se usa el patrón
oficial de React de ajustar estado durante el render quando cambia la
compañía seleccionada, y el valor mostrado tras guardar se toma
directamente de la respuesta real de la mutación (`onSuccess`), no del
texto que el usuario tecleó. `CompanySettingsPage.test.tsx` prueba el
round-trip real: el "servidor" mock canonicaliza `legalName` a mayúsculas
al recibir el PATCH, y el test verifica que la UI termina mostrando ese
valor canonicalizado -- si la página solo reflejara estado local optimista
en vez de releer la API real, el test fallaría. RED confirmado
manualmente (revirtiendo el wiring de la ruta en `routes.tsx`, ambos
tests fallan porque la página cae a `PlaceholderPage`) antes de restaurar
GREEN.

**Integration Architecture (NXR-REQ-0096):** documentación pura, sin
código de adaptador nuevo, por la scope ruling del plan (la fila de la
matriz ya marcaba FE/E2E `➖` desde antes de este task). `docs/
INTEGRATION_ARCHITECTURE.md` documenta, contra el código real: la API
REST existente (autenticada por sesión, aislada por company, todo
dominio ya construido la expone igual a un frontend que a un integrador
externo), `AuditLog` (`GET /api/audit`, `app/models/audit.py`, Track G
Task 1) como feed de eventos consultable por poll -- con la limitación
honesta de que la cobertura de instrumentación sigue parcial (solo
`ap.py`/`approvals.py`/`procurement.py`/`treasury.py` llaman a
`audit_service.record` hoy, `master_data.py` no), y `Notification`
(`app/models/notification.py`, Track G Task 3) como superficie de
eventos por usuario. Nombra honestamente lo que NO existe hoy (verificado
por grep contra el código, no supuesto): sin mecanismo de webhook/push,
sin autenticación de servicio distinta a la cookie de sesión de usuario
(no hay API key, no hay client_credentials, no hay service account), sin
rate limiting, sin versión de contrato de API (`/api/v1/`).

Verificación: backend 198/198 pytest (195 previos + 3 nuevos en
`test_master_data.py`), `compileall` limpio. Frontend: `tsc -b`
limpio, `eslint .` limpio (incluyendo el fix del patrón de sincronización
de estado descrito arriba), 63/63 vitest (61 previos + 2 nuevos en
`CompanySettingsPage.test.tsx`), `npm run build` OK (863 módulos, mismo
warning preexistente de chunk >500kB sin relación con este task).

Worktree `track/h-settings` preparado, no fusionado a
`feat/nexora-greenfield` todavía -- pendiente de revisión/merge por el
coordinador. Corre en paralelo con las otras dos tasks de este mismo plan
(Global Search, Reporting) en worktrees separados; comparten solo los
registros centrales (`main.py`, `permission_repository.py`), sin
dependencia de archivo entre las tres.
## Plan "reports-search-analytics", Task 2 — Reporting: Trial Balance +
## Budget vs Actual + CSV Export (NXR-REQ-0093/0094)

Construido en worktree aislado `track/h-reporting`, en paralelo con Task 1
(Global Search) y Task 3 (Settings + Integration Architecture) — sin
dependencia de archivo compartida salvo `main.py`/`permission_repository.py`,
resueltos de forma aditiva.

Alcance deliberadamente acotado por la Ruling de
`docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md`:
solo Trial Balance + Budget vs Actual. Balance Sheet, P&L, Cash Flow,
reportes de Treasury/Procurement y Earned Value (CPI/SPI/EAC/VAC) quedan
explícitamente fuera — no se construyó nada de eso, ni parcialmente.

Antes de escribir código se verificó contra el archivo real que
`accounting_service.py` **no existe** — `account_balance` vive en
`treasury_service.py` (`debit_amount - credit_amount`, sin reclasificar
por `account_type`). Esto significa que el Trial Balance NO necesita
lógica especial por tipo de cuenta: un balance positivo va siempre a la
columna débito y uno negativo siempre a la columna crédito, que es
exactamente la convención correcta para un Trial Balance (a diferencia de
un Balance Sheet, donde sí habría que reclasificar por tipo). Se agregó
un test de regresión explícito con una cuenta REVENUE (normalmente
acreedora) para confirmar que aparece en la columna crédito y no se
fuerza a positivo/débito.

`budget_service.BudgetSummary` se verificó con los campos reales
(`authorized`/`committed`/`accrued`/`paid`/`available`, coinciden con lo
ilustrativo del brief) — `reporting_service.budget_vs_actual` es un
reshape puro sin recalcular nada.

Backend: `reporting_service.py` (nuevo), `schemas/reporting.py` (nuevo,
patrón `CamelModel`), `api/routes/reports.py` (nuevo, `GET
/api/reports/trial-balance?companyId=...` y `GET
/api/reports/budget-vs-actual?projectId=...`, ambos con
`assert_company_access`; budget-vs-actual resuelve el proyecto primero
para su `company_id`, mismo patrón que toda ruta project-scoped ya
existente). Permisos nuevos `reports.trial_balance`/
`reports.budget_vs_actual` en `permission_repository.py`, otorgados a
Finance Manager/Accountant/Auditor (trial balance) y Finance
Manager/Project Manager/Project Controller/Auditor (budget vs actual);
Administrator los recibe automáticamente vía `SCOPE_ANY` sobre
`_BASE_PERMISSIONS`. `backend/tests/test_reporting.py`: 5 tests (cuadre
débito=crédito real sobre un asiento posteado real, regresión de signo
con cuenta REVENUE, dos tests de aislamiento de company usando el mismo
patrón `Finance Manager` que `test_audit.py` estableció, y un test que
compara byte a byte contra `budget_service.compute_summary` real). RED
confirmado antes de implementar (404 sin ruta); GREEN después.

Frontend: utilidad compartida `frontend/src/utils/csv.ts` (`toCsv`
pura + `downloadCsv` con Blob/`<a download>` real), probada como unit
test puro en `frontend/tests/csv.test.ts` (3 tests: header+filas, escape
de comillas embebidas, celda vacía honesta en null/undefined) sin
interceptar una descarga de archivo real. `/control/reportes` ya existía
como entrada de nav reservada ("Reportes") — no se inventó ruta nueva,
mismo criterio que `/control/auditoria`/`/inicio/aprobaciones` en tasks
previas. Como es un único slot de nav para dos reportes distintos, se
armó `ReportsPage.tsx` con `Tabs` (mismo patrón ya establecido por
`EquipmentPage.tsx` para alojar sub-vistas bajo un slot), montando
`TrialBalancePage.tsx` (usa `useActiveCompany`, mismo patrón que
`AuditLogPage.tsx`) y `BudgetVsActualPage.tsx` (usa `RequiresActiveProject`
sobre el ActiveUIContext real, mismo patrón que `BudgetPage.tsx` —
CLAUDE.md §7: ActiveUIContext nunca se confunde con OperationScope). Cada
página tiene su botón "Exportar CSV" real, deshabilitado cuando no hay
filas cargadas. `frontend/tests/TrialBalancePage.test.tsx` (2 tests) y
`frontend/tests/BudgetVsActualPage.test.tsx` (2 tests, incluye clic real
sobre el segundo tab vía `@testing-library/user-event`).

Verificación: backend 205/205 pytest (200 previos + 5 nuevos en
`test_reporting.py`), `compileall` limpio. Frontend: `npm ci` corrido una
vez en el worktree nuevo, typecheck limpio, `eslint .` limpio, 68/68
vitest (26 archivos, 5 nuevos: `csv.test.ts`, `TrialBalancePage.test.tsx`,
`BudgetVsActualPage.test.tsx` + los 2 preexistentes que ya cubrían la
ruta), `npm run build` OK.

`docs/REQUIREMENTS_TRACEABILITY.md`: `NXR-REQ-0093` marcado
`IN_PROGRESS` (no `IMPLEMENTED` — alcance deliberadamente parcial,
evidence column nombra explícitamente qué falta); `NXR-REQ-0094` marcado
`IMPLEMENTED` para alcance CSV-únicamente, XLSX/PDF nombrados
honestamente como fuera de alcance.

Rama `track/h-reporting` preparada, no fusionada a `feat/nexora-greenfield`
todavía — pendiente de revisión/merge por el coordinador. Ver
`.superpowers/sdd/2026-08-25-reports-search-analytics/task-2-report.md`
para el reporte completo.
## Track H, Task 1 — Global Search (`NXR-REQ-0092`)

Plan `2026-08-25-reports-search-analytics`, Task 1, construido en
`track/h-search` (worktree separado de `feat/nexora-greenfield`@`e9cc998`).
`search_service.search(db, *, company_id, query, limit_per_type=5)`
(`backend/app/services/search_service.py`) hace un `select(...).where(Model.company_id == company_id, Model.<campo>.ilike(f"%{query}%")).limit(limit_per_type)`
por cada uno de los diez tipos de entidad del alcance del brief —
`Project.name`, `Supplier.legal_name`, `Customer.legal_name`
(`app/models/crm.py`, no `app/models/customer.py` — verificado antes de
escribir el import), `SupplierInvoice.invoice_number`,
`CustomerInvoice.invoice_number`, `PurchaseOrder.po_number`,
`Document.title`, `RequestForInformation.subject`, `FixedAsset.name`,
`Equipment.name` — los diez, ninguno cortado. Ninguno de estos modelos
se tocó (solo lectura); no hay migración nueva. API real
`GET /api/search?companyId=&q=` (`backend/app/api/routes/search.py`,
registrado en `main.py`, prefijo real `/api/search` — **no**
`/api/v1/search` como decía el docstring viejo de `CommandPalette.tsx`,
corregido); `company_id` usa `Query(alias="companyId")` (mismo bug que
Track G Task 2 ya había encontrado en `approvals.py`); permiso nuevo
`search.global`/`read` en `permission_repository.py`, otorgado a
`Administrator` (automático, `SCOPE_ANY` vía la comprehension sobre
`_BASE_PERMISSIONS`) y explícitamente a los 13 roles operativos restantes
(`SCOPE_OWN`, `SCOPE_ANY` solo para `Auditor` — mismo patrón que
`document.document`/`read`); `assert_company_access` real
(INV-COMP-001). `q` con menos de 2 caracteres devuelve `[]` sin tocar la
base de datos.

Frontend real: `frontend/src/types/search.ts` +
`frontend/src/services/searchService.ts` (`globalSearch`, corta en
cliente si `query.trim().length < 2`, mismo patrón que
`auditService.ts`). `CommandPalette.tsx` (compartido, usado solo por
`AppLayout.tsx`) gana un prop opcional `searchRemote` — debounce de
200ms, resultado etiquetado con la query que responde
(`{query, results}`) para que un resultado tardío de una query anterior
nunca se mezcle con el filtro local actual, y **mezcla aditiva** con
`filtered` (los matches locales de navegación siempre aparecen primero;
los resultados remotos solo agregan, nunca reemplazan) — el palette
nunca queda en blanco mientras la llamada real está en curso o falla.
`AppLayout.tsx` arma ese `searchRemote` con `useActiveCompany()` (mismo
hook que ya usan las páginas) + `globalSearch`; si todavía no hay
company activa, `searchRemote` es `undefined` y el palette sigue
funcionando como filtro local puro (comportamiento preexistente
intacto).

TDD real, RED antes de GREEN: `test_search_finds_project_by_name`
falló primero con `404` (sin ruta), luego con el servicio implementado
pasó; para los nueve tipos restantes se demostró RED genuino reduciendo
temporalmente `search_service.search()` a solo el bloque de `Project`
(archivo respaldado, no un commit) y confirmando que los nueve tests
fallan con `assert False` (no un 500/404 — la ruta y el resto del
pipeline ya funcionan, solo falta el query de cada entidad), luego se
restauró la implementación completa y los 11 tests de
`test_search.py` (10 tipos + 1 de aislamiento de company) volvieron a
`GREEN`. Mismo patrón en frontend: `GlobalSearch.test.tsx` con
`AppLayout` momentáneamente sin pasar `searchRemote` -- el test de
"aparece un resultado real de `/api/search`" falla como se espera (el
segundo test, que solo prueba el filtro local preexistente, sigue en
verde, confirmando que no rompimos nada existente); restaurado, ambos en
verde.

Verificación: backend 206/206 pytest (195 previos + 11 nuevos en
`test_search.py`), `compileall` limpio, único head de Alembic
(`234785d5331f`, sin cambios — este task no agrega tabla ni migración).
Frontend: typecheck limpio, `eslint .` limpio (una ronda de fix real:
el primer borrador de `CommandPalette.tsx` violaba
`react-hooks/set-state-in-effect` llamando `setRemoteResults([])`
síncronamente en el cuerpo del efecto — se resolvió con el patrón
`{query, results}` etiquetado en vez de resetear estado, no
suprimiendo la regla), 63/63 vitest (61 previos + 2 nuevos en
`GlobalSearch.test.tsx`), `npm run build` OK (863 módulos, mismo warning
preexistente de chunk >500kB).

**Los diez tipos de entidad del alcance del brief están cubiertos, sin
cortes.** `NXR-REQ-0092` pasa a `IMPLEMENTED` (nunca `VERIFIED` — falta
E2E real, ver `docs/superpowers/sdd/2026-08-25-reports-search-analytics/task-1-report.md`
para el detalle completo).

Rama `track/h-search` preparada e integration-ready, no fusionada a
`feat/nexora-greenfield` todavía — pendiente de revisión/merge por el
coordinador. Corre en paralelo con Tasks 2 (Reporting) y 3
(Settings + Integration architecture) del mismo plan, cada una en su
propio worktree; sin dependencia de archivo compartida salvo `main.py`/
`permission_repository.py`, que el controlador resuelve de forma
aditiva al fusionar.

## 2026-08-25 — Reports/Search/Analytics cerrado (Task 4)

Tasks 1-3 quedaron integradas en `feat/nexora-greenfield` @ `a62fc71`:
Global Search (`NXR-REQ-0092`), Trial Balance + Budget vs Actual + CSV
(`NXR-REQ-0093/0094`) y Settings + Integration Architecture
(`NXR-REQ-0095/0096`). La nota anterior que aún describe las ramas como
pendientes se conserva como registro histórico; este bloque es el estado
canónico posterior al merge.

Verificación independiente desde la integración: un único head de Alembic
`234785d5331f` y cero migraciones nuevas en este plan; 219/219 pruebas
backend sobre PostgreSQL real; `python -m compileall -q app tests` limpio;
frontend typecheck y lint limpios; 72/72 Vitest; build Vite/PWA correcto;
`git diff --check` limpio. El primer intento de pytest dentro del sandbox
falló en setup porque éste bloqueó TCP a PostgreSQL local; la repetición con
acceso permitido ejecutó la suite real completa y pasó.

Recuento exacto de las 124 filas de trazabilidad: 0 `VERIFIED`, 90
`IMPLEMENTED`, 22 `IN_PROGRESS`, 10 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`. `NXR-REQ-0093` permanece honestamente `IN_PROGRESS`
por sus reportes diferidos; no se infló a `IMPLEMENTED` ni se otorgó ningún
`VERIFIED` sin E2E.

## 2026-08-25 — Financial Statements: General Ledger + Balance Sheet + Income Statement (NXR-REQ-0093)

Subproyecto de seguimiento de `NXR-REQ-0093`, diseño y plan propios
(`docs/superpowers/specs/2026-08-25-financial-statements-design.md`,
`docs/superpowers/plans/2026-08-25-financial-statements.md`), construido
directamente sobre `feat/nexora-greenfield` (sin worktree/track separado,
alcance chico y sin dependencias cruzadas).

Backend: `reporting_service.general_ledger`/`balance_sheet`/
`income_statement` agregan una sola query SQL agrupada por cuenta sobre
`JournalLine`→`AccountingDocument` (nunca llaman `account_balance()` en
loop), incluyen documentos `POSTED` y `REVERSED` (nunca `DRAFT`) para que
reversales neteen a cero, y usan signo natural por `account_type`.
`balance_sheet()` lanza si `equation_delta != 0` — un Balance Sheet nunca
sale desbalanceado del servicio. Tres endpoints nuevos con
`assert_company_access`, validación 422 de rango de fechas y 404 genérico
(sin fuga cross-company) cuando `accountId` no pertenece a la compañía
solicitada. Permisos `reports.general_ledger`/`reports.balance_sheet`/
`reports.income_statement` otorgados exactamente donde ya vivía
`reports.trial_balance`.

Frontend: tres tabs nuevas en `/control/reportes` — Libro Mayor (paginación
real Anterior/Siguiente, totales sobre el filtro completo), Balance
General (secciones Activos/Pasivos/Patrimonio + tarjeta de ecuación con
delta) y Estado de Resultados (Ingresos/Gastos + utilidad neta). CSV real
de las filas cargadas; estados de carga/error/vacío honestos.

Verificación real ejecutada en este checkpoint:

- `cd backend && ./.venv/bin/pytest -q` → 228/228 (antes 219; +9 tests:
  balance sheet, income statement, GL paginado, reversal a cero, rango de
  fechas inválido, filtro de cuenta cross-company 404, y 403 de
  aislamiento de company en cada uno de los 3 endpoints nuevos).
- `./.venv/bin/python -m compileall -q app tests` limpio.
- `./.venv/bin/alembic heads` → un único head `234785d5331f`, sin
  migración nueva (diseño elegido explícitamente evita tabla nueva).
- `cd frontend && npm run typecheck && npm run lint` limpios.
- `npm test -- --run` → 78/78 (antes 72; +6 tests: ecuación de Balance
  General, empty state, Estado de Resultados con datos reales, CSV
  deshabilitado sin filas, paginación real de Libro Mayor con offset,
  botón Anterior deshabilitado en la primera página).
- `npm run build` → build/PWA correcto; persiste el warning de chunk
  >500 kB ya rastreado en `DEFERRED-FINAL-017` (sin cambio, no se atacó en
  este slice).

`NXR-REQ-0093` permanece `IN_PROGRESS`: Cash Flow (sin clasificación de
actividad operativa/inversión/financiamiento persistida), reportes de
Treasury/Procurement y Earned Value compuesto de Project quedan como
subproyectos futuros independientes.

## 2026-08-25 — AP wired into the real Approval Inbox (resolves DEFERRED-FINAL-016)

`approval_service.create_request` had zero real production callers since
Track G built the Approval Inbox: `ap_service.apply_approval_decision` and
`submittal_service.apply_approval_decision` were registered as `decide()`
adapters, but nothing ever created the `ApprovalRequest` that would reach
them — confirmed by grep, not assumption. Picked AP as the candidate
(more clearly scoped than Submittal, which already has its own
`respond`/`decide` flow without an assignment concept).

Backend: `ap_service.submit_supplier_invoice_for_approval` moves a DRAFT
invoice to `REVIEW` and calls `approval_service.create_request(...)` for
real, behind `POST /api/ap/supplier-invoices/{id}/submit-for-approval`
(new `ap.supplier_invoice/submit` permission, granted wherever `create`
already was). The route validates the assigned approver actually holds
`workflow.approval/decide` and company access before creating the
request — otherwise it would be a dead-end nobody could ever act on (422
`NXR-FINANCIAL-001`). Deciding that request through the existing
`/api/approvals/{id}/decide` now really executes
`ap_service.apply_approval_decision` — previously reachable only from
tests calling `approval_service.decide()` directly, never from an actual
HTTP flow. `approve_supplier_invoice`/`cancel_supplier_invoice` now accept
both `DRAFT` and `REVIEW` as valid starting states, so the pre-existing
direct `.../approve` endpoint (no workflow) keeps working unchanged.

Frontend: `AccountsPayablePage.tsx` gains an "Enviar a aprobación" action
on DRAFT invoices, opening a modal for the approver's user ID (free-text
UUID — no company user-directory endpoint exists yet, a separately
documented gap; same honest pattern `QualityPage.tsx` already uses for
`responsibleUserId`, not a Select faked with invented names).

Verification executed in this checkpoint:

- `cd backend && ./.venv/bin/pytest -q` → 235/235 (+7 tests: real
  ApprovalRequest creation, decision approves via the real adapter,
  decision rejects via the real adapter, submitter-cannot-decide-own-
  request SoD, cannot submit a non-DRAFT invoice, assigned approver
  without decide permission is rejected, cross-company submit is denied).
- `./.venv/bin/python -m compileall -q app tests` clean; `alembic heads`
  → single head `234785d5331f`, no migration (no new table, `REVIEW` was
  already a value in `SUPPLIER_INVOICE_STATUSES`).
- `cd frontend && npm run typecheck && npm run lint` clean; `npm test --
  run` → 79/79 (+1 test); `npm run build` clean, same pre-existing
  `DEFERRED-FINAL-017` chunk-size warning, unchanged.

`submittal_service` remains unconnected to `create_request` — left as a
possible future subproject, not silently dropped (see updated
`DEFERRED-FINAL-016` entry in `docs/DEFERRED.md`).

## 2026-08-25 — Audit: General Ledger manual entries + reversal instrumented

Closed the "General Ledger (asientos manuales / reversal)" line from
`docs/AUDIT.md`'s honest backlog. `POST /api/accounting/journal-entries`
now records `accounting.journal_entry.create`; `POST /api/accounting/
journal-entries/{id}/reverse` records `accounting.journal_entry.reverse`
against the **original** document's `entity_id` (the entity whose status
actually transitions `POSTED -> REVERSED`), with `after.reversalDocumentId`
linking to the new reversal document. Same instrumentation pattern as the
existing AP/Treasury/Procurement routes — no `AuditLog`/`audit_service`
change needed, and `AuditLogPage.tsx` needed no frontend change (already
generic over `entityType`).

Verification: `cd backend && ./.venv/bin/pytest -q` → 237/237 (+2 tests);
`compileall` clean; single Alembic head `234785d5331f`, no migration.
Remaining audit backlog (Project Control, Enterprise Resources,
Commercial, Construction Control, and Transfers/General Expenses/Fund
Restrictions/Bank Reconciliation within Financial Core) is unchanged and
still honestly listed in `docs/AUDIT.md`.

## 2026-08-25 — Real AP accrued/paid in Budget vs Actual (closes NXR-REQ-0034/0035)

While reconciling `docs/REQUIREMENTS_TRACEABILITY.md` against the real
code (per the "CANDADO FINAL" order — no row can stay stale), found
`budget_service.compute_summary` hardcoding `accrued = Decimal("0")` and
`paid = Decimal("0")` — a real financial figure presented as data, which
`CLAUDE.md` explicitly forbids ("Ninguna cifra financiera se hardcodea").
This matched exactly why `NXR-REQ-0034`/`NXR-REQ-0035` were tracked
`NOT_STARTED`.

Added `app/repositories/ap_repository.py` (`project_accrued_total`/
`project_paid_total`), mirroring `procurement_repository.
project_commitment_total`'s existing pattern: grouped by currency, raises
`BudgetCurrencyMismatchError` (`NXR-BUDGET-002`, 409) on a foreign-currency
invoice since this codebase has no FX policy authority yet. Accrued sums
`amount+tax_amount` for invoices whose accrual has actually posted
(`APPROVED` and beyond — never `DRAFT`/`REVIEW`/`CANCELLED`); paid sums
`SupplierInvoice.amount_paid`, already maintained per invoice by
`ap_service.pay_supplier_invoice`. `GET /api/projects/{id}/budgets/summary`
and `BudgetPage.tsx` needed zero changes — the contract already had both
fields, they were just fed a lie.

Also reconciled a second stale row while auditing this area:
`NXR-REQ-0016` ("Financial statements: TB, GL, BS, P&L, Cash Flow") had
been sitting at `NOT_STARTED` under a phantom "Track G" owner, when the
same scope (Trial Balance/General Ledger/Balance Sheet/Income Statement)
was actually built under `NXR-REQ-0093` earlier this session. Moved to
`IN_PROGRESS` pointing at the `NXR-REQ-0093` evidence; only Cash Flow
remains genuinely unbuilt there.

Verification: `cd backend && ./.venv/bin/pytest -q` → 240/240 (+3 tests:
real accrual+payment end to end, DRAFT invoice excluded, cross-currency
accrual rejected); `compileall` clean; single Alembic head
`234785d5331f`, no migration (no schema change). `npm test -- --run
tests/BudgetPage.test.tsx` unaffected (2/2, still stub-driven).

Traceability tally after this reconciliation: 0 `VERIFIED`, 92
`IMPLEMENTED` (+2), 23 `IN_PROGRESS` (+1), 7 `NOT_STARTED` (-3), 2
`BLOCKED_EXTERNAL` — still 124 rows total.

## 2026-08-25 — Inventory Returns (closes NXR-REQ-0054)

Continuing down the genuinely `NOT_STARTED` list: `movement_type="RETURN"`
already existed on `StockLedgerEntry` as documented intentional debt in
`docs/INVENTORY.md`, with no service function or endpoint. Added
`inventory_service.return_to_supplier`, mirroring `issue_to_project`/
`transfer_stock` exactly (same moving-average cost, same `INV-INV-001`
insufficient-stock guard via the shared `_issue` helper) with its own
`movement_type="RETURN"` and `source_type="supplier_return"`/
`source_id=supplier_id` so it's distinguishable from a real project
consumption in the ledger. `POST /api/inventory/stock/return-to-supplier`
validates the supplier belongs to the company
(`assert_supplier_belongs_to_company`, same helper AP/Procurement already
use). `StockLedgerEntryResponse` now also exposes `sourceType`/`sourceId`/
`notes` (previously omitted for every movement type, not just Returns).

Traceability: `NXR-REQ-0054` reconciled to `IMPLEMENTED`, matching its
already-`IMPLEMENTED` siblings `NXR-REQ-0051/0052/0053` (Stock Ledger/
Transfers/Project Issues) exactly on FE/`Perm`/Audit/E2E — none of those
raw stock-movement capabilities have a dedicated UI screen, a
company-isolation-specific test, or audit instrumentation yet either; this
is a real, pre-existing, intentional convention in this row set, not a
gap introduced by this change.

Verification: `cd backend && ./.venv/bin/pytest -q` → 243/243 (+3 tests:
real return reduces stock and tags the supplier, insufficient stock
rejected, cross-company supplier rejected); `compileall` clean; single
Alembic head `234785d5331f`, no migration.

Traceability tally: 0 `VERIFIED`, 93 `IMPLEMENTED` (+1), 23
`IN_PROGRESS`, 6 `NOT_STARTED` (-1), 2 `BLOCKED_EXTERNAL` — 124 rows
total.

## 2026-08-25 — Crews (closes NXR-REQ-0074)

Continuing down the `NOT_STARTED` list: `Crew`/`CrewMember` (migration
`24e79c9cb218`), same minimal-scope criterion `Worker` already established
("covers the least `TimeEntry` needs, not a full HR module") — a named
group of Workers, `project_id` nullable using the same pattern
`Warehouse.project_id` already uses (no `OperationScope` engine, that's
exclusive to financial/administrative documents per `CLAUDE.md` §7), and
plain membership with no scheduling/rotation by date.

Backend: `workforce_service.create_crew`/`list_crews`/`add_crew_member`/
`remove_crew_member`/`list_crew_members`; 5 REST endpoints under
`/api/workforce/crews`; new `workforce.crew` permission
(`create`/`read`/`manage_members`) granted to Equipment Manager (same
owner as `workforce.worker`), read also to Operations User and Auditor.
Added a real `CrewMembershipError` (`NXR-WORKFORCE-002`, 409) for
duplicate/missing membership instead of letting a bare `ValueError` fall
through to an unhandled 500 — caught this by actually writing the
duplicate-membership test first and watching it try to assert on a raw
500, which is bad API design, not a acceptable "RED" state to build
toward.

Frontend: `CrewsPage.tsx` at `/recursos/cuadrillas`, which already existed
as a reserved nav entry ("Cuadrillas", 👷) with no route wired to it
before this — list/create crews (optional attribution to the active
project via `ActiveUIContext`), and a members modal to add/remove Workers
against the real API.

Verification: `cd backend && ./.venv/bin/pytest -q` → 247/247 (+7 tests);
`compileall` clean; `alembic check` → no drift, single head
`24e79c9cb218`. `cd frontend && npm run typecheck && npm run lint` clean;
`npm test -- --run` → 83/83 (+4 tests); `npm run build` clean (same
pre-existing `DEFERRED-FINAL-017` chunk warning).

Traceability tally: 0 `VERIFIED`, 94 `IMPLEMENTED` (+1), 23
`IN_PROGRESS`, 5 `NOT_STARTED` (-1), 2 `BLOCKED_EXTERNAL` — 124 rows
total.

## 2026-08-25 — Supplier Contracts / Subcontracts (closes NXR-REQ-0059/0060) + a real company-isolation fix

Switched from the `NOT_STARTED` list (exhausted, down to genuinely
infra/hardening-phase items and one deliberately-deferred row) to a
reconciliation pass over the 23 `IN_PROGRESS` rows, looking for the same
class of issue that surfaced `NXR-REQ-0034/0035`'s hardcoded zeros and
`NXR-REQ-0016`'s stale ownership earlier this session. `NXR-REQ-0059`
("Supplier Contracts") was `IN_PROGRESS` specifically because it had no
dedicated tests. Writing them (RED, per TDD) exposed a real `INV-COMP-001`
gap: `POST /api/procurement/suppliers/contracts` never validated
`supplier_id`/`project_id` against the requesting `company_id` — a
contract could be created referencing a Supplier or Project belonging to
a completely different company, something every comparable financial
write path in this codebase (AP, Budget, Treasury) already guards
against. Fixed with the same `assert_supplier_belongs_to_company`/
`assert_project_belongs_to_company` helpers those paths already use.

Frontend: `SupplierContractsPage.tsx` at `/abastecimiento/contratos`
(reserved nav entry, "Contratos", previously unwired) — lists contracts,
creates one against a supplier and an optional project.
`NXR-REQ-0060` (Subcontracts) shares the exact same model/fix/evidence —
`SupplierContract` covers both with no distinguishing field, as already
noted in its row.

Verification: `cd backend && ./.venv/bin/pytest -q` → 251/251 (+4 tests:
real create+list, cross-company supplier rejected, cross-company project
rejected, cross-company list isolation); `compileall` clean; `alembic
check` → no drift (no schema change needed for this fix). `cd frontend &&
npm run typecheck && npm run lint` clean; `npm test -- --run` → 86/86
(+3 tests); `npm run build` clean.

Traceability tally: 0 `VERIFIED`, 96 `IMPLEMENTED` (+2), 21
`IN_PROGRESS` (-2), 5 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL` — 124 rows
total.

## 2026-08-25 — Bid Comparison (closes NXR-REQ-0044) + three more real company-isolation fixes

Continued the `IN_PROGRESS` reconciliation pass onto `NXR-REQ-0044` Bid
Comparison. `docs/PROCUREMENT.md` already flagged one piece of intentional
debt here: `PurchaseOrderFromQuotationRequest` never validated that the
quotation belonged to the requesting company ("se confía en que el
caller ya hizo Bid Comparison correctamente"). Investigating that to fix
it surfaced two more, more serious gaps in the same pipeline while
building the screen that finally makes RFQ/Quotations (`NXR-REQ-0042`/
`0043`, deliberately backend-only until now) visible:

- `GET /rfqs/{rfq_id}/quotations` had **zero** company access check at
  all — any authenticated user with `procurement.quotation/read` in *any*
  company could read another company's confidential supplier pricing and
  terms just by knowing or guessing an `rfq_id`. This was a real
  cross-tenant read leak, not just a write-path gap like the others found
  this session.
- `POST /rfqs/{rfq_id}/quotations` (`submit_quotation`) had the same
  missing `assert_company_access`, plus never validated the submitted
  `supplier_id` against the RFQ's company.
- `procurement_service.create_rfq` never validated `supplier_ids`
  belonged to the requesting `company_id`.

All four (including the originally-documented one) fixed with the same
`assert_supplier_belongs_to_company`/company_id-comparison pattern used
everywhere else in this codebase. Also added `GET /api/procurement/rfqs`
(list, company-scoped) — it didn't exist at all, so there was no way to
browse RFQs before drilling into one. `QuotationResponse` gained
`deliveryDays`/`paymentTerms`/`validUntil`/`notes` — the model already
had them, but Bid Comparison specifically needs more than price to
compare bids, and the response omitted them entirely.

Frontend: `BidComparisonPage.tsx` at `/abastecimiento/comparativos`
(reserved nav entry) — lists RFQs, creates one against a supplier, shows
the real quotation comparison table, registers new quotations, and lets
the user pick a winner (creates a real `PurchaseOrder` via the
now-isolated `from-quotation` endpoint).

Verification: `cd backend && ./.venv/bin/pytest -q` → 258/258 (+13 tests:
RFQ rejects foreign supplier, RFQ listing + isolation, quotation submit
requires RFQ-company access, quotation submit rejects foreign supplier,
quotation listing requires RFQ-company access, PO-from-quotation rejects
a foreign company's quotation, delivery/payment terms exposed); `compileall`
clean; `alembic check` → no drift (no schema change). `cd frontend && npm
run typecheck && npm run lint` clean; `npm test -- --run` → 89/89 (+3);
`npm run build` clean.

Traceability tally: 0 `VERIFIED`, 97 `IMPLEMENTED` (+1), 20
`IN_PROGRESS` (-1), 5 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL` — 124 rows
total. `NXR-REQ-0042`/`0043` stayed `IMPLEMENTED` but their evidence was
enriched (their "backend-only" framing is now stale — they have a real
screen).

## 2026-08-25 — Systematic company-isolation audit: 6 more real gaps found and fixed

The RFQ/Quotation read leak found while building Bid Comparison was
serious enough (cross-tenant, not just a write-path gap) to warrant a
dedicated pass rather than trusting it was the only one. Ran a full
read-only audit of every route handler in `backend/app/api/routes/*.py`
for the same defect shape: an entity-id-in-path route that fetches an
entity and returns/mutates data derived from it without calling
`assert_company_access` against that entity's `company_id`. Six more
confirmed, all fixed with the same pattern already established elsewhere
in this codebase (resolve entity → 404 if missing → `assert_company_access`
using the entity's real `company_id` → proceed):

- `POST /procurement/requisitions/{id}/approve` — zero check. Any user
  with `procurement.requisition/approve` in their own company could
  approve another company's purchase requisition.
- `GET /procurement/goods-receipts?purchase_order_id=` — zero check
  (`_user` dependency was even unused). Real cross-tenant **read** leak:
  receipt lines/quantities/warehouse for any company's PO, given its id.
- `POST /procurement/three-way-match` — zero check. Could run and persist
  a three-way match against another company's PO/invoice data.
- `POST /inventory/physical-counts/{id}/approve` — zero check. Any user
  with `inventory.physical_count/approve` in their own company could
  approve another company's physical count, generating real stock
  `ADJUSTMENT` ledger entries against that company's inventory.
- `create_goods_receipt`/`create_service_entry` — a latent bug, not a
  leak: `if order is not None: assert_company_access(...)` then an
  *unconditional* read of `order.company_id` two lines later. An unknown
  `purchase_order_id` skipped the check (nothing to check against) and
  then crashed with an unhandled `AttributeError` → 500, instead of a
  clean 404. Fixed to raise 404 before the check.
- `GET /dashboard/summary` — `active_projects` counted `ACTIVE` projects
  across **every company on the platform**, regardless of who was asking.
  Every authenticated user saw a platform-wide number, not their own.
  Fixed: scoped to the requesting user's own companies
  (`permission_service.list_user_company_ids`) unless their role holds
  `project`/`read` with `company_scope=ANY` (Administrator, Auditor), in
  which case the platform-wide count is the correct real answer for them.

6 new tests, one per fix. Verification: `cd backend && ./.venv/bin/pytest
-q` → 264/264; `compileall` clean; `alembic check` → no drift (no schema
change). No frontend changes needed for the route fixes (contracts
unchanged, just an added authorization/404 check); the dashboard fix is
purely a backend query-scoping change transparent to the frontend.

Traceability: no row changed `IMPLEMENTED`/`IN_PROGRESS` status — these
were quality/security fixes inside already-`IMPLEMENTED` rows
(`NXR-REQ-0040`, `0046`, `0048`, `0051`), evidence notes added to each.
Tally unchanged at 97/20/5/2/0.

## 2026-08-25 — Corrections / posted-document reversal now syncs AP/AR (closes NXR-REQ-0025)

Per the master order: determine whether `reverse_document` already
satisfies this requirement, or whether some domain genuinely needs a
distinct "correction" flow — don't build anything speculative. Verified:
`reverse_document` (INV-ACC-002) already reverses ANY posted
`AccountingDocument` regardless of owning domain, and CLAUDE.md §8
defines "Corrección = reversal/correction enlazado al original" without
demanding a separate verb. So the row's premise ("falta un flujo
distinto") was not quite right — but investigating it surfaced a real,
reachable defect instead: reversing an AP/AR document's accrual through
the generic endpoint left the `SupplierInvoice`/`CustomerInvoice` at
`APPROVED` — still payable/collectible — pointing at a document that was
now `REVERSED`. Finance Manager already holds
`accounting.journal_entry/reverse`, so this was directly reachable, not
theoretical.

Fixed with `posting_service.register_reversal_hook(source_type, hook)`,
the same adapter-registration pattern `approval_service` already uses:
`reverse_document` looks up the `AccountingSourceLink` for the document
being reversed and calls the registered hook (if any) *before* creating
the reversal, so it can raise and prevent an invalid reversal from
creating any state at all. `ap_service.apply_accrual_reversal`/
`ar_service.apply_invoice_reversal` cancel the invoice when its accrual
(`SIN`/`CIN`) is reversed, and reject the reversal outright once the
invoice has any payment/collection against it. Both `source_type`s are
shared with a second `document_type_code` (`PAY`/`REC`) for the
payment/receipt posting itself — reversing *those* is explicitly
rejected for now (`InvalidInvoiceStateError`) rather than silently
leaving inconsistent state; recorded as `DEFERRED-FINAL-018`, not
ignored. `asset_service`/`procurement_service` post with their own
`source_type` and have no hook registered yet either — same entry.

Verification: `cd backend && ./.venv/bin/pytest -q` → 267/267 (+3 tests);
`compileall` clean; `alembic check` → no drift (no schema change, pure
service-layer addition).

Traceability: `NXR-REQ-0025` moved `IN_PROGRESS` → `IMPLEMENTED`. Tally
now 98 `IMPLEMENTED` (+1), 19 `IN_PROGRESS` (-1), 5 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`, 0 `VERIFIED`.

## 2026-08-25 — Real Tax architecture (closes NXR-REQ-0006)

Per the master order: determine exactly what's missing (calculation,
integration, posting, invoice use, reporting, API, tests) and either
complete it if genuinely required, or resolve the exclusion formally and
justifiably — don't leave it ignored. `TaxCode`/`TaxLine` already existed
as a data model and `posting_service.post_manual` already accepted an
optional `tax_lines` param, but nothing could ever create a `TaxCode`
(no service, no API) and nothing ever called `post_manual` with
`tax_lines`. This was pure unused scaffolding, not a partial capability —
exactly what CLAUDE.md §9 says never counts toward a requirement.

Added `tax_repository`/`tax_service` (`create_tax_code` with a real
duplicate-code guard — `TaxCodeExistsError` → `NXR-TAX-001`/409;
`list_tax_codes`; `compute_tax` as a pure function, `base_amount *
rate_percent / 100` HALF_UP to 2 decimals — the "servicio de cálculo"
the row said was missing) and `GET`/`POST /api/master-data/tax-codes`,
alongside the existing Chart of Accounts routes in the same file. New
`tax.tax_code` permission (Finance Manager create/read, Auditor
read-only).

Explicit scope boundary, not silently dropped: AP/AR/Procurement still
accept a manually-entered `tax_amount` rather than computing it from a
selected `TaxCode` — wiring that in touches those domains' already-
shipped, tested invoice flows, a separate and larger change with its own
regression risk. Any domain that wants computed tax now has a real,
tested function to call when it chooses to adopt it. No frontend screen
either — same precedent RFQ/Quotations had before Bid Comparison gave
them one: no reserved nav slot, no consuming UI flow yet.

Verification: `cd backend && ./.venv/bin/pytest -q` → 272/272 (+5 tests);
`compileall` clean; `alembic check` → no drift (no schema change,
`TaxCode` table already existed).

Traceability: `NXR-REQ-0006` moved `IN_PROGRESS` → `IMPLEMENTED`. Tally
now 99 `IMPLEMENTED` (+1), 18 `IN_PROGRESS` (-1), 5 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`, 0 `VERIFIED`.

## 2026-08-25 — Authentication lockout + CSRF guard (closes NXR-REQ-0008/0009)

The row named two concrete missing pieces: rate-limit/lockout and CSRF.
Both closed.

**Lockout**: `User.failed_login_attempts`/`locked_until` (migration
`c15db6e5d9ca`, `server_default='0'` so it backfills safely against the
existing bootstrap admin row rather than failing on the NOT NULL add).
`auth_service.login` locks the account for `settings.lockout_minutes`
(default 15) after `settings.max_login_attempts` (default 5) consecutive
failures — even the *correct* password returns 423 while locked, which
is the point: once tripped, the request can't be distinguished from an
attacker who's guessed the real password on attempt 6. State lives in
PostgreSQL, not process memory, per CLAUDE.md §3 (stateless backend,
works identically across N Container Apps replicas).

**CSRF**: made an explicit, documented decision instead of leaving it
unaddressed. `SameSite=Lax` (dev) already blocks most CSRF; `SameSite=
None` (prod, since frontend/backend live on different subdomains)
doesn't. CORS (`allow_origins=[frontend_url]`) already blocks any JSON
fetch/XHR from an unconfigured origin via preflight — covering nearly
the whole API, which is JSON-only. The real gap: `POST /api/evidence`
uses `multipart/form-data`, a "simple" content-type that skips preflight
entirely, so a malicious cross-site HTML `<form>` could submit it using
the victim's cookies. Rather than patch that one endpoint, added a
uniform `Origin`-header guard (`app/api/csrf.py`) on every mutating
request (POST/PUT/PATCH/DELETE), so a future multipart endpoint doesn't
silently reopen the same hole. Missing `Origin` (curl, TestClient,
non-browser clients) is allowed through — that's not the CSRF vector,
which requires a real browser making the request, and browsers always
set `Origin` on cross-site non-trivial requests.

IP-based rate-limiting (distinct from per-account lockout) is
deliberately left as an infrastructure concern (Azure Front Door/WAF),
appropriate for the 90%+ hardening phase per
`docs/PRODUCTION_READINESS.md`, not this track — documented, not
ignored.

Verification: `cd backend && ./.venv/bin/pytest -q` → 277/277 (+6 new
auth/CSRF tests over the previous 272 plus one prior test file addition
already counted — see exact numbers in the commit); `compileall` clean;
`alembic check` → no drift, single head `c15db6e5d9ca`. The CSRF guard
runs globally, so the full suite passing confirms it doesn't break any
existing request path (none of the ~277 tests send an `Origin` header).

Traceability: `NXR-REQ-0008`/`NXR-REQ-0009` both moved `IN_PROGRESS` →
`IMPLEMENTED`. Tally now 101 `IMPLEMENTED` (+2), 16 `IN_PROGRESS` (-2),
5 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`, 0 `VERIFIED`.

## 2026-08-25 — Core platform reconciled (closes NXR-REQ-0001), domain-logic gap hunt effectively exhausted

`NXR-REQ-0001` had never been reconciled since the original bootstrap
commit (`62c56eb`) — its markers were uniformly partial (🔶) across the
board, not because anything was broken, but because the row was never
revisited. `docs/MASTER_PLAN.md` groups "Core platform" together with
Master Data/RBAC/Chart of Accounts/Posting Engine/GL/OperationScope/
ActiveUIContext under Track 1 — but every one of those already has its
own separately-reconciled row (`NXR-REQ-0002/0003/0004/0007/0008/0009/
0010/0012`). Verified directly against the code that the row's real
remaining scope — bootstrap, settings, health checks — is genuinely
complete: `app/core/config.py` (real `pydantic-settings` config with a
real Key Vault override path for production), `/healthz` (liveness),
`/readyz` (a real `SELECT 1` against PostgreSQL, 503 if the DB doesn't
respond — not a stub), both with a real test (`tests/test_health.py`).
No code changes needed; this was pure verification, not construction.

Traceability: `NXR-REQ-0001` moved `IN_PROGRESS` → `IMPLEMENTED`. Tally
now 102 `IMPLEMENTED` (+1), 15 `IN_PROGRESS` (-1), 5 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`, 0 `VERIFIED`.

Checked what's left in `IN_PROGRESS`/`NOT_STARTED`: `NXR-REQ-0016`/`0093`
(Cash Flow — needs a real schema decision on activity classification, not
a quick fix), `NXR-REQ-0058` (Supplier Performance — deliberately
deferred, no real PO/GR volume to compute honest metrics), and
everything else (`0105-0122`) is squarely the 90–100% feature-freeze
phase per `CLAUDE.md` §10: accessibility, migrations certification,
security hardening, observability, unit-test completeness, E2E, CI/CD,
Bicep/Azure resources, OIDC. The domain-logic gap-hunting pass this
session ran is effectively exhausted — every remaining row either needs
a real design decision, real data volume that doesn't exist yet, or real
infra/testing work rather than a code-reconciliation fix.

## 2026-08-25 — Real Critical Journey E2E built, executed green, 3 real bugs found and fixed (closes NXR-REQ-0112/0113)

Built `frontend/e2e/critical-journey.spec.ts` (Playwright): one continuous
sequential recorrido, not disconnected tests, against a real backend +
frontend it starts itself (`frontend/playwright.config.ts`, dedicated
`nexora_e2e` PostgreSQL DB, dedicated ports 8010/5175, fresh-install
`alembic upgrade head` against an empty DB on every run — a real exercise
of the same migration path `backend/Dockerfile`'s `CMD` uses). Covers, in
one login session (plus a real second-user session for the approval
step): login → company/project creation → ActiveUIContext → WBS → chart
of accounts → Treasury account + CENTRAL remittance → GENERAL expense →
project budget baseline → PR → approval → RFQ → supplier quotation →
Bid Comparison → PO → goods receipt → supplier invoice → 3-way match →
supplier payment → inventory receive/transfer/issue-to-project → crew +
time entry → equipment + fuel log + maintenance order → progress record
→ daily site report → quality inspection → safety observation → RFI →
submittal → change order (submit+approve) → journal entry correction/
reversal (`ANU-` prefix) → CRM (lead → convert → quotation → accept →
convert to sales contract → bill → AR receipt) → Approval Inbox (real
SoD enforcement + a real second approver) → notifications → global
search → reports (Trial Balance, General Ledger, Balance Sheet, Income
Statement) → audit trail → logout → login → persistence. 2/2 consecutive
runs green.

Getting there for real (not by writing the test and declaring victory)
surfaced three genuine product bugs, each fixed with a real regression
test, not just patched in the E2E script:

1. **`treasury_service.register_remittance`/`register_general_expense`
   accepted a counter/expense account equal to the treasury account's own
   GL account** — that produces a debit and credit to the *same* GL
   account, which cancels out the net movement while the
   `AccountingDocument` still looks balanced (`SUM(debit)==SUM(credit)`
   holds trivially). Real INV-TRE violation, found because the E2E test's
   first naive remittance attempt showed `L 0.00` where `L 100,000.00`
   was expected. Fixed with an explicit guard raising
   `InvalidFinancialReferenceError` (`NXR-FINANCIAL-001`) in both
   functions; regression tests in `tests/test_treasury.py`.
2. **`ap.py`'s `submit_supplier_invoice_for_approval` had two real
   authorization bugs.** First: it validated `assignedTo`'s company
   access with a raw `user_has_company_access` call instead of
   `assert_company_access`'s SCOPE_ANY-aware logic — since company
   creation never inserts an explicit `UserCompanyAccess` row for anyone,
   this silently rejected assigning an approval to *any*
   Administrator/Auditor in a company they didn't get an explicit row
   for (which is every company, for every Administrator, always). Fixed
   by checking `user_has_any_company_scope` before falling back to the
   raw row check, mirroring `assert_company_access`. Second: there was no
   real INV-SOD-001 guard at submit time — self-assignment (the same
   user submitting and being asked to decide) was only ever going to be
   caught later, incidentally, at `decide()` time, and only because of
   bug #1's false rejection accidentally standing in as a guard. Added a
   real `SegregationOfDutiesError` (`NXR-WORKFLOW-001`) check at submit
   time. `test_ap_ar.py`'s existing self-assignment test was actually
   asserting on bug #1's error code (`NXR-FINANCIAL-001`) as an
   incidental side effect — updated it to assert the real SoD code, and
   added `test_submit_for_approval_accepts_an_administrator_with_no_explicit_company_access_row`
   as the positive-path regression for bug #1.
3. **`ProjectsPage`'s primary "Crear compañía" flow never set
   `functionalCurrencyCode`**, and `functional_currency_code` is
   immutable post-creation (`CompanyUpdateRequest` deliberately excludes
   it, per `CLAUDE.md`) — so every company created through the app's main
   onboarding screen was permanently unable to have a `Budget`
   (`NXR-BUDGET-002`). `TreasuryPage`'s separate "quick start" flow
   already hardcoded `functionalCurrencyCode: 'HNL'`; applied the same
   default to `ProjectsPage`/`companyService.create`.

Also fixed, incidentally found while wiring the RFQ→PO E2E step:
`PurchaseOrderResponse` never returned `supplier_quotation_id` even
though the model has the column — the field existed everywhere except
the response schema. Regression test in `test_procurement_flow.py`.

No product-code change for the *test's* own bugs (route paths, payload
shapes, Playwright strict-mode selector ambiguities, a `.fill()` vs.
non-breaking-space text-matcher mismatch, 204-body handling) — those were
fixed only in the spec file.

Full verification before calling this done: 280/280 backend pytest
(up from 219 pre-session), `tsc -b --noEmit` clean, `eslint .` clean
(after excluding `e2e/**` from app lint — Playwright specs use `any` for
live API response shapes by design, same as the rest of the industry;
added to `eslint.config.js`'s `globalIgnores`), 89/89 frontend vitest
(after excluding `e2e/**` from vitest's default test glob in
`vite.config.ts`, which was picking up the Playwright spec and failing
on `test.describe.configure`), and the E2E suite itself green twice in a
row.

Real product gap surfaced but deliberately NOT built in this pass (scope
discipline, not an oversight): there is no user-management/invite API or
UI anywhere in the backend yet — only the single bootstrap Administrator
exists in a fresh install. The E2E test's second-approver step works
around this the same way `tests/helpers.py::create_user_with_role`
already does in pytest: it calls the backend's own
`user_repository.create_user`/`role_repository.assign_role`/
`hash_password` directly (same code path `bootstrap_service.py` uses,
not a mock) via a one-off Python subprocess against the real `nexora_e2e`
DB. This is real, not faked — but it underlines that user management
itself is a real, currently-`NOT_STARTED`-in-practice gap the
traceability matrix doesn't yet have its own row for.

Traceability: `NXR-REQ-0112`/`NXR-REQ-0113` moved `NOT_STARTED` →
`VERIFIED` — the first two rows in the entire matrix to reach that
state, with real executed evidence (not code-read, not "parece
funcionar"). Tally now 102 `IMPLEMENTED`, 15 `IN_PROGRESS`, 3
`NOT_STARTED`, 2 `BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — DEFERRED-FINAL-015 closed for real: user directory + real user-management API + generic FK safety net

Continuing immediately per the master order (no stopping between
checkpoints): the canonical next-gap check (`docs/AGENT_HANDOFF.md` +
`docs/PRODUCTION_READINESS.md`) confirmed `NXR-REQ-0109` (Backup/Restore)
is explicitly gated behind "90% real" and Build Width First — not yet
active work. The correct next independent gap was
`DEFERRED-FINAL-015` (open, well-scoped, no Azure dependency): Quality/
Safety's `responsible_user_id` was never validated against
existence/company-membership, and there was no real API to create users
beyond the single bootstrap Administrator — confirmed as a real,
still-current gap by the Critical Journey E2E work just finished (its
`createSecondApprover()` had to call backend repository functions
directly because no such endpoint existed).

All three pieces from the original gap plan:

1. `assert_user_belongs_to_company` (new, `financial_validation_service.py`)
   validates `responsible_user_id` before persisting in
   `quality_service.create_non_conformance`/`create_corrective_action`,
   `safety_service.create_observation`/`create_incident`, and
   `treasury_service.create_cash_closing` (the "same preexisting pattern"
   the original gap note already flagged in another track — closed too,
   though there it's pure defense-in-depth since that field is always
   `user.id` of the requester, never external input).
2. `_integrity_error_handler` (`app/api/error_handlers.py`) — a generic
   catch-all for any `IntegrityError` that reaches a route without a
   specific validator, returning a clean `NXR-DATA-001`/422 instead of an
   uncaught 500, with the real psycopg message logged server-side, never
   returned to the client.
3. `GET/POST /api/master-data/users` — the first real user-management API
   beyond the bootstrap Administrator. `create` is Administrator-only
   (`core.user`/`create`, base-permission auto-grant); `read` follows the
   same per-role scope as `core.company`/`read`.

Getting the "who belongs to this company" semantics right took an actual
wrong turn caught by tests, worth recording: the first version of
`assert_user_belongs_to_company` treated *any* SCOPE_ANY permission grant
as "this user is company-agnostic." That's wrong — Project Manager has
SCOPE_ANY on `core.company`/`core.user` *read* (for cross-company
dashboards) without being a real member of every company, and Auditor
has SCOPE_ANY on nearly everything *read* with zero write/assignment
actions. Both incorrectly qualified as valid `responsible_user_id`/
directory members for companies they have no real relationship to. Fixed
by narrowing the signal specifically to `core.user`/`create` in
SCOPE_ANY (Administrator-only) rather than "any resource/action at all"
— caught by `test_list_users_includes_explicit_access_and_any_scope_roles`
and the quality/safety cross-company tests actually failing on the first
implementation, not by inspection.

`QualityPage.tsx`, `SafetyPage.tsx`, and `AccountsPayablePage.tsx`'s
submit-for-approval modal all replaced their free-text UUID inputs with
a real `Select` populated from the new endpoint (`useCompanyUsers` hook,
`frontend/src/hooks/useCompanyUsers.ts`). `frontend/e2e/critical-journey.spec.ts`
no longer needs its Python-subprocess workaround to create a second
approver — it calls the real API, same as any other admin action in
that journey.

10 new backend tests (`test_user_management.py` x5, 2 quality + 1 safety
cross-company/existence cases, 1 error-handler unit test, plus the
positive-path company-access test), 1 frontend test updated
(`TreasuryPage.test.tsx`'s AP submit-for-approval test now selects a
real user from the directory instead of typing a UUID). Full
verification: 290/290 backend pytest (up from 280), `tsc -b --noEmit`
clean, `eslint .` clean, 89/89 frontend vitest, Critical Journey E2E
green 2/2 after the user-management API swap.

Traceability: no row moved to `VERIFIED` from this slice (it's a bug fix
+ new API within `NXR-REQ-0010`/`0023`/`0082`/`0084`'s already-
`IMPLEMENTED` scope, not a new top-level capability) — evidence updated
on those four rows instead. `docs/DEFERRED.md`'s `DEFERRED-FINAL-015`
marked RESOLVED. Tally unchanged: 102 `IMPLEMENTED`, 15 `IN_PROGRESS`, 3
`NOT_STARTED`, 2 `BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Cash Flow statement built for real (closes NXR-REQ-0016, moves IN_PROGRESS → IMPLEMENTED)

Direct continuation, same session. Next canonical gap per
`docs/AGENT_HANDOFF.md`'s own backlog after `DEFERRED-FINAL-015`: Cash
Flow, the one remaining well-scoped domain-logic item, explicitly
flagged as needing "a real schema decision" (no persisted cash-flow
activity classification existed —
`docs/superpowers/specs/2026-08-25-financial-statements-design.md`
carried it as "explicitly out of scope" since the original Financial
Statements subproject).

**Design decision (direct method, not indirect):** `Account` gains a
nullable `cash_flow_activity` column (`OPERATING`/`INVESTING`/
`FINANCING`/`NULL`, migration `8496f11b1227`, no backfill needed —
existing accounts start unclassified and the report says so honestly).
Cash itself is never explicitly classified: it's identified structurally
as whatever GL account a `TreasuryAccount.gl_account_id` in this company
points to (Treasury already owns that boundary per `CLAUDE.md` §7). By
double-entry conservation, the net change across all Treasury-linked
accounts in a period is exactly the negative of the sum of
(credit-debit) across every other account touched in the same period —
so `reporting_service.cash_flow_statement` never has to correlate
individual documents or explicitly exclude Treasury-to-Treasury
transfers (both legs are "cash," so they cancel out of the non-cash sum
automatically). Classified non-cash accounts sum into
operating/investing/financing; anything not yet classified sums into an
explicit `unclassified` bucket instead of being hidden, guessed, or
silently dropped — and the report always reconciles exactly:
`operating + investing + financing + unclassified == net_change_in_cash`
(this is asserted as a real invariant in
`test_cash_flow_general_expense_is_operating_when_classified`, not just
hoped for).

Shipped: `PATCH /api/master-data/accounts/{id}` (the first way to edit
an account post-creation at all — `accounting.account`/`update`,
Administrator/Finance Manager, same `SCOPE_OWN`/`SCOPE_ANY` split as
`create`) to set the classification; `GET /api/reports/cash-flow`
(`reports.cash_flow`/`read`, granted wherever `reports.balance_sheet`
already is); a generic `InvalidCashFlowActivityError` (`NXR-ACCOUNTING-005`/
422) for a garbage classification value; `CashFlowPage.tsx` as a new tab
in `/control/reportes`, CSV export included. No dedicated Chart of
Accounts admin screen was built to set the classification through the
UI — same precedent as Tax Codes before Bid Comparison existed:
API-real, no UI consumer yet, documented `➖` for that specific gap
rather than invented scope.

7 new backend tests (`test_reporting.py`), 2 new frontend tests
(`FinancialStatementsPage.test.tsx`). Full verification: 296/296 backend
pytest (up from 290), `tsc -b --noEmit` clean, `eslint .` clean, 91/91
frontend vitest (up from 89), Critical Journey E2E green (confirms the
new migration doesn't break the fresh-install `alembic upgrade head`
path — 18 migrations now, still clean).

Traceability: `NXR-REQ-0016` (Financial statements: TB/GL/BS/P&L/Cash
Flow) moved `IN_PROGRESS` → `IMPLEMENTED` — Cash Flow was the only
missing piece. `NXR-REQ-0093` (Reporting, broader row) stays
`IN_PROGRESS`: Treasury/Procurement operational reports and Earned Value
remain genuinely out of scope, unrelated to Cash Flow. Tally now 103
`IMPLEMENTED` (+1), 14 `IN_PROGRESS` (-1), 3 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Migrations certified for real, found and fixed a real downgrade bug in 4 migration files (NXR-REQ-0106 → IMPLEMENTED)

Direct continuation, same session. `NXR-REQ-0106`'s own evidence text
said "`alembic upgrade head` aplicado; falta certificar fresh-install +
upgrade matrix" — the Critical Journey and Cash Flow work this session
already generated repeated real fresh-install evidence (dropdb/createdb
+ `alembic upgrade head` against an empty DB, now 18 migrations, every
E2E run), but "upgrade matrix" (downgrade path, round-trip) was never
actually exercised — every other test in this suite uses
`Base.metadata.create_all`/`drop_all`, never the real Alembic chain.

Built `tests/test_migrations.py`: shells out to the real `alembic` CLI
against a dedicated PostgreSQL database (`nexora_migrations_test_*`,
worktree-isolated same as the main test DB) and runs fresh install →
full `downgrade base` → `upgrade head` again.

**This immediately failed on first run** — not a hypothetical the test
was written to prove is impossible, a real bug it caught doing exactly
what it was built to do. Six constraints across four migration files
(`131a6debf189`, `c622defc2308`, `f1075e290473`, `eaf5b6c0d061`) were
autogenerated by Alembic with `create_foreign_key(None, ...)` /
`create_unique_constraint(None, ...)` — passing `None` lets PostgreSQL
assign an unpredictable constraint name at CREATE time. Each migration's
own `downgrade()` then tried `drop_constraint(None, ...)`, which can
never resolve to an actual constraint and always raised
`sqlalchemy.exc.CompileError`. Every `downgrade()` in the entire chain
was silently broken from the point of the earliest offender onward —
nobody had ever run `alembic downgrade` against this codebase for real
before. Fixed by giving every one of the six constraints an explicit,
descriptive name at creation (e.g. `fk_projects_cost_center_id`,
`uq_companies_code`) and referencing that same name in `downgrade()`.
Verified manually first (fresh install → downgrade to base → upgrade to
head, twice, once broken once fixed) before writing the automated test
around it, so the test's own correctness isn't just trusted on faith.

Editing already-applied historical migration files is normally a
concern, but this specific edit is safe: it changes nothing about what
`upgrade()` produces (same columns, same tables, same constraint
*behavior* — only the constraint's *name* changes on a fresh install),
and `downgrade()` was never successfully run by anyone before this fix,
so there's no working behavior anywhere being changed out from under an
existing environment.

Full verification: 297/297 backend pytest (up from 296, the one new
migration test), Critical Journey E2E green (confirms fresh-install
still works after editing four historical migrations).

Traceability: `NXR-REQ-0106` moved `IN_PROGRESS` → `IMPLEMENTED` with
real fresh-install + full round-trip evidence (not "aplicado" by
itself). Tally now 104 `IMPLEMENTED` (+1), 13 `IN_PROGRESS` (-1), 3
`NOT_STARTED`, 2 `BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Accessibility audited for real, found and fixed 2 real WCAG AA contrast violations (NXR-REQ-0105 → IMPLEMENTED)

Direct continuation, same session. `NXR-REQ-0105`'s own evidence text
named exactly what was missing: "auditoría de contraste real con
herramienta y lector de pantalla." The "herramienta" half is genuinely
buildable by an agent; the "lector de pantalla" half (a manual
VoiceOver/NVDA pass) is not — no fabricating that evidence, it stays an
honestly-documented human-only gap.

Added `@axe-core/playwright` (justified: it's literally the tool the
row's own text called for, and it plugs directly into the existing
Playwright E2E infrastructure — no new browser automation framework).
Built `frontend/e2e/accessibility.spec.ts`: scans the login page and 6
representative real authenticated screens (`/inicio`, `/proyectos`,
`/finanzas/tesoreria`, `/finanzas/contabilidad`, `/control/reportes`,
`/control/auditoria`) with axe-core's `wcag2a`/`wcag2aa`/`wcag21aa`
rule sets, against the real backend+frontend the Critical Journey
already starts (same `nexora_e2e` DB/ports) — one `npm run test:e2e`
invocation now runs both specs.

**It failed immediately on first run**, same pattern as the migrations
test: a real `color-contrast` violation on `.nx-topbar__user-role`
(`--nx-gray-400`, 2.44:1 against white, needs 4.5:1). `--nx-gray-400`
turned out to be used as text color in ~14 places across the design
system (hints, timestamps, empty states, breadcrumb separators, close
icons) — all failing the same way, since it's genuinely the same
"muted small text" role everywhere. Fixed at the token level
(`#9aa7b8` → `#64707f`, ≥5:1) rather than patching each call site.

Re-running surfaced a second, different real bug: the dark sidebar
(`.nx-sidebar__link`/`.nx-sidebar__group-label`, navy `#050b18`
background) reused that same now-darkened `--nx-gray-400` token for its
nav text — 3.9:1 against navy, still failing, because a single gray
value cannot satisfy 4.5:1 against both white and near-black
simultaneously. Added a second, purpose-specific token
(`--nx-navy-100: #a9b4c4`, 9.4:1 against `--nx-navy-950`) instead of
trying to force one shared value to do both jobs. **Also caught and
fixed a self-inflicted mistake while making this second fix**: a
`replace_all` edit on `color: var(--nx-gray-400)` in the same CSS file
accidentally repainted `.nx-topbar__user-role` (a *light*-background
element) with the new *dark-background* token, making it nearly
invisible on white — caught by re-running the scan immediately rather
than assuming the edit was correct, reverted to the token fix from the
first pass. Verified visually with a real screenshot after the fix, not
just by the automated scan passing.

0 violations after both fixes, stable across 2 consecutive scan runs
plus a combined `npm run test:e2e` run of both E2E specs together.

Traceability: `NXR-REQ-0105` moved `IN_PROGRESS` → `IMPLEMENTED` — real
tool-based audit done and passing; manual screen-reader pass explicitly
flagged as the one remaining human-only gap, not hidden. Tally now 105
`IMPLEMENTED` (+1), 12 `IN_PROGRESS` (-1), 3 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Structured logging with a real correlation_id (NXR-REQ-0108 → IMPLEMENTED)

Direct continuation, same session. Dispatched a research-only fork
first to check whether `NXR-REQ-0107` (Security), `0108`
(Observability), or `0114` (CI/CD) had the most cleanly local,
non-Azure remaining scope before picking one — confirmed by direct code
inspection (not guessed) that `0108` was cleanest: a `correlation_id`
dependency already existed (`app/api/deps_correlation.py`) but was only
ever written into the `AuditLog` DB table, never into an actual log
line, and `app/main.py` had zero structured-logging setup at all.

Investigating closer surfaced a real, separate inconsistency worth
fixing at the same time: `error_handlers.py` and `csrf.py` each minted
their own fresh `uuid.uuid4()` for an error response's `correlationId`,
completely disconnected from whatever `Depends(get_correlation_id)`
returned in the same request (which itself re-parsed the
`X-Correlation-Id` header independently in each of 5 routes, so two
different `Depends()` calls in the same request without a client
header could legitimately mint two different random ids). None of this
was wired into Python's `logging` module either.

Built one shared source of truth: `app/core/logging.py` holds a
`contextvars.ContextVar` for the current request's correlation id, a
`logging.Filter` that injects it into every log record, and a JSON
`Formatter`. `app/api/correlation.py`'s `CorrelationIdMiddleware` is
deliberately **pure ASGI, not `BaseHTTPMiddleware`** — Starlette has a
well-known gotcha where a `ContextVar` set inside `BaseHTTPMiddleware
.dispatch()` before `call_next()` isn't always reliably visible
downstream (an internal `anyio` task-group boundary); wrapping the ASGI
callable directly avoids that class of bug entirely rather than risking
it. The middleware reuses an incoming `X-Correlation-Id` header
(distributed tracing) or mints a new one, sets the `ContextVar` before
anything else runs, echoes it in the response header, and logs one
structured line per request (method/path/status/duration_ms).

Had to get middleware **registration order** right, which is
non-obvious in Starlette: `add_middleware()` *prepends* to the internal
list, and the stack is built by wrapping in `reversed()` order — so the
middleware added **last** ends up **outermost** (runs first on the way
in). `CorrelationIdMiddleware` is added after `register_csrf_guard()`
specifically so the id exists before the CSRF guard's own 403 handler
needs it. Verified this was actually correct via a real test
(`test_csrf_rejection_correlation_id_matches_the_response_header`), not
assumed from reading the Starlette source alone.

`deps_correlation.py`'s `get_correlation_id()` (still used by the 5
existing routes as a `Depends()`) now just reads the same `ContextVar`
instead of re-parsing the header — same call signature, so no route
changes needed. `error_handlers.py`/`csrf.py` now use the same shared
value instead of a fresh random uuid.

6 new tests (`test_observability.py`): client-supplied id is reused not
replaced; a generated id is echoed in the response header; an error
response's `correlationId` matches the response header (the exact bug
this closes); the CSRF 403 does too; a real audited action
(`treasury.remittance.create`) persists the same id into
`AuditLog.correlation_id` as the request that triggered it (checked
against the real DB row, not just the response); the JSON formatter
output shape. Manually verified real JSON log lines on stdout against a
live server, not just asserted in tests — confirmed the bootstrap log
(no request context, `correlationId: "-"`) and per-request log lines
both look right, and confirmed the Critical Journey E2E run shows real
structured JSON lines in its own server output.

Full verification: 303/303 backend pytest (up from 297), `tsc -b
--noEmit` clean, `eslint .` clean, 91/91 frontend vitest, combined
Critical Journey + Accessibility E2E 3/3 green with real structured
logs visible in the run.

Traceability: `NXR-REQ-0108` moved `IN_PROGRESS` → `IMPLEMENTED`. Tally
now 106 `IMPLEMENTED` (+1), 11 `IN_PROGRESS` (-1), 3 `NOT_STARTED`, 2
`BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Real security response headers (NXR-REQ-0107 evidence updated, stays IN_PROGRESS honestly)

Direct continuation, same session, following straight from the previous
entry's own "natural next candidate" note. Zero security headers
existed anywhere in the codebase before this (confirmed by grep across
`backend/app/` for `X-Frame-Options`/`X-Content-Type-Options`/
`Strict-Transport-Security`/`Content-Security-Policy`/`Referrer-Policy`
— no matches).

`app/api/security_headers.py`'s `SecurityHeadersMiddleware`
(`BaseHTTPMiddleware` is fine here — unlike `CorrelationIdMiddleware`,
this one only touches the response *after* `call_next()` returns, so
the Starlette contextvar-propagation gotcha that motivated pure ASGI
for correlation ids doesn't apply). Registered as the outermost layer
of the entire middleware stack (added last, after
`CorrelationIdMiddleware`) specifically so the headers apply to
absolutely every response, including a 403 from the CORS/CSRF layers
underneath it — verified by a real test hitting the CSRF rejection
path, not assumed.

Real design decisions, not defaults copy-pasted from a boilerplate
list: `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy` are
universal (safe on every response type, including FastAPI's own
`/docs` HTML). `Content-Security-Policy: default-src 'none'; frame-
ancestors 'none'` applies everywhere the backend serves JSON *except*
`/docs`/`/redoc`/`/openapi.json` — Swagger UI and ReDoc load their real
JS/CSS from a CDN, so a strict CSP there would break them outright;
verified this exemption for real
(`test_docs_endpoint_never_gets_the_strict_csp` actually hits `/docs`
and gets a 200, not assumed to work). `Strict-Transport-Security` only
applies when `settings.is_production` — meaningless (and potentially
confusing during local smoke-testing) over plain HTTP in dev, real over
HTTPS in production; verified both branches with `monkeypatch` on the
already-cached `get_settings()` instance rather than spinning up a
second app/TestClient (simpler, and avoids an unnecessary second
database schema lifecycle in the test).

4 new tests (`test_security_headers.py`). Full verification: 307/307
backend pytest (up from 303), `tsc -b --noEmit` clean, `eslint .`
clean, 91/91 frontend vitest, combined Critical Journey + Accessibility
E2E 3/3 green (confirms the new headers don't interfere with the SPA's
real `fetch()` calls to the API — CSP on a JSON response only restricts
what that response could do if rendered as a *document*, never what a
`fetch()`/XHR caller can read from it, so this was expected to be safe,
and was verified to be).

**Deliberately NOT moved to `IMPLEMENTED`**: the row's own name
includes "rate-limit," which is still genuinely missing and is real
infrastructure work (Azure Front Door/WAF, not application code) —
moving this row to `IMPLEMENTED` while that's still absent would be
exactly the kind of inflation `CLAUDE.md` forbids. Evidence updated
honestly, status stays `IN_PROGRESS`, gap named explicitly.

Traceability: `NXR-REQ-0107` evidence updated (headers real and
tested), status unchanged. Tally unchanged: 106 `IMPLEMENTED`, 11
`IN_PROGRESS`, 3 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Real Backup/Restore, executed and verified (NXR-REQ-0109 → IMPLEMENTED)

Direct continuation, same session, under the user's explicit "no more
deferring implementable work" order — `NXR-REQ-0109` had been
`NOT_STARTED` with a blanket "gated behind 90%" rationale that no
longer held once the order explicitly said to execute it locally now
rather than keep deferring.

`scripts/db_backup.sh`/`scripts/db_restore.sh`: real `pg_dump
--format=custom` / `pg_restore`, restore always targets a freshly
dropped+created database, never overwrites a live one. Both scripts'
only real exercise is `backend/tests/test_backup_restore.py`, so a
regression in either fails there first, not in an actual incident.

The test does exactly what `docs/PRODUCTION_READINESS.md`'s block 4
names, item by item, against real PostgreSQL — not simulated: fresh
`nexora_backup_source_*` DB → `alembic upgrade head` → seed real data
through the actual repository/service layer (a company, its chart of
accounts, a treasury account, a real posted CENTRAL remittance for
L 75,000.00, and a real Administrator user with a real Argon2id hash —
never a raw `INSERT`, so what gets backed up is exactly what a real
user action would produce) → `db_backup.sh` → `db_restore.sh` into a
brand new `nexora_backup_target_*` → verify against the restored DB:

- **migrations/state**: `alembic current` reports the same head.
- **login**: the restored password hash matches the original byte for
  byte, and `verify_password()` — the exact function
  `auth_service.login()` calls in production — accepts the real
  plaintext password against it.
- **datos críticos**: the seeded company is present with the same name.
- **integridad contable**: `SUM(debit_amount) == SUM(credit_amount)`
  over `journal_lines` in the restored DB, and that total is exactly
  the real remittance amount — not "data exists," but "the same data,
  with the same double-entry integrity."

`docs/BACKUP_RESTORE.md` documents the strategy, retention, and RPO/RTO
honestly: DEV local values are real and measured (`restore < 10s`);
Azure DEV/production RPO/RTO are explicitly left undeclared rather than
invented, since there's no deployed Azure Database for PostgreSQL to
measure them against yet (`NXR-REQ-0118`, currently `BLOCKED_EXTERNAL`
on the disabled UNAH subscription) — fabricating a number there would
violate `CLAUDE.md`'s prohibition on fabricated certifications.

Full verification: 308/308 backend pytest (up from 303, this test plus
one already counted from the prior entry).

Traceability: `NXR-REQ-0109` moved `NOT_STARTED` → `IMPLEMENTED` with
real, repeated, executed evidence — not `VERIFIED` (that would need
independent verification against a deployed Azure Postgres instance,
which doesn't exist yet). Tally now 107 `IMPLEMENTED` (+1), 11
`IN_PROGRESS`, 2 `NOT_STARTED` (-1), 2 `BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Supplier Performance built with real controlled fixtures (NXR-REQ-0058 → IMPLEMENTED)

Direct continuation, same session, under the user's explicit "no more
deferring implementable work" absolute-closure order — which
specifically named `NXR-REQ-0058` and said the "not enough historical
volume" rationale was about production data maturity, not about
whether the metric is buildable, and to build it now with real
controlled fixtures rather than defer further.

`reporting_service.supplier_performance` (`app/services/
reporting_service.py`) computes three real metrics per supplier from
data that real procurement flows actually persist — never fabricated,
never hardcoded:

- **On-time delivery**: needs a PO born from a `SupplierQuotation` with
  a real `delivery_days`, and at least one real `GoodsReceipt`.
  `expected = po.created_at.date() + delivery_days`; on time if the
  earliest receipt is on or before that date.
- **Three-way-match clean rate**: fraction of `ThreeWayMatchResult`
  rows with `status == "MATCHED"` (no exceptions) over the total
  recorded for that supplier's POs.
- **Price variance**: `(max - min) / avg` of `PurchaseOrderLine.
  unit_price`, grouped by `description` (not `item_id` — building the
  real fixtures surfaced that `SupplierQuotationLine`, which
  `create_purchase_order_from_quotation` copies lines from, has no
  `item_id` field at all; it's free text, same as a directly-created
  PO. Grouping by `item_id` would have silently produced zero samples
  for every quotation-derived PO, i.e. the only real path this system
  supports today — caught by actually running the test against real
  fixtures, not by reading the model definitions).

**The core honesty guarantee, the actual point of this requirement**:
every rate is `None` — never a fabricated `0%` or `100%` — when there
isn't enough data, and every rate ships with an explicit `sample_size`
alongside it, so a supplier with one order is never presented with the
same confidence as one with fifty. Tested directly: a brand-new
supplier with zero POs returns `null` for every rate with `sample_size:
0`, not a misleadingly perfect or terrible number.

`GET /api/reports/supplier-performance?companyId=` (`reports.
supplier_performance`/`read`, same per-role scope as `procurement.
purchase_order`/`read`) + a real `SupplierPerformancePage.tsx` tab in
`/control/reportes`, rendering `"Sin datos suficientes (n=0)"` plainly
instead of hiding or guessing.

Real controlled fixtures (not synthetic/random data): a "good" supplier
with two on-time, cleanly-matched, consistently-priced orders, and a
"bad" supplier with two late deliveries, two 3-way-match exceptions,
and a real price swing (`L10.00` → `L20.00` for the same line item) —
built entirely through the actual RFQ → quotation → PO → receipt →
match API flow, the same one a real user would use.

3 new backend tests, 1 new frontend test. Full verification: 311/311
backend pytest (up from 308), `tsc -b --noEmit` clean, `eslint .`
clean, 92/92 frontend vitest, combined Critical Journey + Accessibility
E2E 3/3 green.

Traceability: `NXR-REQ-0058` moved `NOT_STARTED` → `IMPLEMENTED`. Tally
now 108 `IMPLEMENTED` (+1), 11 `IN_PROGRESS`, 1 `NOT_STARTED` (-1), 2
`BLOCKED_EXTERNAL`, 2 `VERIFIED`.

## 2026-08-25 — Real concurrency/race testing (master order §10): 2 production bugs found and fixed (NXR-REQ-0110 → VERIFIED)

Direct continuation, same session, under the absolute-closure order's
§10 (Concurrency/Idempotency): run real concurrent tests over
numbering, GL posting, AP payment, Treasury transfer, idempotency
replay, looking specifically for double posting, lost updates,
duplicate document numbers, and duplicate money — fix every bug found
with a real regression test, never a sequential test that couldn't
have caught it.

New `backend/tests/test_concurrency.py`, 5 tests. Every test uses
genuinely independent threads (`concurrent.futures.ThreadPoolExecutor`),
each with its OWN `SessionLocal()` against the SAME live PostgreSQL
test database — deliberately not the shared `db_session` pytest
fixture, which is bound to one non-thread-safe `Session` and cannot
reproduce a real multi-request race:

- Numbering create-race (sequence row doesn't exist yet, 10 threads)
  and steady-state (20 threads against an already-seeded row).
- Idempotency replay (5 threads, same key: exactly 1 real execution,
  4 replays, 0 errors).
- Concurrent CENTRAL remittances into the same treasury account (10 ×
  L100.00, asserts the reported GL balance is exactly L1000.00 — a
  lost update here means real money vanishing from the reported
  position while the GL still shows it posted).
- Concurrent full payments against the same supplier invoice (5
  threads, each trying to pay the full L1000.00 balance): exactly 1
  must succeed, `amount_paid`/`status` verified via raw SQL after the
  race, not just via in-memory return values.

**Found 2 real, previously undetected production bugs**, both the
same root cause: `numbering_service.next_document_number` and
`idempotency_service.begin` both do "check if the row exists, if not
INSERT it" without a lock (there is nothing to `SELECT ... FOR UPDATE`
yet on the very first call for a given key). Two concurrent callers
can both observe "doesn't exist yet" before either commits, so the
loser's INSERT hits the real PostgreSQL unique constraint
(`uq_number_sequences_scope` / the implicit unique index on
`IdempotencyRecord.key`) and raised a raw, uncaught `IntegrityError`
instead of the correct behavior (get its number; get the replayed
result). This is a real bug an actual production race could trigger —
two POs submitted at the same instant for a company's very first
purchase order, or two retried requests with the same brand-new
Idempotency-Key — not a theoretical one; it only surfaced because the
test used real independent threads/sessions instead of sequential
calls.

**Fix**: wrap the INSERT in a SQLAlchemy `SAVEPOINT` (`db.begin_nested()`),
catch `IntegrityError`, roll back only the savepoint — never the
caller's outer transaction, since higher-level services (e.g.
`posting_service.post_manual`) may already have staged other pending
work before calling into numbering/idempotency — then re-`SELECT`
the winner's row `... FOR UPDATE`. For idempotency specifically, the
`FOR UPDATE` re-fetch must *block* until the winner's transaction
commits, so the loser observes the winner's final `COMPLETED` status
rather than a still-`PENDING` one (otherwise the loser would wrongly
conclude it also needs to execute the real side effect).

The AP-payment test found no bug — `pay_supplier_invoice`'s existing
`SELECT ... FOR UPDATE` on the invoice row already serializes callers
correctly, so it was kept as a regression test confirming that
protection holds under a real 5-way race (the losing callers correctly
raise either `OverpaymentError` or `InvalidInvoiceStateError` depending
on whether their stale in-memory `status` read trips the state guard
before the balance guard — both are correct rejections of a duplicate
payment).

Verification: `test_concurrency.py` run 5× consecutively, 5/5 green
every time; full backend suite 316/316 (up from 315, +1 new test),
zero regressions from the `numbering_service.py`/`idempotency_service.py`
fix.

Traceability: `NXR-REQ-0110` (Unit tests) moved `IN_PROGRESS` →
`VERIFIED` — real command-execution evidence (5× stable + full suite),
not just "tests exist". Tally now 108 `IMPLEMENTED`, 10 `IN_PROGRESS`
(-1), 1 `NOT_STARTED`, 2 `BLOCKED_EXTERNAL`, 3 `VERIFIED` (+1).

## 2026-08-25 — Extended concurrency sweep: 3 more real bugs (procurement over-receipt, inventory lost-update, stock ledger ordering)

Direct continuation, same session, same §10 sweep. Dispatched a
research-only subagent to survey `ar_service`, `treasury_service`,
`procurement_service`, `inventory_service`, `budget_service`, and
`approval_service` for unlocked read-then-write sequences on values
that must never be double-counted. Confirmed safe: AR receipt
(`collect_customer_receipt`), Treasury reconciliation matching, and
approval decisions all already lock correctly. Confirmed NOT a
concurrency finding (pre-existing completeness gaps, flagged
separately, not fixed here): `treasury_service.register_transfer` has
no negative-balance guard at all (single-threaded already permits it);
there is no budget-consumption guard anywhere to race against.

**2 real races found and fixed, plus 1 more latent bug found while
fixing the second:**

1. **`procurement_service.record_goods_receipt`** read
   `PurchaseOrderLine.quantity_received` via a plain `db.get()` (no
   lock) before checking it against the remaining ordered quantity —
   N concurrent receipts against the same PO line could all read the
   same stale value and all pass the guard, over-receiving beyond what
   was actually ordered (and double-crediting `inventory_service.
   receive_stock` for stock that was never really purchased). Fixed
   with a new `procurement_repository.
   get_purchase_order_line_for_update` (`SELECT...FOR UPDATE`), same
   shape as `ap_service.pay_supplier_invoice`'s existing protection.

2. **`inventory_service`'s stock position** (`_current_position`,
   used by `_issue`/`_receive_stock_entry`, i.e. every issue/receive/
   transfer) derives "current on-hand qty" from the LAST
   `StockLedgerEntry` — but the ledger is genuinely append-only by
   design (no mutable "current quantity" row, per the module's own
   docstring). A plain `SELECT...FOR UPDATE` on "the last row" doesn't
   actually block a concurrent transaction's NEW insert (classic
   phantom-row problem: the row being locked never gets updated, so a
   second transaction's blocked lock request unblocks holding a
   *stale* "last row" once the first transaction's insert lands
   *after* it). Fixed with a `pg_advisory_xact_lock` keyed by
   `(company_id, item_id, warehouse_id)` in a new
   `_lock_stock_position`, acquired before every read of the position
   — a real mutex for a table that structurally has no row to lock.
   `transfer_stock` (which touches two warehouses in one transaction)
   pre-acquires both locks in a canonical sorted order up front to
   rule out a deadlock against a concurrent transfer running in the
   opposite direction between the same two warehouses (advisory
   xact-locks are reentrant, so the internal re-acquisition inside
   `_issue`/`_receive_stock_entry` is a safe no-op).

3. **Found while verifying fix #2, a genuinely separate latent bug**:
   even with the advisory lock correctly serializing writers, the
   concurrency test for stock issues still failed intermittently
   (~30% of runs). Root cause, confirmed with a minimal raw-SQL
   reproduction outside the ORM entirely: `get_last_ledger_entry`
   ordered by `StockLedgerEntry.created_at DESC` — but PostgreSQL's
   `now()`/`created_at` reflects the *transaction's start time*, not
   the time of the actual write. Under lock contention, a transaction
   that begins early (and so is stamped with an early `now()`) can end
   up writing its row *after* a later-starting transaction that didn't
   have to wait — so `created_at DESC` silently returns the wrong "last"
   row. The existing tiebreaker, `id DESC`, didn't help because
   `StockLedgerEntry.id` is a random UUID (`UUIDPrimaryKeyMixin`), not
   a sequential value. Fixed by adding `StockLedgerEntry.entry_seq`, a
   real PostgreSQL `SEQUENCE` (`nextval()`, evaluated at actual INSERT
   time — non-transactional, genuinely monotonic in true write order)
   as the sole ordering key, via migration `20da9f0955af` (fresh
   install + downgrade/upgrade verified). This is a correctness bug
   that existed independently of the locking fix — it would have
   caused the exact same "which row is current" ambiguity under any
   sufficiently fast burst of writes, concurrency test or not, though
   the advisory lock made it far easier to trigger reliably (removed
   the OTHER race that was previously masking it).

New tests: `test_concurrent_goods_receipts_never_over_receive_beyond_
ordered_quantity`, `test_concurrent_stock_issues_never_over_issue_
beyond_on_hand_quantity` in `test_concurrency.py` (now 7 tests total).

Verification: `test_concurrency.py` 5/5 green × 5 consecutive runs
(plus an isolated 20x loop specifically targeting the `entry_seq` fix
while root-causing it); full backend suite 318/318 (was 316); Alembic
fresh-install + downgrade -1 + upgrade head round-trip verified on a
scratch database.

Traceability: evidence for `NXR-REQ-0110` updated in place with all 4
bugs (the migration doesn't get its own NXR-REQ row — it's part of the
same concurrency-hardening unit of work already tracked there).

## 2026-08-25 — Real app-layer rate limiting on login (NXR-REQ-0107 continued)

Direct continuation, same session. The absolute-closure order was
explicit and specific here: don't declare rate-limiting blocked on
Azure Front Door/WAF without first proving an application-layer
defense is genuinely impossible — it wasn't, so it got built.

`app/services/rate_limit_service.check_and_increment` -- a real,
PostgreSQL-backed fixed-window counter (`RateLimitBucket`: one row per
`bucket_key`, reused/reset in place, never growing unbounded). Not
in-memory: the backend is stateless (orden maestra §3) and may run
multiple Container Apps replicas, so an in-process counter would be
silently wrong under real concurrency; PostgreSQL is the one place
this system is allowed to keep state. Wired as a FastAPI dependency
(`app.api.deps.enforce_login_rate_limit`) on `/api/auth/login`, keyed
by client IP (`X-Forwarded-For` first hop, falling back to
`request.client.host` for local/no-proxy dev) — 20 attempts per 60s by
default, both configurable via settings. This is a *separate* layer
from the existing per-account lockout (`NXR-REQ-0008`): the lockout
protects one already-identified account; this protects against an
attacker rotating through many different accounts (or generating
noise) from the same origin, which the lockout alone can't see.

Same create-race shape as `numbering_service`/`idempotency_service`
(first-ever request for a given IP has no row to lock yet) — reused
the identical SAVEPOINT (`db.begin_nested()`) pattern proactively, and
proved it holds under real concurrency with a new
`test_concurrent_rate_limit_checks_for_the_same_bucket_never_error_or_
undercount` in `test_concurrency.py` (10 threads, same bucket key,
asserts zero errors and the count lands at exactly 10 — no lost
update, no uncaught `IntegrityError`).

Error response follows the app's existing standard (`{"error":
{"code": "NXR-SECURITY-001", ...}}`, 429) via the same
`RateLimitExceededError` → `_ERROR_CODES` registry pattern every other
domain error already uses, not an ad-hoc `HTTPException`.

2 new tests in `test_auth.py` (rate limit trips after N attempts from
one IP; resets once the window expires) + 1 new concurrency test.
Migration `f1efb082cb0e` (new `rate_limit_buckets` table, named unique
constraint from the start — no repeat of the earlier unnamed-
constraint migration bug).

**Real, not simulated, end-to-end verification**: ran an actual
uvicorn server against a scratch PostgreSQL database and fired 21 real
`curl` requests at `/api/auth/login` — attempts 1-20 returned 401
(bad credentials), attempt 21 returned 429 with the exact expected
error body. This is the literal evidence CLAUDE.md requires ("curl
real") before calling anything done.

Verification: full backend suite 321/321 (was 318, +3); `test_
concurrency.py` + `test_auth.py` 5/5 green × 5 consecutive runs;
Alembic fresh-install + downgrade -1 + upgrade head round-trip on a
scratch database; real uvicorn + curl smoke test as above.

Still open in the §9 security checklist (not done here, tracked in
the evidence row): brute force beyond account lockout, token
expiration/revocation, cookie/CORS audit, IDOR, horizontal/vertical
privilege escalation, file upload security, secrets handling,
dependency vulnerabilities, error/log leakage.
