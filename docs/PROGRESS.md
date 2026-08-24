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
