# NEXORA GROUP — Reglas permanentes del proyecto

Estas reglas gobiernan este repositorio y tienen prioridad sobre cualquier
hábito o patrón aprendido de proyectos anteriores. Si el contexto de una
sesión de Claude se pierde o se reinicia, este archivo es la fuente de
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
  suscripciones, autorizaciones que Claude no puede resolver por sí mismo):
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
