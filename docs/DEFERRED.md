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

**Estado:** ~~RESUELTO~~ (2026-08-30). El job `docker-compose` de
`.github/workflows/ci.yml` levanta Postgres + backend con
`docker compose up -d --build`, aplica migraciones Alembic, verifica
`/api/healthz` y `/api/readyz` == 200 y destruye el entorno
(`docker compose down -v`). Verde en CI a partir del arreglo de
`pre_migration_repairs` (PR #34): el preflight pre-Alembic ya no falla
contra una base de datos limpia. `EXTERNAL-BLOCKER-002` cerrado.

---

Los siguientes items se detectaron durante el plan "interrupted tracks
recovery"
(`docs/superpowers/plans/2026-08-24-interrupted-tracks-recovery.md`, ledger
en `.superpowers/sdd/2026-08-24-interrupted-tracks-recovery/progress.md`).
Ninguno bloquea Build Width First; todos deben llegar a cero antes de
certificar el 100%.

- ~~`DEFERRED-FINAL-001`~~ — **RESUELTO (2026-08-26).** Hook
  `useMutationError` compartido + toast feedback en 22 mutaciones que
  fallaban silenciosamente (procurement/inventory/treasury/approvals/
  documents). Ver `frontend/src/hooks/useMutationError.ts`.
- ~~`DEFERRED-FINAL-002`~~ — RESUELTO en Task 7 (2026-08-25): se recontaron
  las 124 filas de `docs/REQUIREMENTS_TRACEABILITY.md` línea por línea
  contra el resumen prosa y se corrigió un desfase de 1 fila (NXR-REQ-0033
  estaba IMPLEMENTED en la tabla pero faltaba en la enumeración del
  resumen). El resumen ahora coincide exactamente con la tabla: 0 VERIFIED
  + 69 IMPLEMENTED + 26 IN_PROGRESS + 27 NOT_STARTED + 2 BLOCKED_EXTERNAL
  = 124. Sigue aplicando el recontado en cada integración de track a
  futuro.
- ~~`DEFERRED-FINAL-003`~~ — **RESUELTO (2026-08-26).** Se agregó el endpoint
  `GET /api/projects/{id}/budgets` que devuelve todas las versiones de
  presupuesto (BASELINE + REVISED), tal como documenta
  `docs/BUDGET_CONTROLLING.md`.
- ~~`DEFERRED-FINAL-004`~~ — **RESUELTO (2026-08-26).** Predicate de retry
  transient-only en `queryClient.ts`: queries reintentan solo en errores
  5xx/red, nunca en 4xx deterministas. Se eliminó `retry: 1` de las 5
  mutaciones de Treasury (ya tenían idempotencyKey). Mutaciones ahora
  heredan `retry: false` global.
- `DEFERRED-FINAL-005` — **Diseño registrado, no implementable localmente.**
  Transferencias multi-moneda requieren una política FX autoritativa
  (tipo de cambio, fuente, effective date, rounding). La arquitectura
  actual rechaza explícitamente POs de proyecto en moneda distinta a la
  funcional (`NXR-PROCUREMENT-002`, `BudgetCurrencyMismatchError`). Para
  soportar transferencias multi-moneda se necesita: (a) un modelo
  `ExchangeRate` con source/effective_date/rate, (b) un servicio
  `fx_service.convert(amount, from, to, date)`, (c) actualización de
  `treasury_service.create_transfer` para convertir y generar dos asientos
  contables (origen en moneda A, destino en moneda B con ganancia/pérdida
  cambiaria). Esto es un feature completo, no un bug. Documentado para
  que futuras sesiones lo implementen cuando el negocio lo requiera.
- ~~`DEFERRED-FINAL-006`~~ — **IMPLEMENTADO, pendiente de verificación CI
  final (2026-08-29).** Existen pantallas reales dedicadas para
  conciliación bancaria, cierres de caja, restricciones de fondos y
  comprobantes; incluyen matching/unmatch/exclusión, aprobación de cierre,
  disponibilidad/restricciones, selector de documento contable y descarga
  PDF autenticada. El Critical Journey de cierre cubre los cuatro flujos
  contra backend y PostgreSQL reales.
- ~~`DEFERRED-FINAL-007`~~ — **IMPLEMENTADO, pendiente de verificación CI
  final (2026-08-29).** FUEL, MAINTENANCE y LABOR usan configuración
  contable por compañía (`ResourcePostingConfig`), validan pertenencia y
  tipo de cuenta, postean mediante Posting Engine y enlazan el origen con
  `AccountingSourceLink`. La restricción única por source da idempotencia;
  si falta configuración activa el sistema falla cerrado sin inventar
  cuentas.
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
- ~~`DEFERRED-FINAL-010`~~ — **RESUELTO (2026-08-26).** `FixedAssetsPage`
  y `EquipmentPage` fuel log ahora tienen selector de ámbito
  (GENERAL/PROJECT) con selector de proyecto. Antes estaba hardcodeado
  `scope: 'GENERAL'`.
- ~~`DEFERRED-FINAL-011`~~ — **RESUELTO (2026-08-26).** Nuevo
  `InvalidEquipmentStatusError` (`NXR-EQUIPMENT-002`, 422) en vez de
  `InvalidOperationScopeError` (`NXR-ACCOUNTING-002`) para validación
  de status de equipment.
- ~~`DEFERRED-FINAL-012`~~ — **RESUELTO (2026-08-26).** FKs reales
  agregados: `MaintenanceOrder.supplier_id` FK a `suppliers.id` y
  `Project.customer_id` FK a `customers.id`, con migración Alembic
  `a1b2c3d4e5f6`. Los campos `supplier_ref`/`customer_ref` de texto
  libre se mantienen para compatibilidad pero los FKs son la fuente
  de referencia principal.
- ~~`DEFERRED-FINAL-013`~~ — **RESUELTO / CERRADO (2026-08-26).** La
  migración `f1075e290473` hace `customer_invoices.customer_id` NOT NULL
  con FK a `customers.id`. Es seguro porque: (a) es greenfield sin data
  real en ningún ambiente, (b) la migración es incremental nueva sobre
  la revisión publicada, (c) el downgrade es reversible (re-agrega
  `customer_name`, droppa FK y columna). No se necesita backfill porque
  la tabla `customer_invoices` fue creada en el mismo commit que la
  migración (nunca tuvo datos con `customer_name`).
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

- ~~`DEFERRED-FINAL-017`~~ — **RESUELTO (2026-08-26).** Company PATCH:
  `ValueError` → `NotFoundError` (NXR-DATA-002, 404) con handler global
  en `error_handlers.py`. Eliminado `db.get()` duplicado (la ruta ya
  llama `get_by_id`; `update_company` ahora recibe el objeto directamente).
  Trial Balance N+1 → query agregada única (`GROUP BY account.id`).
  El warning de chunk size del build frontend (500 kB) y el
  index-signature cosmético del CSV quedan como items de performance
  menores para certificación, no son DEFERRED funcionales.
- ~~`DEFERRED-FINAL-018`~~ — **IMPLEMENTADO, pendiente de verificación CI
  final (2026-08-29).** AP conserva `SupplierPayment` y AR conserva
  `CustomerReceipt`; ambos crean el asiento inverso, guardan motivo,
  usuario, fecha y documento reverso, restauran monto y estado de factura,
  rechazan doble reversal y registran auditoría. Las páginas separadas de
  AP y Collections muestran historial, estado reversado y modal de motivo;
  el Critical Journey ejecuta ambos reversals y comprueba la restauración.
- ~~`DEFERRED-FINAL-019`~~ — **RESUELTO (2026-09-01, ORDEN MAESTRA §28).**
  `pillow-heif` está en `requirements.txt`. Al subir una foto HEIC/HEIF, el
  original privado se guarda tal cual y `evidence_service._derive_display_jpeg`
  genera un JPEG derivado (`evidence.derived_blob_key` / `derived_mime_type`,
  migración `d5a7c9e30f66`). `GET /evidence/{id}/render` sirve ese derivado
  (inline) y el PDF del comprobante lo embebe vía `voucher_service._evidence_image`
  (usa `render_mime_type` / `download_render`). Conversión real probada en
  `test_evidence.py::test_evidence_heic_gets_a_derived_jpeg_render` con un HEIC
  decodificable generado en el test. Si la decodificación falla, el upload no
  se rompe: el original queda íntegro y descargable.
- `DEFERRED-FINAL-020` — **ABIERTO (2026-09-03, ORDEN MAESTRA DE CIERRE
  FINAL DE PRODUCTO §10/§11).** `Company.logo_evidence_id` /
  `signature_evidence_id` existen como columnas pero nunca se exponen en
  `CompanyUpdateRequest`/`CompanyResponse` ni se leen en ningún service —
  dato muerto, imposible de asignar vía API. El comprobante (`voucher_service.py`)
  no embebe logo ni firma gráfica; falta snapshot en `VoucherIssuance`
  (mismo patrón que `company_footer_snapshot`, que sí se corrigió en esta
  misma orden — ver `voucher_footer_text` ya impreso). Los bancos se
  imprimen solo como texto (`bank_label`); no existe ningún mecanismo de
  logo bancario (evidence-based ni ícono neutral de fallback) — §11 no
  tiene ningún código todavía.
- `DEFERRED-FINAL-021` — **ABIERTO (2026-09-03, ORDEN MAESTRA DE CIERRE
  FINAL DE PRODUCTO §19).** No existe endpoint de AP Aging (`ar_metrics`
  existe en `financial_control_service.py`, su equivalente AP no). Ningún
  reporte financiero tiene exportación XLSX o PDF reales (`openpyxl`/
  `xlsxwriter`/`reportlab` no se usan en `reports.py`); solo el ledger de
  pagos de contrato exporta CSV.

## Bloqueos externos

- ~~`EXTERNAL-BLOCKER-001`~~ — **RESUELTO históricamente.** Azure DEV ya
  existe y sirve frontend + API same-origin. La ejecución final de Deploy
  Azure se certifica después de fusionar PR #21; no se crea APIM.
- ~~`EXTERNAL-BLOCKER-002`~~ — **RESUELTO (2026-08-30).** Ya no depende de
  Docker local: el job `docker-compose` de CI construye y arranca el stack
  real (`docker compose up -d --build`), corre migraciones y comprueba
  `healthz`/`readyz`. Verde tras el arreglo de `pre_migration_repairs`
  (PR #34). Ver `DEFERRED-FINAL-DOCKER-001`.
- ~~`EXTERNAL-BLOCKER-003`~~ — **RESUELTO (2026-08-30).** La facturación de
  GitHub Actions volvió a estar activa: CI y `Deploy Azure` reciben runner y
  ejecutan steps reales sobre `main`. Certificado con el run de `Deploy
  Azure` `33340196708` sobre `main@124cebe` (imagen = SHA exacto, Container
  App `Running`/`Healthy`, `latestRevision == latestReadyRevision`,
  producción verificada: healthz/readyz/CORS/login/cookie/dashboard).
  Historial del bloqueo abajo.
- `EXTERNAL-BLOCKER-003` (histórico) — **BLOQUEADO EXTERNO (2026-08-29):
  facturación de GitHub Actions.** CI run #233 y Deploy Azure run #142,
  incluidos sus reintentos, no iniciaron ningún step. GitHub muestra en cada anotación:
  “The job was not started because recent account payments have failed or
  your spending limit needs to be increased.” Debe resolverse el pago o
  límite en Billing & plans y reintentarse el mismo HEAD. Hasta entonces no
  se permite merge, deploy final ni limpieza de ramas.

  **Reconfirmado 2026-08-30 en `2445d8e3771afda6e95110982e46bd7824e8030b`:**
  PR #24 disparó CI run `33286924542` (run number 241). Los cuatro jobs
  (`backend`, `frontend`, `e2e`, `Compile Azure Bicep`) finalizaron `failure`
  con `steps=[]`; GitHub no ejecutó checkout ni código. Acción manual exacta:
  corregir el pago o elevar el spending limit de GitHub Actions en la cuenta
  propietaria de `Clopezgg/nexora-group`, y re-ejecutar los jobs fallidos del
  run `33286924542`. Criterio de cierre: los cuatro jobs reciben runner,
  ejecutan steps reales y concluyen `success` sobre este HEAD o uno posterior
  que solo contenga correcciones verificadas.
