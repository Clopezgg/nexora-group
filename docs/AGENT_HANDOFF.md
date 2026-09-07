# NEXORA GROUP — Canonical Agent Handoff

**Repositorio:** `Clopezgg/nexora-group`  
**Rama de producción:** `main`  
**Fuente final de verdad:** el HEAD remoto actual de `main`, no ramas históricas ni documentos de recuperación.

## Regla principal

Antes de cualquier trabajo futuro:

1. `git fetch --all --prune`;
2. leer `origin/main` y su SHA;
3. revisar PRs abiertos y runs de GitHub Actions;
4. comprobar `docs/DEFERRED.md`, `docs/REQUIREMENTS_TRACEABILITY.md` y la certificación de release más reciente;
5. no revivir ramas antiguas salvo auditoría forense de commits que no estén integrados.

Nunca declarar NEXORA “100 %” solo porque compile o porque un check aislado esté verde. La certificación exige código, tests, infraestructura y producción coherentes para el mismo SHA.

## Arquitectura empresarial canónica

NEXORA es un ERP financiero y operativo multiempresa orientado a proyectos de construcción:

`GRUPO → EMPRESAS → PROYECTOS → WBS/PRESUPUESTO → CONTRATOS/COMPRAS → AP/AR → TREASURY → GL → REPORTES → DOCUMENTOS/EVIDENCE → AUDITORÍA`

Las capacidades no son aplicaciones paralelas: un evento económico debe tener una única representación canónica y trazable.

## Invariantes no negociables

- Doble partida: `SUM(debit) == SUM(credit)`.
- Un `AccountingDocument` POSTED no se edita destructivamente; se corrige mediante reversal/adjustment.
- Anticipo contractual = prepayment/ASSET hasta devengo; no gasto automático.
- Un pago disminuye Treasury una sola vez.
- Contrato de ejecución y PO vinculada no duplican commitment.
- `effective_date` = fecha económica; `posted_at` = fecha técnica de contabilización.
- Company isolation y `project_scope` se validan server-side.
- RBAC/SoD no depende de ocultar botones.
- Transfer/deposit/check exige Evidence cuando la política del voucher lo requiere.
- Numeración, pagos, asignaciones, inventario, rate limits y restricciones sensibles deben ser seguros ante concurrencia.
- El sistema falla cerrado ante configuración financiera ausente; nunca inventa cuentas, tipos de cambio o evidencia.

## Estado integrado previo al cierre de PR #112

El `main` base de PR #112 ya contiene el trabajo fusionado de PR #110 y PR #111, incluyendo las correcciones financieras finales, AP Aging, estados contractuales, precisión monetaria, `/api/version`, comprobantes y el cierre general anterior.

PR #112 (`fix/nexora-final-zero-deferred-20260906`) existe para cerrar los últimos gaps reales detectados durante la auditoría de ramas antes de borrarlas:

- identidad empresarial de vouchers mediante logo/firma en Evidence privado;
- snapshot inmutable de branding en `VoucherIssuance`;
- exportación nativa XLSX/PDF de reportes financieros/operativos;
- reconciliación del backlog diferido y documentación de cierre;
- correcciones de regresiones detectadas por CI.

No borrar la rama del PR hasta que esté fusionada y se haya confirmado que el commit final está en `main`.

## Lógica financiera final

### Anticipos

Un anticipo contractual mueve efectivo a una cuenta de anticipo/prepayment. No reconoce gasto por sí mismo. Debe conservar la relación con contrato, plan y asignaciones; el reversal restaura Treasury, GL y estado contractual sin destruir historia.

### Contratos y planes

Para valor contractual `V` y anticipo `A`:

- `regular_base = V - A`;
- la suma de cuotas regulares debe ser exactamente `regular_base`;
- anticipo + cuotas = valor contractual;
- la última cuota absorbe residuo de redondeo;
- MONTHLY/CUSTOM falla cerrado si se intenta pagar sin plan/asignaciones, salvo override autorizado y auditado.

### Commitments

`executionContractValue` y `poCommitted` son conceptos distintos. Una PO enlazada a un contrato consume/dibuja del compromiso contractual y no debe duplicarlo en el total de exposición.

### Presupuesto

El presupuesto autorizado, compromiso, devengado, pagado, costo GL, anticipos y disponible son métricas diferentes. Si no hay BASELINE, la UI debe decir “Sin configurar” y mostrar exposición sin presupuesto; no fabricar un disponible negativo.

### Treasury

Treasury representa efectivo real. Las restricciones de fondos etiquetan disponibilidad pero no transfieren propiedad del dinero a un proyecto. Las transferencias internas soportadas en el release son same-currency; cross-currency se rechaza hasta que exista una política FX empresarial autoritativa.

## Evidencia y documentos

Evidence es privado y company/project-scoped. Los blobs no se consideran existentes si el storage real no está configurado. Los vouchers congelan identidad relevante en la primera emisión y las reimpresiones conservan ese snapshot histórico.

## Release gates obligatorios

Para fusionar un cierre futuro a `main` deben pasar, cuando apliquen:

- backend compile/Ruff/dependency audit/pytest;
- Alembic fresh upgrade con un solo head;
- frontend typecheck/lint/tests/build;
- Docker Compose smoke;
- Playwright critical journey + accessibility E2E;
- Bicep compile y Azure what-if;
- required checks de GitHub Actions verdes.

Después del merge:

- desplegar el SHA final mediante el workflow oficial de Azure;
- comprobar imagen del backend con SHA exacto;
- Container App `Running/Healthy` y latest ready revision;
- Static Web App + same-origin API;
- PostgreSQL/migrations;
- Blob Storage, Key Vault, Application Insights según Bicep;
- `/api/healthz` y `/api/readyz`;
- login/cookie/authenticated smoke;
- Critical Journey de producción sobre dataset QA seguro.

## Limpieza de ramas

Una rama solo puede eliminarse cuando una comparación contra `main` demuestre que no contiene commits únicos necesarios. Esta regla es importante: una auditoría de cierre ya encontró trabajo válido olvidado en una rama que inicialmente parecía residual.

## Documentación

`docs/DEFERRED.md` contiene únicamente deuda final vigente y decisiones Future/Optional. No usar archivos `.recovery-*` ni handoffs antiguos como verdad operacional. El historial sigue disponible en Git.

Al completar un release, registrar SHA de `main`, PR, runs de CI/Deploy y URL productiva en una certificación de release; no sustituir esos identificadores con frases como “todo debería funcionar”.
