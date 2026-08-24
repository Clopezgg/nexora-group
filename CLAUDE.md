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

## 6. Roadmap por fases

El proyecto avanza por fases (`FASE 0/1`, `FASE 2`, ...). Cada fase tiene un
objetivo verificable explícito entregado por el usuario. No se inventan
fases ni alcance no solicitado.
