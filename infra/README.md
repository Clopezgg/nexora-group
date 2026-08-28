# Infraestructura Azure (Bicep)


Recursos DEV observados en `nexora-rg-dev`: Azure Static Web Apps Standard,
Container Apps, Azure Database for PostgreSQL, Storage Account/Blob, Key
Vault, Log Analytics y Application Insights. Static Web Apps enlaza el
Container App como backend de mismo origen bajo `/api`; el ingreso directo del
Container App queda protegido por esa integración.

El run `33134425882` desplegó y verificó este entorno DEV. Esa evidencia no
certifica un entorno PROD ni autoriza despliegues posteriores.

Infraestructura como código para Nexora Group. `az bicep build` compila los
templates sin crear recursos y `az deployment sub what-if` muestra el cambio
propuesto. El workflow valida automáticamente; un despliegue real exige un
`workflow_dispatch` manual con `deploy=true` y una razón explícita.

## Recursos

| Módulo | Recurso Azure | Tier |
|---|---|---|
| `modules/monitoring.bicep` | Log Analytics Workspace + Application Insights | PerGB2018, cap 1GB/día |
| `modules/keyvault.bicep` | Key Vault (RBAC) | Standard |
| `modules/storage.bicep` | Storage Account + contenedor `evidence` | Standard_LRS, tier Cool |
| `modules/postgres.bicep` | PostgreSQL Flexible Server 16 | Burstable B1ms, 32GB |
| `modules/containerapps.bicep` | Container Apps Environment + Container App (backend) + identidad administrada | Consumption, mínimo 1 réplica |
| `modules/staticwebapp.bicep` | Static Web App (frontend) | Standard |

`main.bicep` orquesta todo a nivel de suscripción (crea el resource group
`nexora-rg-<environment>` y despliega los módulos dentro).

## Por qué estas decisiones

- **GHCR en vez de Azure Container Registry**: evita el costo fijo mensual de
  ACR. El backend usa una imagen placeholder pública
  (`mcr.microsoft.com/k8se/quickstart:latest`) hasta que CI construya y
  publique la imagen real en `ghcr.io/<owner>/nexora-backend`.
- **Identidad administrada asignada por el usuario** (no system-assigned) para
  el Container App: evita una dependencia circular entre el role assignment
  (que necesita el `principalId`) y el propio Container App (que necesita el
  role ya concedido para resolver los secretos de Key Vault al crearse).
- **Sin VNet/Private Endpoint** para Postgres ni Storage en esta fase: se
  prioriza costo y velocidad de bootstrap sobre aislamiento de red. Revisar
  en FINAL HARDENING (ver `docs/DEFERRED.md`).
- **Static Web App sin `repositoryUrl`**: no se liga el repo en el template
  para no requerir un GitHub PAT dentro del Bicep. El deploy real del
  frontend se hace vía `Azure/static-web-apps-deploy-action` en CI, usando el
  deployment token del recurso ya creado.

## Validar sin desplegar (costo cero)

```bash
# Compila cada archivo .bicep
az bicep build --file main.bicep --stdout > /dev/null
for f in modules/*.bicep; do az bicep build --file "$f" --stdout > /dev/null; done

# Simula el plan completo de despliegue sin crear ningún recurso
az deployment sub what-if \
  --name nexora-whatif \
  --location eastus2 \
  --template-file main.bicep \
  --parameters postgresAdminPassword='<valor-temporal>' \
               backendSecretKey='<valor-temporal>' \
               bootstrapAdminPassword='' \
               bootstrapAdminEmail='admin@nexora.group'
```

## Desplegar de verdad (crea o modifica recursos facturables)

Requiere decisión explícita del usuario — no se ejecuta automáticamente.

```bash
az login
az account set --subscription <subscription-id>

az deployment sub create \
  --name nexora-deploy \
  --location eastus2 \
  --template-file main.bicep \
  --parameters @main.parameters.example.json \
  --parameters postgresAdminPassword='<real, no commitear>' \
               backendSecretKey='<real, no commitear>' \
               bootstrapAdminPassword='<real, no commitear>'
```

`main.parameters.example.json` es una plantilla sin secretos reales — copiarla
a `main.parameters.json` (gitignored) y completar los valores localmente, o
pasar los secretos por línea de comandos/CI secrets como en el ejemplo.

Para el deploy vía CI, ver `.github/workflows/deploy-azure.yml`: requiere
configurar `AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID` (OIDC,
sin client secret) y los secrets de aplicación en GitHub. Solo un dispatch
manual con `deploy=true` ejecuta el job; los eventos `push` y `pull_request`
se limitan a validación.
