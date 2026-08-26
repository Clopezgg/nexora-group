# NEXORA GROUP — MASTER PLAN

Fuente de verdad de la ORDEN MAESTRA única (recibida en la sesión que
generó este documento). Si el contexto de Claude se reinicia, este archivo
+ `CLAUDE.md` + `docs/REQUIREMENTS_TRACEABILITY.md` reconstruyen la misión
completa sin necesidad de que el usuario la repita.

## Estado de arranque (ya construido y verificado antes de esta orden)

- Commit base: `62c56eb` — bootstrap greenfield (React/Vite + FastAPI +
  PostgreSQL + Alembic + auth + RBAC básico + dashboard + tests).
- Commit `7821f8a` — infraestructura Azure como código (Bicep validado con
  `az bicep build` y `what-if`, sin recursos reales creados), retiro de
  Render.
- Rama activa: `feat/nexora-greenfield`.
- `DEFERRED-FINAL-DOCKER-001` abierto: verificación en vivo de
  `docker compose up` pendiente (Docker no instalado en la máquina de
  build). Debe cerrarse antes de certificar 100%.

Ninguna de esta base se reconstruye. Se extiende.

## Rúbrica — FIJA E INMUTABLE

| % | Bloque |
|---|---|
| 5% | Platform baseline / Bootstrap |
| 5% | Core & Master Data |
| 5% | Identity / RBAC |
| 8% | Accounting / General Ledger |
| 7% | Treasury |
| 5% | Accounts Payable |
| 4% | Accounts Receivable |
| 7% | Projects / WBS / Planning |
| 6% | Budget / Controlling / Forecast |
| 7% | Procurement |
| 6% | Inventory / Warehouses |
| 4% | Suppliers / Contracts |
| 4% | CRM / Sales |
| 4% | Assets / Equipment / Maintenance |
| 3% | Workforce / Time |
| 5% | Documents / Evidence / Progress / Site / Quality |
| 4% | Workflow / Approvals / Audit / Notifications |
| 4% | Reports / Search / Analytics |
| 4% | Full UX / Responsive / PWA / Accessibility |
| 2% | Azure / Hardening / Production Certification |
| **100%** | **TOTAL** |

"Platform baseline / Bootstrap" (5%) se considera cubierto por el commit
`62c56eb`. Ningún otro bloque se marca completo sin evidencia verificada
(ver `docs/REQUIREMENTS_TRACEABILITY.md`).

## Tracks paralelos

| Track | Alcance | Dependencia |
|---|---|---|
| **1 — Foundation** | Core platform, Master Data, Identity/RBAC ampliado, Chart of Accounts, Posting Engine, General Ledger, OperationScope (constraint real), ActiveUIContext | Ninguna — es la raíz de dependencias de todo lo demás |
| **A — Financial Core** | Treasury, AP, AR (sobre el Posting Engine de Track 1) | Track 1 |
| **B — Project Control** | Projects, WBS, Budgets, Forecast, Progress, Change Orders | Track 1 |
| **C — Supply Chain** | Procurement, Suppliers, Contracts, Inventory, Warehouses | Track 1, integra con A (AP) |
| **D — Enterprise Resources** | Assets, Equipment, Maintenance, Workforce, Documents, Quality, Site Control | Track 1 |
| **E — Commercial** | CRM, Customers, Sales, Contratos comerciales, Billing, Collections | Track 1, integra con A (AR) |
| **F — Experience** | Design System, App Shell, Role Homes, Dashboards, Responsive, Accessibility, PWA | Puede avanzar en paralelo desde ya (bajo riesgo de colisión de archivos con backend) |
| **G — Platform** | Identity avanzada, Workflow engine, Audit, Notifications, Search, Reporting, Integraciones opcionales, Azure, Seguridad, CI, Testing | Se completa incrementalmente junto con cada track funcional |

El agente principal (esta sesión) define contratos, asigna ownership de
archivos por track para evitar colisiones, integra, y resuelve conflictos.
No se permite edición simultánea del mismo archivo central (posting
engine, modelos core, `CLAUDE.md`, documentos de trazabilidad) por más de
un track a la vez.

## Orden de ejecución

1. Track 1 (Foundation) primero — todo lo demás depende de Company,
   Project, Chart of Accounts, Posting Engine, OperationScope.
2. Track F (Experience) en paralelo desde el inicio — bajo riesgo de
   colisión, no bloquea ni es bloqueado por el backend de dominio.
3. Cuando Track 1 aterriza: A, B, C, D, E se construyen incrementalmente,
   cada uno en vertical slices (dominio → DB → servicio → API →
   autorización → audit → frontend → tests → commit → push), integrando
   contra el Posting Engine y Master Data ya existentes.
4. Track G se construye de forma transversal: cada pieza de plataforma
   (audit, workflow, search, reporting) se añade a medida que los módulos
   funcionales que la necesitan van llegando, no al final.
5. Al 90% real (verificado en `docs/REQUIREMENTS_TRACEABILITY.md`):
   feature freeze. Legacy Feature Gap Review (read-only) →
   `docs/LEGACY_FEATURE_GAP.md`. Resolver gaps legítimos + todos los
   `DEFERRED-FINAL-*`.
6. Hardening completo → Bicep/Azure real (con la confirmación puntual de
   despliegue pactada en `CLAUDE.md` §11) → certificación de producción →
   cleanup → entrega. **La definición completa y no negociable de "100%"
   (backup/restore probado, disaster recovery, rollback, seguridad,
   concurrencia, performance, observability, PROD deployment,
   traceability en cero pendientes, etc.) vive en
   `docs/PRODUCTION_READINESS.md` — no se declara 100% ni "production
   certified" sin cumplir ese checklist completo.**

## Excepciones vigentes (ver `CLAUDE.md` §11)

1. Ningún recurso Azure real se crea sin confirmación puntual en el
   momento del primer despliegue.
2. Ningún requisito se marca `VERIFIED` ni se declara 100% sin evidencia
   real ejecutada.
