# Cierre — ORDEN MAESTRA DEFINITIVA DE INTEGRACIÓN OPERATIVA (2026-09-01)

Documento de evidencia de cierre para la ejecución de la ORDEN MAESTRA de
integración operativa. **No** declara "100% CERTIFIED": lista lo entregado
con evidencia y lo que queda pendiente.

## Referencias

| Concepto | Valor |
|---|---|
| Rama de trabajo | `work/nexora-integrated-erp-final` (fusionada y borrada) |
| PR | [#92](https://github.com/Clopezgg/nexora-group/pull/92) — `feat: integrate NEXORA project-to-payment ERP experience` |
| Commit en `main` | `e93e142e7cae8368032b4e70e0914964e9fb0f56` (squash) |
| CI de rama (verde) | run `33515365948` — backend / frontend / e2e / docker-compose / bicep ✓ |
| CI de `main` (verde) | run `33516833462` — todos los jobs ✓ |
| Deploy Azure (real) | run `33518405139` — `workflow_dispatch` `deploy=true`, `main@e93e142` |
| "Deploy infra + apps" | **success** (NO skipped) |
| Imagen backend desplegada | `ghcr.io/clopezgg/nexora-backend:e93e142e7cae8368032b4e70e0914964e9fb0f56` |
| Frontend (SWA) | `https://jolly-plant-0d6bf700f.7.azurestaticapps.net` |
| Backend (Container App) | `nexora-backend-dev` — revisión sana, `runningStatus: Running` |
| Cabeza de migración | `d5a7c9e30f66` |
| Ruleset de `main` (§42) | `22017503` — require PR + checks (backend/frontend/e2e) + block force-push + block deletion — **active** |

## Migraciones aplicadas en producción

```
a1c3e5f70b21 -> b2d4f6a80c33   supplier_contracts.contract_category + número único por compañía + projects.manager_user_id
b2d4f6a80c33 -> c4f6a8b20d55   suppliers: dirección estructurada (§26)
c4f6a8b20d55 -> d5a7c9e30f66   evidence.derived_blob_key / derived_mime_type — render HEIC->JPEG (§28)
```

Single head. Roundtrip upgrade/downgrade verificado en DB fresca y existente
antes del despliegue. `pillow-heif 1.6.0` instalado en la imagen.

## Verificación de producción

### Step "Verify production" del propio deploy (run 33518405139)
- Frontend `/` → HTTP 200
- SWA `/api/healthz` → 200 · `/healthz` → 200
- API first-party health → 200 · DB readiness → 200
- Ruta Protected Edit → HTTP 405 (existe) · token inválido → **HTTP 403 (fail-closed, sin fallback)**
- Cookie de sesión: `Secure` + `HttpOnly` + `Path=/`
- `auth/me`, `master-data/companies` (1 visible), `projects`, `master-data/accounts`, `dashboard/summary` (HNL), `fiscal/periods/current` → HTTP 200
- `auth/logout` → 204 · relogin → 200

### Smoke funcional adicional (endpoints nuevos, sin auth)
| Endpoint | Código | Interpretación |
|---|---|---|
| `GET /api/financial-control/cash-flow-actual/series?...` | 401 | registrado |
| `GET /api/procurement/suppliers/contracts?...&category=LABOR` | 401 | registrado, acepta `category` |
| `GET /api/evidence/{id}/render` | 401 | ruta nueva registrada |
| `GET /api/contract-payments/schedules/{id}/fifo-preview` | 405 | POST-only registrado |
| `POST .../fifo-preview` | 401 | registrado |

Ningún endpoint nuevo devuelve 404.

## Entregado (con test)

- **WS1 (P0 §5/§6/§7/§10)** — Home sin S1–S13: módulo compartido
  `features/finance/cashflow/`, `series()` con rangos 1M/3M/6M/12M y
  granularidad Auto/Día/Semana/Mes, etiquetas de calendario, resumen visible.
- **WS2 (§13/§15/§16)** — `contract_category` full stack, `contract_number`
  único por compañía, `Project.manager_user_id` FK.
- **WS3 (P0 §20-25)** — el formulario real de pago de una factura ligada a
  contrato muestra el contexto contractual y genera `ContractPaymentAllocation`
  por FIFO.
- **WS4 (P0 §11/§17/§18/§19/§35)** — ubicación en el alta, `ProjectWizard`
  guiado (borrador/activar), `ProjectDetailPage` como object page con
  pestañas, pestaña "Contratos" con tarjetas.
- **WS5 (§25/§26/§28/§30)** — dirección estructurada de proveedor, categoría
  del contrato en el comprobante, pipeline HEIC→JPEG real (`DEFERRED-FINAL-019`
  cerrado), beneficiario buscar-o-crear.
- **WS6 (§36/§37)** — vista previa de temas con períodos reales, FilterBar en
  Contratos.
- **§42** — ruleset de `main` aplicado.

## Segunda iteración (PR #94 — WS5 §27 + WS6 §50)

- **WS5 §27** — comprobante premium: membrete corporativo con identidad
  completa de la empresa emisora (razón comercial/legal, RTN, dirección,
  teléfono · correo · **sitio web**) + tarjeta de metadatos del documento +
  QR; `_styles()` documentado como sistema tipográfico DEL DOCUMENTO,
  independiente de los temas de UI; banda "PAGADO A / BENEFICIARIO" / "PAGADO
  POR"; `_section()` uniforma la jerarquía; bloque TOTAL PAGADO a 20pt; pie de
  página en cada hoja (NEXORA GROUP · Comprobante · Verificación · Página X).
  `company_website_snapshot` (migración `e6b8d0c41a77`). Test
  `test_voucher_pdf_is_a_premium_corporate_document`.
- **WS6 §50** — `e2e/visual-audit.spec.ts`: 8 rutas autenticadas + el
  asistente de proyecto a 1440/768/390 con gates reales (sin scroll
  horizontal de página, nada fuera del viewport, objetivo táctil ≥ 32px en
  móvil, sin S1..S13). Hallazgo corregido: `.nx-linkbutton` del flujo de caja
  era 20×20 → 32px mínimo. Corre en CI vía `npm run test:e2e`.

## Pendiente

- **WS6 §31-38** — profundización estructural adicional de temas por familia
  (dialogs/drawers/object-page con tratamientos perceptiblemente distintos
  entre Horizon/Quartz/Belize/NEXORA más allá de lo ya diferenciado en PR-D).
- **WS7** — captura visual del Home DESPLEGADO en producción confirmando
  ausencia de S1–S13 en el navegador (requiere credenciales de la sesión de
  producción, que no están disponibles en este entorno) y verificación
  visual de los 4 temas en el build de producción.

No se usa la frase reservada de cierre: queda §31-38 estructural y la
verificación visual en el navegador de producción.
