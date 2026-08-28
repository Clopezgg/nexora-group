# Main Production Hardening Design

## Contexto y fuente de verdad

La fuente de verdad es `origin/main`. El baseline auditado es
`cd77d700c4433b48653e11f41ef791da13bea56b`. El commit
`a8d80c340e4dd29efaea619a080efb61ab35cbaa` está integrado y es ancestro de
ese HEAD. El Azure existente usa `environmentName=dev`, recursos `*-dev` y
resource group `nexora-rg-dev`; se clasifica como DEV, no como PROD
certificado.

## Alternativas consideradas

1. **Slices de riesgo con contratos compatibles (elegida).** Primero se
   elimina el despliegue automático, luego se cierran defectos reproducibles,
   audit/security/scale y finalmente se reconcilia documentación. Mantiene el
   producto utilizable y deja evidencia por commit.
2. **Reescritura transversal.** Cambiar simultáneamente todas las respuestas
   de listas, transacciones y pipelines. Podría uniformar más rápido, pero
   rompería numerosos consumidores y haría difícil aislar regresiones.
3. **Solo documentación y CI.** Es la opción de menor riesgo inmediato, pero
   dejaría gaps reales: proveedores sin audit, uploads que cargan todo en
   memoria y tests dependientes del entorno.

## Arquitectura del cambio

### 1. Control de despliegue

Los pushes y pull requests continuarán ejecutando validación Bicep/what-if,
pero el job que construye la imagen y ejecuta `az deployment ... create` solo
podrá iniciarse mediante `workflow_dispatch` con confirmación explícita. Un
push a `main` nunca debe desplegar por sí solo. El workflow conservará
concurrency, OIDC y smoke test para una ejecución manual autorizada.

### 2. Gates reproducibles

El test de backup/restore usará el mismo intérprete que ejecuta pytest
(`sys.executable`). El almacenamiento de compañía activa tolerará que
`localStorage` no exista o arroje una excepción. CI añadirá compilación Python,
un gate Ruff de errores objetivos, `pip-audit`, `npm audit` y compilación
Bicep. Los gates actuales de PostgreSQL, frontend y Playwright se conservan.

### 3. Audit íntegro y escalable

Las altas de proveedor y contrato se ejecutarán como una sola transacción
business+audit. Un fallo del audit revertirá el registro de negocio. Los
snapshots excluirán datos bancarios. El feed de audit aceptará `offset` y
`limit` acotados sin cambiar la forma de respuesta existente, manteniendo
compatibilidad con el frontend. Se añadirá un índice compuesto por compañía y
orden temporal para el patrón de consulta real.

### 4. Seguridad de evidencias

El endpoint leerá el upload por bloques y rechazará al superar el límite sin
cargar el archivo completo en memoria. El nombre persistido se normalizará a
un basename seguro; el contenido deberá corresponder al tipo permitido. Si
falla la persistencia o el audit después de subir el blob, se intentará borrar
el blob como compensación. Listados de evidencia incorporarán límites
compatibles.

### 5. CI/CD e infraestructura

Container Apps declarará probes de startup, liveness y readiness. La imagen no
se presentará como reproducible mientras las dependencias y la base no estén
fijadas de forma verificable. El despliegue continuará aplicando migraciones
como hoy durante esta pasada; separar migraciones en un job único requiere un
runbook y una estrategia Azure adicional y no se certificará sin una prueba
real autorizada.

### 6. Documentación y trazabilidad

`README`, `MASTER_PLAN`, `REQUIREMENTS_TRACEABILITY`, `PRODUCTION_READINESS`,
`DEFERRED`, `AUDIT`, `AGENT_HANDOFF`, `PROGRESS`, `RBAC`, integración e
infraestructura se reconciliarán contra Git y GitHub. Se distinguirán:

- evidencia local ejecutada;
- evidencia CI del SHA exacto;
- evidencia DEV Azure;
- capacidades implementadas pero no verificadas en PROD;
- bloqueos que necesitan política de negocio o autorización Azure.

No se marcará PROD, 100%, Azure production E2E ni restore/PITR Azure como
verificado sin evidencia real.

## Flujo de errores y transacciones

- Toda mutación auditada hace `flush -> audit flush -> commit` una vez.
- Cualquier excepción antes del commit hace rollback.
- Blob Storage usa compensación explícita porque PostgreSQL no puede incluir
  un blob remoto en su transacción.
- Paginación rechaza límites fuera de `1..100` con 422 de FastAPI.
- Las nuevas defensas mantienen los códigos `NXR-*` existentes.

## Estrategia de pruebas

- RED/GREEN dirigido para cada defecto de portabilidad.
- Tests API reales sobre PostgreSQL para supplier audit, rollback y
  paginación.
- Dobles de Azure únicamente en el límite remoto, verificando efectos del
  servicio real y la compensación.
- Suite backend completa, Vitest Node 22 y Node 26, typecheck, lint, build,
  Playwright, auditorías de dependencias, compileall, Ruff objetivo, Bicep y
  `git diff --check`.
- Tras cada commit: `git fetch`, confirmar fast-forward respecto a
  `origin/main` y push sin fuerza.
