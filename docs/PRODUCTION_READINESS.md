# NEXORA GROUP — Production Readiness Gate (Definición Absoluta de 100%)

## Live production evidence — 2026-08-27

The earlier Azure authorization/provisioning blocker is no longer current.

- Production main before PR #11: `ed3d3822247bd7f8447bd965d06b6e72313d66bf`.
- Deploy Azure run #21: PASS (Bicep what-if, OIDC login, backend image build/push, Bicep deployment, frontend build and Static Web Apps deployment).
- Frontend: `https://jolly-plant-0d6bf700f.7.azurestaticapps.net/`.
- Same-origin API probes: `/api/healthz` and `/api/readyz` returned `{"status":"ok"}` on 2026-08-27.
- Container App direct ingress is intentionally protected by the Static Web Apps linked-backend integration.
- PR #11 (`work/nexora-final-product`) contains the final product/UI pass and is not production evidence until CI, merge, Deploy Azure and authenticated smoke tests complete.

Do not interpret historical BLOCKED/NOT_STARTED language below as the current Azure state; it is retained as chronology.


Este documento registra la ORDEN MAESTRA de extensión final recibida
2026-08-25: la definición de "100%" que prevalece sobre cualquier
definición anterior. Si el contexto de una sesión se pierde, este
archivo + `CLAUDE.md` + `docs/MASTER_PLAN.md` +
`docs/REQUIREMENTS_TRACEABILITY.md` son la fuente de verdad — no se
reinterpreta esta orden desde cero.

**Estado actual (2026-08-26):** 113/124 requisitos completos (110
IMPLEMENTED + 3 VERIFIED). 11 requisitos restantes: 8 IN_PROGRESS
(Azure infrastructure, BLOCKED por §11.1), 1 NOT_STARTED (OIDC), 2
BLOCKED_EXTERNAL (production). Ver `docs/REQUIREMENTS_TRACEABILITY.md`
para el detalle fila por fila.

**No aplicar todavía.** Esta orden gobierna la fase 90-100% (feature
freeze → certificación de producción). Mientras el sistema esté en
Build Width First (completando tracks funcionales, actualmente
construyendo Track G), estos gates NO son trabajo activo — son la
definición de destino. Ejecutarlos prematuramente sobre un sistema
todavía incompleto sería desperdiciar el trabajo (p.ej. un load test
antes de que existan los módulos que se van a cargar).

**Regla no negociable:** ninguna de las frases "implementation
complete", "code complete", "feature complete", "all modules merged",
"tests pass locally", "DEV works", "ready for production", "95%",
"99%" significa terminado. El sistema no está terminado hasta que sea:
funcional + financieramente íntegro + seguro + auditable + recuperable
+ observable + desplegado + probado + fusionado + certificado en
producción.

## Checklist de certificación final (orden de ejecución, §45 de la orden)

Cada bloque abajo corresponde a una sección de la orden maestra
recibida 2026-08-25. Al llegar a feature freeze (90% real, verificado
en `docs/REQUIREMENTS_TRACEABILITY.md`), estos bloques se ejecutan en
este orden, sin detenerse entre etapas salvo por la excepción de
autorización PROD (`CLAUDE.md` §11.1):

1. **Environments** — contratos claros LOCAL/DEV/PROD (y STAGING si
   corresponde): DATABASE_URL, API URL, CORS, Storage, Key Vault,
   logging, telemetry, auth, flags, migration behavior, allowed
   origins. Safeguards contra que DEV apunte a PROD o que tests
   escriban en PROD.
2. **CI/CD completo** — PR gates (tests, typecheck, lint, build,
   migration validation, security checks), main gates (build
   artifacts, deploy workflow), production gates (deployment
   reproducible, migrations controladas, health/readiness, smoke,
   rollback). Reconstruible desde Git + Azure config por cualquier
   agente autorizado.
3. **Container/image certification** — build reproducible, dependencias
   pineadas, servidor no-dev, startup/health/readiness/graceful
   shutdown, sin debug mode ni dev secrets, logging de producción.
4. **Database backup/restore** — estrategia, retención, point-in-time
   recovery si el tier lo permite, RPO/RTO documentados, **al menos
   una prueba real de restore** en destino no productivo (backup →
   restore → migrations/state → login → datos críticos → integridad
   contable).
5. **Disaster recovery** — procedimiento documentado y ejecutable para
   frontend/backend/PostgreSQL/Storage caídos, bad deployment/
   migration, config corrupta, secret filtrado, borrado accidental de
   recursos. Sin arquitectura multi-region si no es necesaria.
6. **Deployment rollback** — probado o demostrado de forma
   reproducible para frontend, Container App, configuración;
   estrategia explícita para migraciones no reversibles (git revert no
   revierte la base de datos).
7. **Data integrity certification** — SUM(debits)=SUM(credits) por
   documento, ningún posted document mutable, sin journal lines
   huérfanas; Treasury sin cash ownership en Project y reconciliable
   con GL; AP/AR balance coherente con pagos/cobros; PO vs receipts vs
   invoices coherentes; stock ledger vs on-hand coherente; budget/
   commitment/accrual/payment/actual cost coherentes; sin FKs
   huérfanas, claves duplicadas, estados imposibles, negativos
   imposibles, contaminación cross-company.
8. **Concurrency/race testing** — numbering, posting, idempotency
   replay, AP payment, AR receipt, Treasury transfers, reconciliation
   matching, inventory receiving/issue, approvals, budget consumption.
   No basta con tests secuenciales donde podría duplicarse dinero,
   inventario o documentos.
9. **Performance/load** — login, dashboard, project list, Treasury
   position, GL/reporting, global search, tablas grandes, procurement/
   inventory listing. Thresholds razonables, corregir N+1/missing
   indexes/queries lentas/payloads excesivos/bundle issues.
10. **Pagination/scale safety** — toda colección potencialmente grande
    (journal lines, invoices, audit logs, notifications, documents,
    inventory ledger, procurement history, search results) con
    pagination/limit-offset/cursor/filtering.
11. **Security certification** — auth (hashing, sesión, logout,
    brute-force/lockout, cookies/tokens seguros), authorization
    (escalación horizontal/vertical, company/project isolation, IDOR),
    input (SQLi, XSS, path traversal, uploads), secrets (sin
    commitear/loguear, Key Vault, rotación), headers/CORS de PROD,
    dependencias sin vulnerabilidades conocidas sin deshabilitar el
    checker.
12. **File/document security** — company/project authorization en
    Documents/Evidence, límites de upload, sanitización de filename,
    prevención de colisión de storage key, container no público salvo
    intención explícita, reglas de delete/versioning, inmutabilidad de
    evidence donde corresponda.
13. **Audit completeness** — actor, action, entity_type, entity_id,
    company, project/scope, before/after cuando sea seguro, request_id,
    correlation_id, timestamp; nunca secretos completos en before/
    after; append-only.
14. **Observability** — structured logging, request_id/correlation_id/
    operation_id, document_number, user ID seguro, company, project/
    scope, código NXR-*, health/readiness, Application Insights,
    métricas útiles, captura de excepciones. Nunca loggear passwords/
    tokens/secrets completos.
15. **Alerting** — backend unavailable, high error rate, Container App
    failure, PostgreSQL connectivity, failed deployment, fallos
    excesivos, storage/key vault críticos. DEV económico, sin ruido.
16. **Cost control** — inventario de recursos y costo aproximado,
    Azure budget/cost alerts, retención sana de Log Analytics, sin
    recursos huérfanos, sin API Management, sin ambientes duplicados
    accidentales. Revisar `az resource list` post-deploy.
17. **Privacy/data exposure** — schemas de respuesta deliberados: sin
    password hashes, auth tokens, Key Vault data, secrets internos,
    datos personales innecesarios, banking info fuera de rol, datos
    cross-company.
18. **Accessibility final** — keyboard nav, focus visible, labels,
    error associations, landmarks, headings semánticos, botones vs
    links correctos, contraste, touch targets móviles, tablas usables,
    focus behavior en modals/drawers.
19. **Browser/device matrix** — Desktop Chromium, Safari/WebKit si hay
    tooling, viewport móvil y tablet. No afirmar Safari probado si no
    se ejecutó.
20. **Offline/PWA safety** — installable, manifest válido, service
    worker, API financiera NETWORK ONLY, sin mutación financiera
    offline, sin respuesta sensible cacheada incorrectamente.
21. **Date/time/money correctness** — Decimal/Numeric (nunca float
    financiero), currency explícita, rounding definido; timezone
    behavior, date-only vs datetime, UTC storage cuando corresponda,
    sin timezone de máquina local en posting timestamps críticos.
22. **Tax/FX completeness** — si aplica: fuente/ownership de exchange
    rate, effective date, validación de currency, rounding, audit; tax
    codes/cálculo/posting/invoice integration/reporting. Si un
    componente se excluye legítimamente, justificar explícitamente en
    MASTER_PLAN/TRACEABILITY, nunca ignorarlo en silencio.
23. **Financial statements cross-check** — Trial Balance (debit=credit),
    Balance Sheet (Assets=Liabilities+Equity), P&L derivado de cuentas
    reales, Cash Flow no inventado; verificar contra documentos
    contables de prueba conocidos.
24. **Report exports** — probar export real (no solo el botón) en el
    formato que la arquitectura decidió (CSV/XLSX/PDF).
25. **Search certification** — autorización, company isolation, tipos
    de entidad, pagination, sin data leakage, ranking/filtering usable,
    deep-link correcto; probar resultados reales para Project/Supplier/
    Customer/Invoice/PO/Document/RFI/Asset/Equipment y demás entidades
    obligatorias.
26. **Notifications certification** — create/read/unread/mark
    read/authorization/company isolation/workflow event/approval
    event/financial-project event relevante. Sin notificaciones falsas.
27. **Workflow/SoD certification** — requester no puede aprobar cuando
    la política lo prohíbe, approver no puede ejecutar cuando se
    requiere un tercer rol, transición no autorizada rechazada,
    aprobación duplicada segura, item rechazado se comporta
    correctamente, existe entrada de audit, existe notificación.
28. **Seed/bootstrap/first run** — instalación limpia reproducible:
    migrations, master data esencial, roles/permisos, admin inicial,
    bootstrap de company, chart of accounts, currencies/document types
    iniciales. Sin editar la DB manualmente, sin credenciales por
    defecto inseguras.
29. **Documentation final** — README, architecture, local setup, DEV/
    PROD deployment, migrations, backup/restore, disaster recovery,
    security, RBAC, accounting, Azure, CI/CD, troubleshooting. Sin
    referencias a Render/Frappe/ERPNext como arquitectura activa.
30. **Runbook** — login failure, API down, DB down, failed migration/
    deployment, restore, secret rotation, scale issue, high errors,
    rollback, emergency disable/recovery. Concreto y ejecutable.
31. **Release management** — tag/versión (p.ej. v1.0.0) solo cuando
    todos los gates estén certificados; release notes con módulos,
    migraciones, limitaciones legítimas, SHA de deployment, fecha,
    resumen de verificación.
32. **Zero known critical defects** — 0 blocker, 0 critical, 0 bug de
    integridad de datos conocido, 0 issue de seguridad crítico
    conocido, 0 invariante financiero roto. `DEFERRED-FINAL` en 0.
33. **Clean repository** — sin junk generado, sin secrets, sin DBs
    locales, sin temp files, sin conflict markers, sin fuente
    requerida sin trackear. Working tree limpio.
34. **Final independent review** — revisión final del sistema
    integrado completo (no solo el último track): arquitectura,
    invariantes financieros, seguridad, migraciones, integración
    cross-domain, completitud de frontend, tests, Azure, deferreds,
    traceability. Todo finding significativo: fix → test → review
    again.
35. **Traceability final** — recontar cada NXR-REQ con evidencia real;
    para declarar 100% funcional: IN_PROGRESS=0, NOT_STARTED=0,
    BLOCKED_EXTERNAL=0 (excepto una autorización externa legalmente
    insustituible). Si existe BLOCKED_EXTERNAL, nunca decir "100%
    production certified".

## Production deployment (bloques 37-41 de la orden)

Solo después de TODO lo anterior:
1. `feat/nexora-greenfield` → PR/review → gates requeridos → `main`.
2. Verificar `main` directamente post-merge (fetch, checkout, pull,
   verificación de SHA, tests críticos, build, migration head check,
   smoke) — nunca asumir que el merge garantiza estado correcto.
3. Con autorización PROD explícita puntual (`CLAUDE.md` §11.1):
   desplegar el SHA exacto certificado, registrar git SHA/container
   revision/frontend deployment/migration revision/resource group/
   timestamp.
4. Post-deploy certification sobre PROD real: frontend reachable,
   backend health/ready, DB connection, login, permissions, company
   isolation, rutas críticas de lectura, mutación controlada,
   reporting, documents/storage, audit, notifications, persistencia de
   login/logout. Sin generar transacciones financieras basura —
   bootstrap/smoke data controlado.
5. Ventana de monitoreo post-deploy razonable: buscar 500s, restart
   loops, fallos de DB, fallos de CORS/auth, issues de migración,
   errores de assets del frontend. Corregir hallazgos reales.
6. Revisión final de costo: sin API Management, sin recursos
   duplicados, sin servicios accidentales caros, tier de PostgreSQL
   correcto, scaling correcto de Container Apps, logging limitado,
   Storage correcto. Documentar costo estimado.

## Excepción de pausa por autorización PROD

Si lo único que falta es la autorización explícita de aprovisionar
Azure PROD (`CLAUDE.md` §11.1): no declarar 100%. Reportar el avance
real máximo alcanzado, con `BLOCKED_EXTERNAL` único: "Azure production
provisioning authorization". Todo lo demás debe estar completo. Al
recibir la autorización: continuar automáticamente con deploy PROD →
certificación → main/post-main → release → 100%.
