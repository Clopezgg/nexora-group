# Infraestructura Azure (Bicep)

Infraestructura como código de Nexora Group para el entorno Azure DEV actual.
`az bicep build` compila sin crear recursos y `az deployment sub what-if`
muestra el cambio propuesto antes del deploy.

## Arquitectura vigente

Recursos en `nexora-rg-dev`:

| Módulo | Recurso Azure | Tier / contrato |
|---|---|---|
| `modules/monitoring.bicep` | Log Analytics Workspace + Application Insights | PerGB2018, cap configurado |
| `modules/keyvault.bicep` | Key Vault (RBAC) | Standard |
| `modules/storage.bicep` | Storage Account + contenedor `evidence` | Standard_LRS |
| `modules/postgres.bicep` | PostgreSQL Flexible Server 16 | Burstable B1ms |
| `modules/containerapps.bicep` | Container Apps Environment + backend + identidad administrada | Consumption, backend con mínimo 1 réplica |
| `modules/staticwebapp.bicep` | Static Web App frontend | Standard |

`main.bicep` orquesta todo a nivel de suscripción y crea/actualiza el resource
group `nexora-rg-<environment>`.

### Frontend ↔ backend

La arquitectura productiva actual **no usa un linked backend de Static Web
Apps ni un proxy same-origin `/api`**. El workflow elimina cualquier vínculo
residual y compila el frontend con el endpoint HTTPS directo de Container Apps:

```text
VITE_API_BASE_URL=https://<container-app-fqdn>/api
```

FastAPI permite únicamente el origen exacto de Static Web Apps mediante CORS
con credenciales; el guard CSRF exige ese mismo `Origin`. Las cookies de sesión
productivas son `Secure`, `HttpOnly`, `SameSite=None`, `Path=/`.

## Decisiones de infraestructura

- **GHCR en vez de Azure Container Registry:** evita un recurso adicional con
  costo fijo. CI construye y publica `ghcr.io/<owner>/nexora-backend:<git-sha>`.
- **Identidad administrada asignada por el usuario:** permite al Container App
  resolver secretos de Key Vault sin secretos de cliente embebidos.
- **Sin VNet/Private Endpoint en DEV:** decisión de costo del entorno actual;
  no debe presentarse como aislamiento de red equivalente a producción
  endurecida.
- **Static Web App sin `repositoryUrl`:** el frontend se publica desde GitHub
  Actions usando el deployment token obtenido desde Azure después de OIDC.
- **Backend mínimo 1 réplica:** evita que el endpoint productivo quede detenido
  durante las comprobaciones de disponibilidad actuales.

## Validar sin desplegar

```bash
az bicep build --file main.bicep --stdout > /dev/null
for f in modules/*.bicep; do az bicep build --file "$f" --stdout > /dev/null; done

az deployment sub what-if \
  --name nexora-whatif \
  --location eastus2 \
  --template-file main.bicep \
  --parameters postgresAdminPassword='<valor-temporal>' \
               backendSecretKey='<valor-temporal>' \
               bootstrapAdminPassword='<valor-temporal>' \
               bootstrapAdminEmail='admin@nexora.group' \
               editAccessTokenSalt='<valor-temporal>' \
               editAccessTokenDigest='<valor-temporal>'
```

## Desplegar

La ruta oficial es `.github/workflows/deploy-azure.yml` con Azure OIDC. Requiere
los secretos de Azure/aplicación configurados en GitHub.

Un PR ejecuta `Bicep what-if` y validaciones pero **no modifica Azure**. El job
de deploy se ejecuta cuando:

- un `push` a `main` tiene `[deploy]` en el mensaje del commit de cabeza; o
- se usa `workflow_dispatch` con `deploy=true` y una razón explícita.

El workflow:

1. autentica contra Azure por OIDC;
2. construye/publica la imagen del backend con el SHA exacto;
3. ejecuta reparaciones pre-migración y `alembic upgrade head`;
4. despliega Bicep y verifica que Container Apps quede `Running`;
5. exige que la revisión más reciente sea la ready/healthy y use la imagen del SHA;
6. verifica la API HTTPS directa;
7. compila el frontend con el FQDN real del backend;
8. despliega Static Web Apps;
9. verifica frontend, health/readiness, CORS, login real, cookie de sesión,
   dashboard autenticado, HNL y Protected Edit.

No se debe certificar un despliegue únicamente porque Bicep haya terminado:
el gate `Verify production` debe quedar verde para el SHA que está en `main`.
