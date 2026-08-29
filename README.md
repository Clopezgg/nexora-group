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
   backend.

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
npm run typecheck && npm run lint && npm run test && npm run build
```

## Deploy

Plataforma oficial: **Microsoft Azure**. Render fue descartado como destino
de despliegue (ver `CLAUDE.md`).

- Frontend → Azure Static Web Apps (Free tier)
- Backend → Azure Container Apps (consumption plan, scale-to-zero)
- Base de datos → Azure Database for PostgreSQL Flexible Server (Burstable B1ms)
- Evidencias/documentos → Azure Blob Storage
- Secrets → Azure Key Vault
- Observabilidad → Azure Monitor + Application Insights + Log Analytics
- Infraestructura → Bicep (`infra/`), ver `infra/README.md` para el
  procedimiento completo de despliegue y el detalle de cada módulo.
- CI/CD → GitHub Actions con Azure OIDC/federated credentials
  (`.github/workflows/deploy-azure.yml`); requiere que el usuario configure
  los secrets del repo y apruebe el environment `production` antes de que
  el deploy real se ejecute.

Azure DEV está provisionado y disponible en
`https://jolly-plant-0d6bf700f.7.azurestaticapps.net/`, con API same-origin,
Container Apps, PostgreSQL, Blob Storage y Key Vault administrados por el
workflow `Deploy Azure`. Los secretos de Protected Edit se pasan como
parámetros seguros de Bicep y referencias de Key Vault; si no están
provisionados, el backend falla cerrado.
