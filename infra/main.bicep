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

@description('Imagen de contenedor del backend. CI siempre sobrescribe este valor con ghcr.io/<owner>/nexora-backend:<git-sha> en despliegues reales.')
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

// No se declara ni se conserva una asociación Static Web Apps -> Container Apps.
// El navegador usa el FQDN HTTPS directo del backend, compilado en el frontend.
// El workflow de despliegue elimina cualquier linked backend residual antes de
// publicar Static Web Apps para que /api nunca vuelva a ser una ruta ambigua.

output resourceGroupName string = rg.name
output backendFqdn string = containerApps.outputs.backendFqdn
output backendResourceId string = containerApps.outputs.backendResourceId
output frontendHostname string = staticWebApp.outputs.defaultHostname
output keyVaultUri string = keyVault.outputs.keyVaultUri
output storageAccountName string = storage.outputs.storageAccountName
output postgresServerFqdn string = postgres.outputs.fqdn
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output editAccessConfigured bool = editAccessConfigured
