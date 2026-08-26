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
- `DEFERRED-FINAL-014` — **RESUELTO (2026-08-25 Track G Task 1 + 2026-08-26 backlog burn-down total).**
  No existía ningún mecanismo real de audit log en el codebase. Ahora
  existe `AuditLog` real (`app/models/audit.py`, append-only, nunca
  UPDATE/DELETE), invocado explícitamente desde la capa de ruta (nunca
  hook oculto de ORM, nunca cambio de firma de servicio existente) —
  ver `docs/AUDIT.md`. **COBERTURA COMPLETA 2026-08-26:** los 56
  routes de mutación del codebase están instrumentados con atomic audit
  (commit=False + audit_service.record() + db.commit()). Dominios:
  Financial Core (AP/AR/Treasury/GL), Supply Chain (Procurement/
  Inventory/Stock), Project Control (Project/WBS/Task/Milestone/Budget/
  ChangeOrder/Progress), Enterprise Resources (Workforce/Assets/
  Equipment), Commercial/CRM, Construction Control (RFI/Submittals/
  Quality/Safety/SiteReport/Documents/Evidence), Platform (Company/
  Account/TaxCode/User), Notifications, Approvals, Workflow. 10 service
  layers ganaron `commit: bool = True`. Si audit falla, toda la
  mutación hace rollback. Solo queda E2E como futuro work item.
- `DEFERRED-FINAL-015` — **RESUELTO (2026-08-25, sin worktree separado —
  construido directamente en `feat/nexora-greenfield`, mismo día que el
  Critical Journey E2E que confirmó el gap por segunda vez de forma
  independiente).** Las tres piezas del plan original están construidas:
  (a) `assert_user_belongs_to_company` (nueva, en
  `financial_validation_service.py`) valida `responsible_user_id` antes
  de persistir en `quality_service.create_non_conformance`/
  `create_corrective_action`, `safety_service.create_observation`/
  `create_incident`, y también en `treasury_service.create_cash_closing`
  (el "mismo patrón preexistente" que este mismo texto ya señalaba abajo
  — cerrado también, aunque ahí `responsible_user_id` siempre es
  `user.id` del propio requester, nunca input externo, así que es
  defensa en profundidad, no un gap explotable real como en Quality/
  Safety). "Pertenece a la compañía" = `UserCompanyAccess` explícito, o
  `core.user`/`create` en SCOPE_ANY (Administrator-only) — deliberadamente
  NO "cualquier resource/action en SCOPE_ANY": varios roles operativos
  (Project Manager) tienen SCOPE_ANY solo en lecturas puntuales sin ser
  miembros reales de cada compañía, y Auditor tiene SCOPE_ANY en lecturas
  de todo el sistema sin ninguna acción de escritura/asignación real —
  ninguno de los dos debe poder "pertenecer" a una compañía a la que
  nunca se le dio acceso explícito (confirmado por un bug real que los
  tests atraparon durante la construcción: el primer intento usaba
  cualquier SCOPE_ANY como señal y dejaba pasar a un Project Manager de
  otra compañía). (b) `_integrity_error_handler` genérico
  (`app/api/error_handlers.py`, `NXR-DATA-001`/422) para cualquier FK sin
  validador específico que aún así llegue a violarse — loguea el mensaje
  real de psycopg, nunca lo devuelve al cliente. (c)
  `GET/POST /api/master-data/users` (`core.user` create/read,
  create=Administrator-only vía `_BASE_PERMISSIONS`, read=mismo scope por
  rol que `core.company`/read) — primera API real de creación de
  usuarios más allá del bootstrap Administrator inicial.
  `QualityPage.tsx`/`SafetyPage.tsx`/`AccountsPayablePage.tsx`
  (submit-for-approval) reemplazaron sus campos de texto UUID por un
  `Select` real poblado desde este endpoint.
  `frontend/e2e/critical-journey.spec.ts` ya no necesita su workaround de
  subprocess de Python para crear el segundo usuario del Approval Inbox
  — usa el endpoint real. 10 tests backend nuevos
  (`test_user_management.py`, más casos en `test_quality.py`/
  `test_safety.py`/`test_error_handlers.py`), 290/290 backend + 89/89
  frontend + Critical Journey E2E 2/2 en verde tras el cambio.

  Texto original del gap, preservado para contexto histórico: no existía
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
- `DEFERRED-FINAL-016` — **RESUELTO (2026-08-25, `NXR-REQ-0023`, sin
  worktree separado — construido directamente en
  `feat/nexora-greenfield`).** Track G (Task 3, Notifications, 2026-08-25):
  `approval_service.create_request` no tenía todavía ningún llamador real
  en producción — confirmado por grep sobre todo `backend/app`: ni
  `ap_service.py` ni `submittal_service.py` lo invocaban, ambos solo
  registraban su adaptador de `decide()` vía `register_decision_adapter`
  (`app/main.py`). El disparo de notificación "assigned_to al crear un
  ApprovalRequest" (Task 3) estaba correctamente conectado al único punto
  real de creación, pero ese punto en sí mismo nunca se ejecutaba en un
  flujo de negocio real — código muerto arquitectónicamente correcto, no
  un defecto de Task 3. Resuelto conectando `ap_service` (candidato más
  claramente acotado frente a Submittal, que ya tenía su propio flujo
  `respond`/`decide` sin concepto de asignación): `ap_service.
  submit_supplier_invoice_for_approval` (DRAFT -> REVIEW) llama
  `approval_service.create_request(...)` de verdad, vía
  `POST /api/ap/supplier-invoices/{id}/submit-for-approval`. Decidir esa
  solicitud desde `/api/approvals/{id}/decide` ahora ejecuta el adaptador
  `ap_service.apply_approval_decision` por primera vez desde un flujo de
  negocio real, no solo desde un test que llama `decide()` directamente.
  `submittal_service` sigue sin conectar — su propio flujo de decisión
  interno (`respond`/`decide`, sin Approval Inbox) queda como posible
  subproyecto futuro independiente si se decide que Submittal también
  debe pasar por el Inbox genérico. Ver `docs/PROGRESS.md` y
  `docs/REQUIREMENTS_TRACEABILITY.md` (fila `NXR-REQ-0023`).

- `DEFERRED-FINAL-017` — Track H (plan
  `2026-08-25-reports-search-analytics`): hardening menor detectado en las
  revisiones finales. El PATCH de Company resuelve un ID inexistente con un
  `ValueError` sin handler antes del chequeo de acceso (respuesta 500 y
  superficie menor de enumeración) y repite un `db.get()` ya hecho por la
  ruta. Trial Balance ejecuta una consulta de balance por cuenta (N+1;
  correcto funcionalmente, pendiente de optimizar a agregado si crece el
  plan de cuentas). El tipo de fila CSV usa un index-signature workaround
  cosmético. El build frontend sigue avisando que el chunk principal supera
  500 kB y necesita code splitting antes de la certificación de performance.
  Ninguno altera los resultados verificados de este plan, pero todos deben
  revisarse durante FINAL HARDENING.
- `DEFERRED-FINAL-018` — 2026-08-25, NXR-REQ-0025 (Corrections):
  `posting_service.register_reversal_hook` sincroniza el status de
  `SupplierInvoice`/`CustomerInvoice` cuando se revierte su documento de
  *accrual* (`SIN`/`CIN`). Revertir el documento de un **pago o recibo**
  (`PAY`/`REC` -- mismo `source_type` que el accrual, distinto
  `document_type_code`) se rechaza explícitamente
  (`InvalidInvoiceStateError`, `NXR-AP-001`/409) en vez de dejar un
  estado a medias, porque no existe todavía un flujo que reduzca
  `amount_paid`/`amount_collected` y reabra la factura de forma
  consistente. Ningún dominio lo ha necesitado todavía (no hay caller que
  intente revertir un `PAY`/`REC` en producción); si aparece esa
  necesidad real, construir `ap_service.reverse_payment`/
  `ar_service.reverse_receipt` con el mismo criterio (validar estado,
  reducir el monto pagado/cobrado, reabrir la factura al estado que
  corresponda) en vez de ampliar el hook existente a ciegas.
  `asset_service`/`procurement_service` (`DepreciationEntry`,
  `goods_receipt`) también postean con `source_type` propio y no tienen
  hook de reversal registrado todavía -- mismo patrón, sin caller
  reachable que lo haya necesitado en esta sesión; revisar si Enterprise
  Resources/Procurement construyen un flujo de reversal para esos
  documentos antes de asumir que ya está cubierto.

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
