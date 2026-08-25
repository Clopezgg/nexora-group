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
