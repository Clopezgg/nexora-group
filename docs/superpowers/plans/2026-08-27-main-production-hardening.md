# Main Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endurecer `main` sin despliegues Azure automáticos y cerrar gaps verificables de tests, audit, seguridad, escala y documentación.

**Architecture:** Cambios compatibles organizados por riesgo. Cada slice empieza con una prueba que reproduce el defecto, aplica el cambio mínimo y termina con verificación y commit independiente.

**Tech Stack:** FastAPI, SQLAlchemy 2, PostgreSQL 16, Pytest, React 19, TypeScript, Vitest, Playwright, GitHub Actions y Azure Bicep.

**Spec:** `docs/superpowers/specs/2026-08-27-main-production-hardening-design.md`

## Global Constraints

- `origin/main` es la única fuente de verdad.
- No force push ni reescritura de historial.
- El Azure existente es DEV; ningún deploy real sin confirmación puntual.
- Treasury conserva ownership exclusivo del dinero.
- `OperationScope` y `ActiveUIContext` permanecen independientes.
- No estado persistente en memoria ni filesystem persistente.
- Ninguna afirmación verde sin comando recién ejecutado.

---

### Task 1: Gate explícito para Azure

**Files:**
- Modify: `.github/workflows/deploy-azure.yml`
- Modify: `infra/README.md`

**Interfaces:**
- Consumes: eventos `pull_request`, `push` y `workflow_dispatch` de GitHub.
- Produces: validación automática; deploy únicamente con dispatch manual confirmado.

- [ ] Cambiar `workflow_dispatch` para solicitar un booleano `deploy` y una razón.
- [ ] Cambiar `jobs.deploy.if` a `github.event_name == 'workflow_dispatch' && inputs.deploy`.
- [ ] Ejecutar `az bicep build --file infra/main.bicep --stdout`.
- [ ] Revisar el YAML y documentar que un push nunca despliega.
- [ ] Commit `ci: require explicit dispatch for Azure deployment` y push a `main`.

### Task 2: Portabilidad reproducible de los tests

**Files:**
- Modify: `backend/tests/test_backup_restore.py`
- Modify: `frontend/src/hooks/useActiveCompany.ts`
- Modify: `frontend/tests/HomePage.test.tsx`

**Interfaces:**
- Consumes: intérprete pytest y Web Storage opcional.
- Produces: subprocess Python hermético y selección de compañía que degrada a memoria.

- [ ] Reproducir el fallo backup/restore ejecutando pytest desde el binario del venv sin activar PATH.
- [ ] Sustituir la búsqueda de `python3` por `sys.executable`; correr el test hasta verde.
- [ ] Agregar un test que importe/renderice con `localStorage` no disponible y verificar que la pantalla sigue funcionando.
- [ ] Ejecutar el test en rojo con Node 22.
- [ ] Implementar lectura/escritura tolerante a ausencia o excepción de storage.
- [ ] Ejecutar Vitest con Node 22 y Node 26.
- [ ] Commit `fix(testing): make local and browser state gates portable`.

### Task 3: CI de calidad y seguridad

**Files:**
- Modify: `backend/requirements-dev.txt`
- Modify: `.github/workflows/ci.yml`
- Modify: `backend/app/models/company.py`
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/models/role.py`
- Modify: `backend/app/models/session.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/user_role.py`

**Interfaces:**
- Consumes: dependencias backend/frontend y source tree.
- Produces: gates compileall, Ruff objetivo, pip-audit, npm audit y Bicep.

- [ ] Agregar imports `TYPE_CHECKING` que resuelvan los forward references reales.
- [ ] Ejecutar `ruff check --select E9,F63,F7,F82 app tests` y verificar verde.
- [ ] Añadir `ruff` y `pip-audit` a dependencias de desarrollo.
- [ ] Añadir los comandos al job backend; añadir `npm audit --audit-level=high` al frontend.
- [ ] Añadir un job IaC que compile `infra/main.bicep` sin desplegar.
- [ ] Ejecutar localmente todos los nuevos gates.
- [ ] Commit `ci: add reproducible quality and security gates`.

### Task 4: Supplier audit atómico

**Files:**
- Modify: `backend/app/api/routes/suppliers.py`
- Modify: `backend/tests/test_supplier_contracts.py`
- Modify: `backend/tests/test_audit_e2e.py`

**Interfaces:**
- Consumes: `audit_service.record`, correlation ID y repositorios existentes.
- Produces: `procurement.supplier.create` y `procurement.contract.create` atómicos.

- [ ] Escribir test que verifica el audit de supplier sin exponer banking details.
- [ ] Escribir test que fuerza fallo de audit y verifica rollback del supplier.
- [ ] Escribir tests equivalentes para supplier contract.
- [ ] Ejecutar los tests y observar ausencia de audit/persistencia incorrecta.
- [ ] Aplicar `flush -> audit -> commit` una sola vez en ambas rutas.
- [ ] Ejecutar tests dirigidos y suite backend.
- [ ] Commit `fix(audit): make supplier mutations atomic`.

### Task 5: Feed de audit paginado e indexado

**Files:**
- Modify: `backend/app/repositories/audit_repository.py`
- Modify: `backend/app/api/routes/audit.py`
- Modify: `backend/tests/test_audit.py`
- Create: `backend/alembic/versions/9c6d4b2a1e70_index_audit_feed.py`

**Interfaces:**
- Consumes: `companyId`, `offset`, `limit` y filtros existentes.
- Produces: misma lista JSON, acotada y ordenada establemente.

- [ ] Escribir tests de default, offset, límite máximo y orden estable.
- [ ] Ejecutar en rojo.
- [ ] Agregar `.offset(offset).limit(limit)` y desempate por `id`.
- [ ] Crear índice `(company_id, created_at DESC, id)` con downgrade.
- [ ] Ejecutar upgrade/downgrade/upgrade y tests de audit.
- [ ] Commit `feat(audit): paginate and index the audit feed`.

### Task 6: Upload de evidencias seguro y compensable

**Files:**
- Modify: `backend/app/api/routes/evidence.py`
- Modify: `backend/app/services/evidence_service.py`
- Modify: `backend/app/integrations/azure_blob.py`
- Modify: `backend/tests/test_evidence.py`

**Interfaces:**
- Consumes: stream `UploadFile`, límite configurado y Azure container client.
- Produces: contenido validado, nombre seguro y compensación de blob huérfano.

- [ ] Escribir test de stream que excede el límite y no consume bytes adicionales.
- [ ] Escribir tests de filename con rutas/control chars y contenido que no coincide con MIME.
- [ ] Escribir test donde audit/persistencia falla y el blob remoto es eliminado.
- [ ] Ejecutar en rojo.
- [ ] Leer en chunks hasta `max+1`, validar firma PDF/imagen y normalizar basename.
- [ ] Agregar helper de delete idempotente y compensación en excepción.
- [ ] Ejecutar tests dirigidos y suite backend.
- [ ] Commit `fix(evidence): bound uploads and compensate failed persistence`.

### Task 7: Probes y documentación canónica

**Files:**
- Modify: `infra/modules/containerapps.bicep`
- Modify: `README.md`
- Modify: `infra/README.md`
- Modify: `docs/MASTER_PLAN.md`
- Modify: `docs/REQUIREMENTS_TRACEABILITY.md`
- Modify: `docs/PRODUCTION_READINESS.md`
- Modify: `docs/DEFERRED.md`
- Modify: `docs/AUDIT.md`
- Modify: `docs/AGENT_HANDOFF.md`
- Modify: `docs/PROGRESS.md`
- Modify: `docs/RBAC.md`
- Modify: `docs/INTEGRATION_ARCHITECTURE.md`

**Interfaces:**
- Consumes: SHA final, resultados locales y runs GitHub del SHA exacto.
- Produces: probes declarados y una sola narrativa verificable de estado.

- [ ] Añadir startup/liveness `/healthz` y readiness `/readyz` a Container Apps.
- [ ] Compilar Bicep.
- [ ] Recontar las 124 filas de traceability desde la tabla.
- [ ] Actualizar evidencia Azure como DEV y eliminar afirmaciones de PROD no sustentadas.
- [ ] Actualizar audit, deferred y readiness con gaps reales restantes.
- [ ] Registrar comandos y resultados de esta ejecución en Progress/Handoff.
- [ ] Buscar referencias obsoletas y corregir solo las secciones canónicas actuales; conservar cronología marcada como histórica.
- [ ] Commit `docs: reconcile main hardening and DEV readiness evidence`.

### Task 8: Verificación final y entrega

**Files:**
- Review: todos los archivos modificados.

**Interfaces:**
- Consumes: todos los slices anteriores.
- Produces: `main` limpio, push sin fuerza y evidencia verificable.

- [ ] Ejecutar suite backend completa sobre PostgreSQL 16.
- [ ] Ejecutar typecheck, lint, Vitest Node 22, build y Playwright.
- [ ] Ejecutar compileall, Ruff objetivo, pip-audit, npm audit y Bicep.
- [ ] Ejecutar `git diff --check`, revisar commits y working tree.
- [ ] Fetch `origin/main`; integrar solo fast-forward o rebase seguro si cambió.
- [ ] Push final a `main` sin force.
- [ ] Esperar CI del SHA final y reportar cualquier gate o deployment omitido.
