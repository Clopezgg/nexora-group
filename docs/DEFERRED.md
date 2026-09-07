# NEXORA GROUP — Deferred / Future Scope

**Estado autoritativo del alcance final:** no quedan bugs o funcionalidades obligatorias conocidas clasificadas como `DEFERRED` dentro del alcance de cierre del producto.

Este archivo fue reconciliado el 2026-09-06 durante el cierre de integridad de PR #112. El historial detallado de los antiguos `DEFERRED-FINAL-*` se conserva en Git; no se mantiene aquí texto histórico contradictorio con el producto actual.

## Regla de interpretación

Un elemento solo puede permanecer como `DEFERRED` si pertenece al alcance final aprobado y todavía no está implementado. Ideas futuras, extensiones que requieren una política empresarial todavía no definida o mejoras puramente opcionales se registran en **Future / Optional**, no como deuda necesaria para certificar NEXORA.

Los gates de release — CI, merge, despliegue Azure, smoke y E2E de producción — tampoco son funcionalidades diferidas: son condiciones de certificación y deben estar verdes antes de declarar un SHA como release final.

## Backlog final obligatorio

**0 elementos abiertos conocidos.**

Los últimos gaps funcionales reales detectados en la auditoría final quedaron cerrados así:

- **DEFERRED-FINAL-020 — RESUELTO.** La identidad documental ya no es dato muerto. `Company.logo_evidence_id` y `Company.signature_evidence_id` se administran mediante el perfil de compañía, validando que Evidence pertenezca a la misma empresa. `VoucherIssuance` congela ambos IDs en la primera emisión y `voucher_service` renderiza logo y firma desde Evidence privado, de modo que una reimpresión conserva la identidad histórica aunque el perfil cambie después.
- **DEFERRED-FINAL-021 — RESUELTO.** AP Aging existe mediante el control financiero integrado en PR #110. Los reportes ERP tienen exportación nativa XLSX/PDF mediante `report_export_service`, con rutas autorizadas y acciones de frontend para Trial Balance, Balance General, Estado de Resultados, Flujo de Efectivo, Libro Mayor, Presupuesto vs. Real y Desempeño de Proveedores. Los importes conservan precisión `Decimal` en el backend.
- **DEFERRED-FINAL-006/007/018 — RESUELTOS.** Conciliación/cierres/restricciones/comprobantes, posting automático FUEL/MAINTENANCE/LABOR y reversals AP/AR están incorporados al producto y cubiertos por suites de backend/E2E.
- **DEFERRED-FINAL-019 — RESUELTO.** HEIC/HEIF conserva el original privado y usa derivado JPEG para visualización/PDF cuando la decodificación es posible.
- **DEFERRED-FINAL-DOCKER-001 — RESUELTO.** Docker Compose smoke es un job real del CI y valida PostgreSQL, migraciones, backend, `/api/healthz` y `/api/readyz`.

## Decisiones de alcance explícitas

### Transferencias internas entre monedas diferentes

El producto final soporta de forma autoritativa transferencias de Treasury **entre cuentas de la misma moneda**. Una transferencia interna entre monedas distintas permanece deliberadamente bloqueada: NEXORA no inventa un tipo de cambio ni una cuenta de ganancia/pérdida cambiaria.

El modelo `Currency/ExchangeRate` existe como master data, pero habilitar conversión automática de tesorería requiere que NEXORA GROUP defina primero una política empresarial autoritativa para:

- fuente y propietario del tipo de cambio;
- fecha efectiva aplicable;
- regla de redondeo;
- tratamiento de diferencias de cambio;
- cuentas contables de ganancia/pérdida FX;
- aprobación/auditoría de la tasa.

Hasta que esa política exista, rechazar una transferencia cross-currency es el comportamiento financiero correcto y fail-closed, no un bug pendiente. No se permite usar una tasa implícita o `1.0` para simular soporte multidivisa.

### Branding de bancos

El comprobante usa el nombre de la institución y la cuenta enmascarada, y la identidad oficial del emisor proviene del logo/firma privados de la compañía. No se empaquetan logotipos de bancos de terceros ni se descargan desde Internet. Un catálogo visual de marcas bancarias puede añadirse en el futuro si existe una fuente de assets autorizada; no es necesario para la integridad financiera ni documental del comprobante.

### QA humana asistiva

La accesibilidad automatizada se valida con Playwright/axe y rutas reales. Una pasada manual con VoiceOver/NVDA sigue siendo una actividad humana recomendada, no una funcionalidad de software pendiente.

## Future / Optional — fuera del candado de cierre

Estas capacidades pueden desarrollarse si el negocio las solicita posteriormente; no son defectos del release actual:

1. Conversión automática de Treasury entre monedas con política FX aprobada.
2. Catálogo autorizado de logotipos de instituciones bancarias.
3. Integraciones externas adicionales no exigidas por el núcleo NEXORA.
4. Mejoras visuales o analíticas posteriores que no cambien los invariantes contables certificados.

## Invariantes que no pueden relajarse para “cerrar” un pendiente

- `TOTAL DEBE = TOTAL HABER`.
- Un anticipo es prepayment/ASSET hasta su devengo; no se duplica como gasto.
- Un único evento económico no puede disminuir Treasury dos veces.
- Contrato y PO vinculada no se cuentan dos veces como commitment.
- Un documento POSTED se corrige mediante reversal/adjustment; no por mutación destructiva.
- Transfer/deposit/check exige evidencia de pago antes de emitir el voucher cuando así lo define la política del sistema.
- Company isolation, project scope, RBAC/SoD y auditoría se aplican en backend, no solamente ocultando UI.
- `effective_date` representa la fecha económica; `posted_at` la contabilización técnica.
- El sistema falla cerrado ante una configuración financiera ausente; no inventa cuentas, tasas ni datos.

## Gates de certificación del release

La existencia de backlog final `0` no basta por sí sola para llamar a un commit “100 % certificado”. El SHA final debe demostrar además:

- backend completo verde;
- frontend typecheck/lint/tests/build verde;
- E2E y accessibility verde;
- Docker Compose smoke verde;
- Alembic con un solo head y migraciones aplicables;
- Bicep compile/what-if verde;
- PR fusionado a `main`;
- deployment Azure del SHA final;
- Container App healthy y revisión correcta;
- Static Web App operativa;
- PostgreSQL/Blob/Key Vault/Application Insights accesibles según arquitectura;
- `/api/healthz` y `/api/readyz` verdes;
- smoke autenticado y recorrido crítico de producción verificados;
- ramas de cierre eliminadas solo después de comprobar que no contienen commits únicos fuera de `main`.

La evidencia exacta del release final debe quedar en la certificación de cierre correspondiente; no se reemplaza evidencia técnica con porcentajes declarativos.
