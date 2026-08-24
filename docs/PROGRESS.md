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
