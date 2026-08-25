# Pendientes diferidos

Bugs o verificaciones no bloqueantes, documentados en vez de ocultados
(regla de `CLAUDE.md`: "Bugs no bloqueantes pueden diferirse, pero deben
quedar documentados"). Deben resolverse/certificarse antes de declarar el
proyecto al 100% (FINAL HARDENING).

## DEFERRED-FINAL-DOCKER-001

**Qué falta:** verificación en vivo de `docker compose up` (Postgres +
backend vía Docker Compose).

**Por qué está diferido:** Docker no estaba instalado en la máquina donde se
construyó la Fase 0/1. El flujo completo (migraciones, auth, dashboard) se
verificó igualmente end-to-end usando PostgreSQL 16 nativo (Homebrew) en vez
de Docker, así que la aplicación en sí está probada — lo que falta es
confirmar que `docker-compose.yml` y `backend/Dockerfile` funcionan tal cual
están escritos.

**Cómo certificarlo:** en una máquina con Docker instalado, ejecutar
`docker compose up` desde la raíz del repo y confirmar que:
- Postgres arranca y queda healthy.
- El backend arranca, aplica `alembic upgrade head` y responde en
  `/healthz`/`/readyz`.
- El login (`POST /api/auth/login`) funciona contra la base del contenedor.

**Estado:** pendiente. Debe resolverse en FINAL HARDENING antes del 100%.

---

Los siguientes items se detectaron durante el plan "interrupted tracks
recovery"
(`docs/superpowers/plans/2026-08-24-interrupted-tracks-recovery.md`, ledger
en `.superpowers/sdd/2026-08-24-interrupted-tracks-recovery/progress.md`).
Ninguno bloquea Build Width First; todos deben llegar a cero antes de
certificar el 100%.

- `DEFERRED-FINAL-001` — Las páginas de mutación de Track C
  (procurement/inventory) todavía no muestran feedback de error de la API
  al usuario; falta un patrón compartido de error de mutación en la UI.
- `DEFERRED-FINAL-002` — Los totales resumen de
  `docs/REQUIREMENTS_TRACEABILITY.md` quedan desfasados después de cada
  merge de track; deben recontarse en la integración final de
  documentación (no en cada merge individual).
- `DEFERRED-FINAL-003` — `docs/BUDGET_CONTROLLING.md` documenta un endpoint
  de historial de presupuesto que la API no expone realmente; corregir la
  doc o agregar la ruta.
- `DEFERRED-FINAL-004` — Las mutaciones de React Query en el frontend usan
  `retry: 1`, que también reintenta respuestas 4xx deterministas, no solo
  fallos transitorios/de red. Necesita un predicado de retry
  transient-only y una prueba de regresión a nivel de componente.
- `DEFERRED-FINAL-005` — Track A: las transferencias de Treasury en
  múltiples monedas no están soportadas explícitamente (no existe todavía
  una política de conversión).
- `DEFERRED-FINAL-006` — Track A: falta cobertura dedicada de UI/E2E para
  reconciliación, cierres de caja, restricciones de fondos y generación de
  comprobantes; solo existe cobertura a nivel backend/API por ahora.
- `DEFERRED-FINAL-007` — Track D: el posting a GL de bitácoras de
  combustible, costo de mantenimiento y costo de mano de obra está
  diferido intencionalmente (solo la depreciación de activos fijos postea
  hoy a través del Posting Engine).
- `DEFERRED-FINAL-008` — Track D: Workforce/Time todavía no tiene pantalla
  de frontend (backend/API/RBAC/tests están completos).
- `DEFERRED-FINAL-009` — Track D: el slice Documents/Site/Quality está
  NOT_STARTED (no existe dominio, DB, service, API ni UI todavía).
- `DEFERRED-FINAL-010` — Track D: `FixedAssetsPage` y el formulario de
  bitácora de combustible de `EquipmentPage` fijan `scope: 'GENERAL'` en el
  cliente; el backend soporta completamente activos/bitácoras de
  combustible PROJECT-scoped pero la UI todavía no puede crearlos.
- `DEFERRED-FINAL-011` — Track D: `equipment_service.change_equipment_status`
  lanza `InvalidOperationScopeError` (mapea a `NXR-ACCOUNTING-002`) para un
  estado inválido — familia de error semánticamente incorrecta para un
  concern de equipment. Inofensivo hoy porque el schema de la API
  (`Literal[...]`) ya bloquea valores inválidos antes de llegar al service;
  de todos modos debe corregirse a su propia clase de error.
- `DEFERRED-FINAL-012` — Track A/C/D: `MaintenanceOrder.supplier_ref` y el
  patrón original de `CustomerInvoice.customer_ref` de Track A empezaron
  como referencias basadas en texto antes de que tracks posteriores
  entregaran el FK real (Supplier en Task 4, Customer en Task 6). Vigilar
  si queda algún otro track que todavía deba su FK real a una referencia
  basada en texto.
- `DEFERRED-FINAL-013` — Track E (pendiente de revisión al momento de este
  checkpoint): la nueva migración de Alembic hace `customer_invoices.customer_id`
  `NOT NULL` sin ruta de backfill. El implementador reporta que no existe
  data real todavía, así que hoy es seguro, pero el task reviewer debe
  confirmar que esto se hizo como una migración incremental NUEVA encima de
  la revisión `58ce35982711` ya mergeada/pusheada, y no como una edición de
  esa revisión ya publicada, antes de aceptar el Task 6.

## Bloqueos externos

- `EXTERNAL-BLOCKER-001` — Los recursos de Azure (PostgreSQL Flexible
  Server, Container Apps, Static Web Apps, Storage, Key Vault) todavía NO
  están desplegados. La suscripción está ACTIVE, el resource group
  bootstrap y GitHub OIDC están configurados, `az bicep build` y
  `what-if` pasan. No ejecutar `az deployment ... create` (ni acción
  equivalente que aprovisione recursos facturables) sin una confirmación
  explícita puntual del usuario (`CLAUDE.md` §11.1). API Management NO debe
  crearse. Revisar el sizing DEV cost-conscious (tier B1ms de PostgreSQL)
  antes de ese deploy.
