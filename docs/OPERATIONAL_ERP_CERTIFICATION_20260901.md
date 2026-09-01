# NEXORA GROUP — Certificación operacional ERP (2026-09-01)

Documento de evidencia para la ejecución de la **ORDEN MAESTRA DEFINITIVA DE
INTEGRACIÓN OPERACIONAL ERP**. Lista lo entregado con evidencia real y lo que
queda pendiente. No se infla el porcentaje ni se declara "100% CERTIFIED" si
queda algún P0.

## Objetivo

Auditar los 22 hard gates de §87 contra el código real de `main`, cerrar los
que no estaban cubiertos, integrar, probar, fusionar por PR, desplegar en Azure
y verificar producción.

## Referencias

| Concepto | Valor |
|---|---|
| Rama de trabajo | `work/nexora-operational-erp-final-20260901` (fusionada y borrada) |
| PR | [#98](https://github.com/Clopezgg/nexora-group/pull/98) — `feat: split execution contract cost from PO commitment + fail-closed contractual payments` |
| Commit en `main` (squash) | `56256eca0df49f5c9fbc35912248f22320a81391` |
| CI de rama (verde) | run `33561314892` — backend / frontend / e2e / docker-compose / bicep ✓ |
| CI de `main` (verde) | run `33562770660` — backend / frontend / e2e / docker-compose / bicep ✓ |
| Deploy Azure (real) | run `33564239269` — `workflow_dispatch` `deploy=true`, `main@56256ec` |
| Alembic head | `72aed748da19` (single head) |
| Backend tests (local, PostgreSQL real) | **527 passed** |
| Frontend tests | **184 passed** (`vitest`), typecheck + lint + build ✓ |

## Hard gates §87 — estado

| Gate | Estado | Evidencia |
|---|---|---|
| PROJECT: "+ Agregar contrato" desde el proyecto | ✅ cerrado en PR #98 | `ExecutionContractForm` + `ProjectContractsTab`; test `frontend/tests/ProjectContractsTab.test.tsx` |
| FINANCE: costo contratado ejecución ≠ compromiso PO | ✅ cerrado en PR #98 | `project_financial_service` (`executionContractValue/Paid/Balance`, `poCommitted`); test `test_project_execution_contract_kpi.py` |
| CONTRACT: payment terms explícitos | ✅ cerrado en PR #98 | `SupplierContract.payment_terms_type`, migración `72aed748da19` |
| BACKEND: contractual payment fail-closed | ✅ cerrado en PR #98 | `ap_service.pay_supplier_invoice` 422 sin allocations; test `test_contract_payment_failclosed.py` |
| SCHEDULE required cuando MONTHLY/CUSTOM | ✅ cerrado en PR #98 | mismo test — contrato MONTHLY sin plan ⇒ 422 |
| OVERPAYMENT bloqueado | ✅ pre-existente (PRs #85–#97) | `contract_payment_service.allocate_payment` `OverpaymentError`; `test_contract_payment_control.py` |
| PAYMENT: período contractual ≠ fecha efectiva | ✅ pre-existente | `effective_date` distinto de `posted_at` (PR #85); `test_contract_payment_control.py` |
| HISTORY sin meses futuros | ✅ pre-existente | `contract_payment_service.history_through`; `test_contract_payment_control.py` |
| REVERSAL reabre la cuota | ✅ pre-existente | `reverse_payment_allocations`; `test_contract_payment_allocation_via_ap_endpoint_and_reversal` |
| EVIDENCE integrada al pago | ✅ pre-existente | `ContractInstallmentPanel` + evidencia obligatoria por método (PR #94) |
| PROJECT: pagar cuota contextual | 🔶 parcial | plan de pagos y estado por contrato inline en el Project Cockpit; el drawer de pago end-to-end desde el proyecto sigue apoyándose en el flujo AP existente |
| VOUCHER: evidence + contract history | ✅ pre-existente | comprobante premium §27 (PR #94) |
| TESTS / CI / DEPLOY | ✅ | runs arriba |
| PRODUCTION verified / SHA exact | (ver sección siguiente) | |

## Verificación de producción

| Concepto | Valor |
|---|---|
| Deploy Azure run | `33564239269` — `workflow_dispatch` `deploy=true` |
| "Deploy infra + apps" | **success** (NO skipped) |
| Imagen backend desplegada | `ghcr.io/clopezgg/nexora-backend:56256eca0df49f5c9fbc35912248f22320a81391` — SHA exacto de `main` |
| Frontend (SWA) | `https://jolly-plant-0d6bf700f.7.azurestaticapps.net` |
| Backend (Container App) | `https://nexora-backend-dev.agreeablewave-7d628262.eastus2.azurecontainerapps.io` |

### Step "Verify production" del propio deploy (run 33564239269)
- Frontend `/` → HTTP 200
- SWA `/api/healthz` → 200 · `/healthz` → 200
- First-party API health → 200 · DB readiness → 200
- Ruta Protected Edit → HTTP 405 (existe) · token inválido → **HTTP 403 (fail-closed, sin fallback)**
- Cookie de sesión: `Secure` + `HttpOnly` + `Path=/`
- `auth/me`, `master-data/companies` (1 visible), `projects`, `master-data/accounts`,
  `dashboard/summary` (HNL), `fiscal/periods/current` → HTTP 200
- `auth/logout` → 204 · `auth/me` post-logout → 401 · relogin → 200

### Smoke adicional (endpoints, directo al Container App, sin auth)
| Endpoint | Código | Interpretación |
|---|---|---|
| `GET /api/projects/{id}/financial-summary` | 401 | registrado (auth requerida) |
| `GET /api/procurement/suppliers/contracts?company_id=...` | 401 | registrado |
| `GET /api/contract-payments/schedules?companyId=...` | 401 | registrado |

### Certificación de SHA exacto
```
origin/main HEAD        = 56256eca0df49f5c9fbc35912248f22320a81391
CI main (33562770660)   = 56256eca0df49f5c9fbc35912248f22320a81391
backend image (deploy)  = ghcr.io/clopezgg/nexora-backend:56256eca0df49f5c9fbc35912248f22320a81391
```
Aún no existe metadata `VITE_GIT_SHA` / `GET /api/version` (§62/§63) — pendiente
documentado, no bloqueante. El SHA del frontend desplegado se certifica por el
build del propio deploy sobre `main@56256ec`.

## Pendiente de mayor alcance (documentado, no bloquea los gates cerrados)

- §3 — Project Wizard de 9 pasos (Budget + Contracts + Payment Plan + Documents
  dentro del wizard). Hoy el wizard cubre datos/ubicación/fechas/equipo y el
  resto se configura tras crear el proyecto.
- §8 / §31 — ProjectDetail como command-center completo (compras, avances,
  documentos, auditoría y contabilidad contextualizados sin salir del proyecto).
- §11 — Drawer de "Pagar próxima cuota" contextual con evidencia integrada
  end-to-end desde el Project Cockpit.
- §42 / §44 — Auditoría visual Playwright ampliada a todas las rutas × matriz de
  viewports × familias de tema.
- §47 / §48 — Exportes XLSX/PDF de los reportes ERP y AP/AR Aging.

Estos puntos se retoman en la siguiente iteración de la ORDEN MAESTRA.
