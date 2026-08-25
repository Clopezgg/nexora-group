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
- ~~`DEFERRED-FINAL-002`~~ — RESUELTO en Task 7 (2026-08-25): se recontaron
  las 124 filas de `docs/REQUIREMENTS_TRACEABILITY.md` línea por línea
  contra el resumen prosa y se corrigió un desfase de 1 fila (NXR-REQ-0033
  estaba IMPLEMENTED en la tabla pero faltaba en la enumeración del
  resumen). El resumen ahora coincide exactamente con la tabla: 0 VERIFIED
  + 69 IMPLEMENTED + 26 IN_PROGRESS + 27 NOT_STARTED + 2 BLOCKED_EXTERNAL
  = 124. Sigue aplicando el recontado en cada integración de track a
  futuro.
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
- `DEFERRED-FINAL-008` — **RESUELTO (2026-08-25, Track D Task 2,
  `track/d-workforce-ui`).** Workforce/Time todavía no tenía pantalla de
  frontend (backend/API/RBAC/tests ya estaban completos). Ahora existen
  `WorkersPage` (`/recursos/personal`) y `TimeEntriesPage`
  (`/recursos/tiempo`): lista/crea trabajadores y registros de tiempo,
  aprueba/rechaza contra la API real, filtros por proyecto/fecha/estado,
  y muestra el `labor_cost` server-computed (nunca calculado en el
  cliente). 4 tests nuevos (`WorkersPage.test.tsx`,
  `TimeEntriesPage.test.tsx`), RED/GREEN real (ver
  `docs/PROGRESS.md`). Pendiente de revisión/merge del coordinador a
  `feat/nexora-greenfield` — no se marca `VERIFIED` en
  `docs/REQUIREMENTS_TRACEABILITY.md` hasta que eso ocurra.
- `DEFERRED-FINAL-009` — **RESUELTO (2026-08-25, plan
  `2026-08-25-track-d-construction-control`, Tasks 1/3/4, todas
  fusionadas a `feat/nexora-greenfield`).** Cuando se escribió este item
  el bloque CONSTRUCTION CONTROL completo estaba NOT_STARTED. Ahora:
  Documents/Evidence (`NXR-REQ-0077/0078/0079`, Task 1, ver
  `docs/DOCUMENTS_EVIDENCE.md`), RFI/Submittals (`NXR-REQ-0085/0086`,
  Task 4, dominio+DB+service+API+RBAC+`RfiPage`/`SubmittalsPage` reales),
  y Daily Site Reports/Quality/Safety (`NXR-REQ-0081/0082/0083/0084`,
  Task 3, con constraint real de PostgreSQL para PROJECT-scoped
  obligatorio y para severidad→responsable, UI real
  `DailyReportsPage`/`QualityPage`/`SafetyPage`) están todos
  implementados y fusionados. Ver `docs/PROGRESS.md` y
  `docs/REQUIREMENTS_TRACEABILITY.md` para el detalle; ninguno se marca
  `VERIFIED` todavía.
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
- `DEFERRED-FINAL-013` — Track E: la migración de Alembic hace
  `customer_invoices.customer_id` `NOT NULL` sin ruta de backfill.
  Verificado por el task reviewer (Task 6, 2026-08-24): es una migración
  incremental nueva (`f1075e290473`) encima de la revisión ya publicada
  `58ce35982711`, no una edición de esa revisión. Seguro hoy porque no
  existe data real todavía en ningún ambiente; sigue abierto como
  recordatorio de que un ambiente sembrado con datos antes de un backfill
  explícito requeriría uno.
- `DEFERRED-FINAL-014` — No existe ningún mecanismo real de audit log en
  el codebase todavía (ni `AuditLog` ni repositorio equivalente) —
  confirmado sistémico, no específico de un track: `INV-AUD-001` en
  `docs/ACCOUNTING.md` ya está `IN_PROGRESS`/dueño Track G. Surgió
  explícitamente durante el review de Track D construction-control Task 1
  (Documents/Evidence, 2026-08-25): cada mutación de Document/Evidence
  queda sin rastro de auditoría, igual que el resto del sistema hoy.
  Prioridad para cuando se construya Track G (Workflow/Approvals/Audit/
  Notifications) — no bloquea Documents/Evidence ni los tracks que los
  consuman mientras tanto (Daily Site Reports/Quality/Safety, RFI/
  Submittals).
- `DEFERRED-FINAL-015` — Track D (Task 3, Site/Quality/Safety): no existe
  todavía ningún directorio/selector de usuarios en el frontend (ningún
  track anterior lo construyó — Track A tampoco lo necesitó para
  `approved_by`/`uploaded_by`, que siempre usan el usuario autenticado
  actual). `NonConformance`/`CorrectiveAction`/`SafetyObservation`/
  `SafetyIncident` requieren `responsible_user_id`; `QualityPage.tsx`/
  `SafetyPage.tsx` lo resuelven con un campo de texto UUID pre-rellenado
  con el usuario autenticado (editable para asignar a otro usuario si se
  conoce su UUID de memoria) en vez de un selector real con nombres.
  **Corrección (2026-08-25, review de Task 3): `responsible_user_id` NO
  está realmente validado por el backend.** `quality_service.py`/
  `safety_service.py` no tienen ningún chequeo de existencia ni de
  pertenencia a la compañía sobre ese campo — solo existe la FK cruda de
  PostgreSQL. Un UUID que no corresponde a ningún `User` no produce un
  error de validación limpio: como no hay un handler genérico de
  violación de FK en `app/api/error_handlers.py`, la inserción falla con
  un `IntegrityError` sin capturar, que sale como un 500 no controlado, no
  como un 422 con código `NXR-*`. Y un UUID que sí existe pero pertenece a
  un usuario de **otra compañía** se acepta sin ningún rechazo — no hay
  equivalente a `assert_evidence_belongs_to_company` para
  `responsible_user_id`, así que hoy es posible asignar la responsabilidad
  de una no conformidad/incidente a un usuario de otra compañía sin que el
  sistema lo impida. Este gap es el mismo patrón preexistente que ya tiene
  `treasury_service.create_cash_closing` en otro track — no es nuevo de
  esta tarea, pero tampoco estaba documentado hasta ahora. Se resuelve
  agregando (a) un chequeo de existencia + pertenencia a compañía sobre
  `responsible_user_id` en `quality_service`/`safety_service` (mismo
  criterio que `assert_evidence_belongs_to_company`), (b) un handler de
  `IntegrityError` de FK genérico o específico en `error_handlers.py`, y
  (c) un endpoint de listado de usuarios por compañía (no existe hoy) para
  reemplazar el campo de texto por un `Select`/`Combobox` real.

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
