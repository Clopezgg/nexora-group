# Nexora Group

Plataforma administrativa greenfield de Nexora Group: tesorería, proyectos y
operaciones. Ver `CLAUDE.md` para las reglas permanentes del proyecto y
`docs/ROADMAP.md` para el estado por fases.

Stack: React + TypeScript + Vite (frontend) y FastAPI + PostgreSQL (backend).
Sin Frappe, sin ERPNext, sin código heredado.

## Estructura

```
frontend/   React + Vite + TS
backend/    FastAPI + SQLAlchemy + Alembic
docs/       Documentación y roadmap
scripts/    Scripts de desarrollo local
```

## Requisitos

- Node.js 22+
- Python 3.12+
- PostgreSQL 16 (local, vía Homebrew, o Docker)

## Desarrollo local

1. Copia `.env.example` a `backend/.env` y completa los valores (al menos
   `DATABASE_URL`; opcionalmente `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD`
   para crear el primer usuario Administrator).
2. Backend:

   ```bash
   ./scripts/dev-backend.sh
   ```

   Crea el virtualenv si no existe, instala dependencias, aplica las
   migraciones de Alembic y levanta `uvicorn` en `http://localhost:8000`.

3. Frontend (en otra terminal):

   ```bash
   ./scripts/dev-frontend.sh
   ```

   Levanta Vite en `http://localhost:5173`, con proxy de `/api` hacia el
   backend exclusivamente para desarrollo local.

### Con Docker

```bash
docker compose up
```

Levanta PostgreSQL y el backend (aplica migraciones automáticamente al
arrancar). El frontend se sigue ejecutando con Vite localmente.

## Verificación

Backend:

```bash
cd backend && source .venv/bin/activate
pytest -q
```

Frontend:

```bash
cd frontend
npm run typecheck && npm run lint && npm run test
VITE_API_BASE_URL=https://ci.invalid/api npm run build
```

El build de producción **falla cerrado** si `VITE_API_BASE_URL` no es
first-party: acepta un path same-origin (`/api`, el valor real de producción)
o una URL HTTPS absoluta; rechaza cualquier URL en texto claro.

## Deploy

Plataforma oficial: **Microsoft Azure**. Render fue descartado como destino
de despliegue (ver `CLAUDE.md`).

- Frontend → Azure Static Web Apps (Free tier)
- Backend → Azure Container Apps (consumption plan, `minReplicas=1` para el backend productivo actual)
- Base de datos → Azure Database for PostgreSQL Flexible Server (Burstable B1ms)
- Evidencias/documentos → Azure Blob Storage
- Secrets → Azure Key Vault
- Observabilidad → Azure Monitor + Application Insights + Log Analytics
- Infraestructura → Bicep (`infra/`), ver `infra/README.md` para el procedimiento completo
- CI/CD → GitHub Actions con Azure OIDC/federated credentials (`.github/workflows/deploy-azure.yml`)

### Contrato de red de producción

El frontend llama a la API en su **mismo origen**: `/api/*` sobre el dominio de
Azure Static Web Apps. El workflow liga el Container App como *linked backend*
de Static Web Apps (`az staticwebapp backends link`), que actúa de reverse
proxy hacia el HTTPS del Container App y reescribe `Set-Cookie` al dominio
first-party. Durante el deploy el frontend se compila con:

```text
VITE_API_BASE_URL=/api
```

**Por qué first-party y no el FQDN directo de Container Apps:** el frontend
(`*.azurestaticapps.net`) y el Container App (`*.azurecontainerapps.io`) están
en dominios registrables distintos. Una cookie de sesión cross-site
(`SameSite=None`) es descartada silenciosamente por Safari/WebKit (ITP): el
login parece exitoso pero toda llamada autenticada posterior devuelve 401 y
media aplicación muestra "Ocurrió un error". Con el linked backend la cookie es
first-party y funciona en todos los navegadores.

Ligar el backend también **habilita autenticación en el Container App**: el
FQDN público `*.azurecontainerapps.io` deja de responder tráfico anónimo
(devuelve 401) y solo es alcanzable a través del proxy first-party de Static
Web Apps. El gate de despliegue lo verifica (`Verify direct Container Apps API
is locked down`). El HTML de Static Web Apps se entrega `no-store` y el service
worker no precachea HTML/JS/CSS del shell transaccional.

**Verificación de producción (gate `Verify production`):** hace login real y
ejercita `auth/me`, `master-data/companies` (exige ≥1 visible al
Administrator), `projects`, `master-data/accounts`, `dashboard` (contrato
`currency == "HNL"`), `fiscal/periods/current` y `logout`+`relogin` — todo a
través del origen first-party `$FRONTEND_URL/api`, no con `curl` al FQDN del
Container App.

### Autorización del despliegue

Un `push` a `main` solo ejecuta el job que modifica Azure cuando el mensaje del
commit de cabeza contiene `[deploy]`. También existe `workflow_dispatch` con
la confirmación `deploy=true`. Los PR ejecutan Bicep what-if y las validaciones,
pero no modifican Azure.

El gate productivo comprueba, entre otros puntos: migraciones Alembic, imagen
correspondiente al SHA, Container App `Running`, revisión `Healthy`, health y
readiness HTTP, frontend desplegado, CORS exact-origin, login real, atributos de
la cookie de sesión, dashboard autenticado, contrato HNL y Protected Edit.

Azure DEV está provisionado en
`https://jolly-plant-0d6bf700f.7.azurestaticapps.net/`. El backend se publica a
través del FQDN HTTPS de `nexora-backend-dev` y ese endpoint se inyecta en el
build del frontend; no debe sustituirse por `/api` en producción.
