# NEXORA GROUP — Reglas permanentes del proyecto

Estas reglas gobiernan este repositorio y tienen prioridad sobre cualquier
hábito o patrón aprendido de proyectos anteriores. Si el contexto de una
sesión de Codex se pierde o se reinicia, este archivo es la fuente de
verdad de la misión.

## 1. Naturaleza del proyecto

- **NEXORA GROUP es greenfield.** Se construye desde cero absoluto.
- **NO Frappe.** No se reutiliza, importa ni referencia código de Frappe.
- **NO ERPNext.** No se reutiliza, importa ni referencia código de ERPNext.
- **NO código legacy.** Ningún archivo, patrón, migración, workflow, test o
  Dockerfile del sistema anterior (`Gesti-n-de-Construcci-n-Residencial` /
  `NEXORA_WORKSPACE`) se copia o adapta automáticamente a este repo.
- El sistema anterior es **únicamente referencia funcional READ-ONLY**: solo
  se consulta si el usuario lo pide explícitamente, nunca se copia código ni
  arquitectura desde ahí.

## 2. Reglas de dominio (no negociables)

- **Treasury es dueño del dinero.** Toda posición de caja, ingreso y egreso
  vive en Tesorería. Ningún otro módulo posee saldo.
- **Project jamás posee efectivo.** Un proyecto puede tener presupuesto,
  compromisos y gasto imputado, pero nunca custodia dinero.
- **OperationScope = `CENTRAL` | `GENERAL` | `PROJECT`.** Es el ámbito de una
  operación financiera/administrativa. Es un concepto de **backend/dominio**.
- **ActiveUIContext es independiente de OperationScope.** Es el proyecto/vista
  activa seleccionada por el usuario en la UI. Nunca deben confundirse ni
  fusionarse en el mismo concepto o el mismo campo.

## 3. Reglas técnicas

- **Backend stateless.** El backend no depende de estado en memoria del
  proceso entre requests; toda sesión y estado persistente vive en
  PostgreSQL.
- **PostgreSQL** es la única base de datos soportada.
- **Azure-compatible.** El backend corre en Azure Container Apps (consumption
  plan); arranca con `$PORT`/puerto fijo del contenedor y no asume
  infraestructura fuera de lo declarado en `infra/` (sin Redis, sin Celery,
  sin colas, salvo que se decida explícitamente lo contrario).
- **No filesystem persistente.** No se asume disco persistente entre deploys;
  cualquier evidencia/archivo subido usa Azure Blob Storage
  (`EVIDENCE_BACKEND=azure_blob`), no `/var/...` local.
- **No mocks presentados como funcionalidad real.** Un endpoint que no está
  implementado de verdad no debe devolver datos inventados como si fueran
  reales; debe reflejar su estado real (vacío, 501, o UI en EmptyState).
- **No hardcoded financial data en producción.** Ninguna cifra financiera se
  hardcodea; todo se calcula desde la base de datos.
- **No self-patching CI.** El pipeline de CI no se modifica a sí mismo para
  forzar un verde.

## 4. Reglas de proceso

- **Build first.** Prioriza tener el sistema arrancando de extremo a extremo
  sobre completar features individuales en profundidad.
- **Bugs no bloqueantes pueden diferirse**, pero deben quedar documentados,
  no ocultados.
- **Nunca declarar algo terminado sin prueba.** "El código parece correcto"
  no es verificación. Antes de marcar cualquier fase como completa: ejecutar
  tests, typecheck, lint, build, y confirmar comportamiento real (curl,
  navegador, logs). Ver `superpowers:verification-before-completion`.

## 5. Stack oficial

**Frontend:** React + TypeScript + Vite, React Router, TanStack Query,
React Hook Form, Zod, Recharts, PWA.

**Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic,
psycopg, Argon2id para contraseñas.

**Testing:** Pytest (backend), Vitest + React Testing Library (frontend),
Playwright (E2E, fases posteriores).

**Deploy:** Microsoft Azure (Static Web Apps, Container Apps, PostgreSQL
Flexible Server, Blob Storage, Key Vault, Monitor/Application Insights),
optimizado para el menor costo posible (consumption plan, tier Burstable/Free
donde exista). Infraestructura como código en Bicep (`infra/`). Render fue la
plataforma inicial del bootstrap y quedó completamente descartada — ver
`docs/DEFERRED.md` y `infra/README.md`.

## 6. Misión (ORDEN MAESTRA)

Este proyecto ya no avanza por fases sueltas: opera bajo una **ORDEN MAESTRA
ÚNICA** (registrada en `docs/MASTER_PLAN.md`) que define la construcción
completa de NEXORA GROUP como ERP empresarial de construcción. Si el
contexto de una sesión se pierde, **este archivo + `docs/MASTER_PLAN.md` +
`docs/REQUIREMENTS_TRACEABILITY.md`** son la fuente de verdad — no se
reinterpreta el alcance desde cero, se retoma desde estos documentos.

NEXORA se inspira conceptualmente en el modelo integrado de SAP (master
data, accounting, controlling, treasury, procurement, inventory, projects,
assets, workflows, reporting, UX por rol) pero NO es un clon de SAP ni de su
UI propietaria.

## 7. Los tres pilares innegociables

1. **TREASURY** — dinero real. Toda posición de caja/banco vive aquí.
2. **OPERATION SCOPE** (`CENTRAL` | `GENERAL` | `PROJECT`) — ámbito de una
   operación financiera/administrativa, concepto de backend/dominio.
   `CENTRAL` y `GENERAL` ⇒ `project_id IS NULL` (constraint real en
   PostgreSQL). `PROJECT` ⇒ `project_id` requerido.
3. **ACTIVE UI CONTEXT** — proyecto/vista activa del usuario en la UI. Nunca
   se muta implícitamente por una operación con `project_id IS NULL`.

No inventar sinónimos ("Proyecto General", "Caja Central de Proyectos",
etc.) para estos conceptos.

## 8. Contabilidad — invariantes no negociables

- El **General Ledger es la verdad contable**; Treasury Ledger es movimiento
  de dinero; el documento fuente explica el negocio; Project/WBS es
  atribución; Budget es control. No mezclar estos conceptos.
- Doble partida real: `TOTAL DEBIT == TOTAL CREDIT` en cada
  `AccountingDocument`, como constraint/invariante de dominio, no como
  convención de UI.
- Todo posting pasa por un **Posting Engine central** (`PostingRule` /
  `PostingService`) — nunca débitos/créditos hardcodeados en controllers.
- Documento contabilizado (`posted`) es **inmutable**: no `UPDATE`, no
  `DELETE`. Corrección = reversal/correction enlazado al original.
- Registro completo de invariantes en `docs/ACCOUNTING.md`
  (`INV-ACC-*`, `INV-TRE-*`, `INV-OPS-*`, `INV-CTX-*`, `INV-BUD-*`,
  `INV-PROC-*`, `INV-INV-*`, `INV-IDEM-*`, `INV-AUD-*`, `INV-SOD-*`,
  `INV-COMP-*`) con test asociado a cada uno.

## 9. Rúbrica de avance — FIJA E INMUTABLE

No se redefine, no se le bajan pesos, no se infla el porcentaje reportado.
Ver desglose completo y estado real en `docs/MASTER_PLAN.md` y
`docs/REQUIREMENTS_TRACEABILITY.md`. Un requisito solo cuenta si tiene
domain + DB + backend + API + frontend (si aplica) + autorización + audit +
test — nunca por scaffold/TODO/mock/interfaz vacía/placeholder.

## 10. Filosofía de ejecución

- **0–90%: Build width first.** Construcción masiva por tracks, vertical
  slice → test dirigido → integrar → commit → push → siguiente slice.
- **90–100%: Feature freeze.** Solo DEFERRED, bugs, seguridad, migraciones,
  testing completo, performance, Azure, certificación de producción.
- Un checkpoint reportado al usuario **nunca es una entrega final** ni un
  punto de parada — se continúa automáticamente con el siguiente trabajo
  independiente disponible.
- `DEFERRED-FINAL-XXX` para bugs no bloqueantes: deben volver a ser
  prioridad al 90% y llegar a cero antes de certificar 100%.
- `EXTERNAL-BLOCKER-XXX` para bloqueos externos legítimos (credenciales,
  suscripciones, autorizaciones que Codex no puede resolver por sí mismo):
  no detienen el resto de la construcción.

## 11. Dos excepciones explícitas a "no preguntes nada"

La ORDEN MAESTRA autoriza avanzar sin pedir permiso en decisiones normales
de ingeniería (commits, push a la rama de trabajo, correcciones, tests,
merges de rama de trabajo). Dos excepciones se mantienen siempre,
independientemente de esa autorización general:

1. **Ningún `az deployment ... create` (ni acción equivalente) que
   provisione recursos Azure reales y facturables se ejecuta sin una
   confirmación explícita puntual en ese momento.** La suscripción Azure
   activa en esta máquina pertenece al tenant de la Universidad Nacional
   Autónoma de Honduras (UNAH), no a una cuenta de negocio del usuario —
   comprometer gasto recurrente ahí excede lo que una autorización general
   puede cubrir. Preparar y validar IaC (`az bicep build`,
   `what-if`) sí está siempre autorizado.
2. **Nunca declarar "100% CERTIFIED" ni marcar un requisito `VERIFIED` sin
   evidencia real** (comando ejecutado, test pasando, curl real, captura de
   comportamiento). Si el estado real es parcial, se reporta el porcentaje
   real con evidencia — nunca se infla para cerrar una conversación.

## 12. Roadmap / tracks

El desglose de tracks paralelos (Financial Core, Project Control, Supply
Chain, Enterprise Resources, Commercial, Experience, Platform) y su estado
vivo se mantienen en `docs/MASTER_PLAN.md` y `docs/PROGRESS.md`. No se
inventan fases nuevas fuera de lo que la ORDEN MAESTRA ya cubre.


<!-- NEXORA RECOVERY CONTEXT -->

# NEXORA GROUP — Persistent Recovery and Continuity Rules

## Identity

This repository is the current official NEXORA GROUP codebase.

Do not treat this as a greenfield project unless the repository itself proves
that a component truly does not exist.

The repository, its current Git history, tests, configuration, documentation,
database definitions, migrations, APIs and existing implementation are the
primary source of truth.

## Mandatory startup procedure

Before significant implementation work:

1. Inspect `git status`.
2. Inspect the current branch.
3. Inspect recent commits.
4. Read the root documentation and relevant package manifests.
5. Read `.nexora-context/PROJECT_STATE.md` when present.
6. Read `.nexora-context/DETECTED_COMMANDS.md` when present.
7. Inspect existing code before proposing replacements.
8. Determine what already works, what is partially implemented, and what is
   actually missing.
9. Preserve all valid existing work.

Do not ask the user to reconstruct project history that can be recovered from
Git or the repository.

## Continuity

A previous OpenCode, Codex or Claude session may have stopped because of:

- provider rate limits;
- context limits;
- model limits;
- interrupted terminal sessions;
- exhausted credits;
- network failures.

These interruptions DO NOT mean the project should be restarted.

When session history is unavailable, reconstruct the current state from:

- Git;
- the source tree;
- AGENTS.md;
- `.nexora-context/PROJECT_STATE.md`;
- documentation;
- tests;
- build output;
- CI configuration;
- migrations and schemas;
- TODO/FIXME markers;
- current modified files.

## Safety

Never run destructive recovery commands merely to make the tree clean.

Do NOT automatically execute:

- `git reset --hard`
- `git clean -fd`
- force checkout of modified files
- force push
- deletion of untracked user work
- destructive database reset
- removal of production data
- mass replacement of existing modules

without explicit user authorization.

Never silently discard local modifications.

## Architecture

Respect the architecture already established by the repository.

Before creating a new:

- page;
- component;
- service;
- API endpoint;
- database table;
- authentication flow;
- permission system;
- utility;
- hook;
- schema;
- workflow;

search for an existing implementation first.

Prefer extending the existing system rather than creating parallel,
duplicated architecture.

## Engineering quality

Fix root causes rather than hiding symptoms.

Do not mark work complete simply because a command was skipped or an error was
suppressed.

For each meaningful change, run the relevant verification supported by this
repository, such as:

- type checking;
- linting;
- unit tests;
- integration tests;
- build;
- database validation;
- application smoke tests.

Use the project's actual scripts rather than inventing commands when existing
scripts are available.

## Errors

When an error occurs:

1. capture the exact error;
2. identify the component causing it;
3. inspect the relevant implementation;
4. determine root cause;
5. make the smallest correct fix;
6. rerun the failed verification;
7. check for regressions.

Do not repeatedly retry an API or LLM provider when it is returning an explicit
rate-limit response.

A model/provider rate limit is infrastructure state, not a code defect in
NEXORA.

## Provider/model independence

Project knowledge must live in the repository and persistent instruction files,
not only in one model's conversation history.

Switching models or providers must not cause the project to lose its logic.

Never rewrite architecture solely because a new model lacks prior chat memory.

## Git discipline

Before modifying code, understand current branch and working tree state.

Keep unrelated user changes intact.

Do not automatically commit or push unless the current task explicitly calls
for it.

When commits are requested, keep them coherent and verify the repository before
push.

## Definition of done

Do not claim a task is complete until relevant checks have actually passed.

If something cannot be verified, explicitly state what remains unverified.

<!-- END NEXORA RECOVERY CONTEXT -->
