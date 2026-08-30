targetScope = 'subscription'

@description('Prefijo de nombres de recursos')
param namePrefix string = 'nexora'

@description('Nombre del entorno (dev | staging | prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environmentName string = 'dev'

@description('Región de despliegue. eastus2 tiene buena disponibilidad de Container Apps y Static Web Apps a bajo costo.')
param location string = 'eastus2'

@secure()
@description('Password del administrador de PostgreSQL Flexible Server. Requerido, sin valor por defecto: nunca se commitea.')
param postgresAdminPassword string

@secure()
@description('SECRET_KEY de la aplicación backend (se guarda en Key Vault). Requerido, sin valor por defecto.')
param backendSecretKey string

@secure()
@description('Password del admin de bootstrap de la aplicación. Vacío = no se crea el secreto ni el admin.')
param bootstrapAdminPassword string = ''

@description('Email del admin de bootstrap (no es secreto, pero se pasa junto al password por conveniencia).')
param bootstrapAdminEmail string = ''

@secure()
@description('Salt PBKDF2 de Protected Edit codificado base64url. Vacío mantiene Protected Edit fail-closed.')
param editAccessTokenSalt string = ''

@secure()
@description('Digest PBKDF2 de Protected Edit codificado base64url. Vacío mantiene Protected Edit fail-closed.')
param editAccessTokenDigest string = ''

@description('Imagen de contenedor del backend publicada por CI en GHCR. Placeholder hasta el primer build real.')
param backendImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Usuario administrador de PostgreSQL. No es secreto (el password sí lo es).')
param postgresAdminLogin string = 'nexoraadmin'

var resourceGroupName = '${namePrefix}-rg-${environmentName}'
var uniqueSuffix = uniqueString(subscription().subscriptionId, resourceGroupName)
var editAccessConfigured = !empty(editAccessTokenSalt) && !empty(editAccessTokenDigest)

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: 'nexora-group'
    environment: environmentName
    managedBy: 'bicep'
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    namePrefix: namePrefix
    environmentName: environmentName
    location: location
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  scope: rg
  params: {
    namePrefix: namePrefix
    location: location
    uniqueSuffix: uniqueSuffix
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  scope: rg
  params: {
    namePrefix: namePrefix
    environmentName: environmentName
    location: location
    uniqueSuffix: uniqueSuffix
    administratorLogin: postgresAdminLogin
    administratorPassword: postgresAdminPassword
  }
}

var databaseUrl = 'postgresql+psycopg://${postgresAdminLogin}:${postgresAdminPassword}@${postgres.outputs.fqdn}:5432/${postgres.outputs.databaseName}?sslmode=require'

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    namePrefix: namePrefix
    environmentName: environmentName
    location: location
    uniqueSuffix: uniqueSuffix
    databaseUrl: databaseUrl
    secretKey: backendSecretKey
    bootstrapAdminPassword: bootstrapAdminPassword
    editAccessTokenSalt: editAccessTokenSalt
    editAccessTokenDigest: editAccessTokenDigest
  }
}

module staticWebApp 'modules/staticwebapp.bicep' = {
  name: 'staticwebapp'
  scope: rg
  params: {
    namePrefix: namePrefix
    environmentName: environmentName
    location: location
  }
}

module containerApps 'modules/containerapps.bicep' = {
  name: 'containerapps'
  scope: rg
  params: {
    namePrefix: namePrefix
    environmentName: environmentName
    location: location
    logAnalyticsCustomerId: monitoring.outputs.logAnalyticsCustomerId
    logAnalyticsSharedKey: monitoring.outputs.logAnalyticsSharedKey
    keyVaultName: keyVault.outputs.keyVaultName
    keyVaultUri: keyVault.outputs.keyVaultUri
    storageAccountName: storage.outputs.storageAccountName
    backendImage: backendImage
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    frontendUrl: 'https://${staticWebApp.outputs.defaultHostname}'
    bootstrapAdminEmail: bootstrapAdminEmail
    editAccessConfigured: editAccessConfigured
  }
}

// The Static Web Apps -> Container Apps association is intentionally managed by
// `az staticwebapp backends link` in the deployment workflow. The GA command
// performs the complete linking/auth handshake for Container Apps, which a raw
// ARM child resource alone does not reliably establish.

output resourceGroupName string = rg.name
output backendFqdn string = containerApps.outputs.backendFqdn
output backendResourceId string = containerApps.outputs.backendResourceId
output frontendHostname string = staticWebApp.outputs.defaultHostname
output keyVaultUri string = keyVault.outputs.keyVaultUri
output storageAccountName string = storage.outputs.storageAccountName
output postgresServerFqdn string = postgres.outputs.fqdn
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output editAccessConfigured bool = editAccessConfigured
