@description('Prefijo de nombres de recursos')
param namePrefix string

@description('Sufijo de entorno')
param environmentName string

@description('Región de despliegue')
param location string

@description('Customer ID (workspace ID) de Log Analytics, requerido por el Container Apps Environment')
param logAnalyticsCustomerId string

@secure()
@description('Clave compartida del Log Analytics Workspace')
param logAnalyticsSharedKey string

@description('Nombre del Key Vault del que el backend lee secretos en runtime')
param keyVaultName string

@description('URI del Key Vault')
param keyVaultUri string

@description('Nombre de la storage account de evidencias')
param storageAccountName string

@description('Imagen de contenedor del backend. Placeholder público hasta que CI publique la imagen real en GHCR.')
param backendImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Connection string de Application Insights')
param appInsightsConnectionString string

@description('Puerto en el que escucha el backend (coincide con EXPOSE/CMD del Dockerfile)')
param targetPort int = 8000

@description('URL pública del frontend (Static Web App), para CORS/FRONTEND_URL')
param frontendUrl string = ''

@description('Email del admin de bootstrap (no es secreto)')
param bootstrapAdminEmail string = ''

@description('Indica si ambos secretos de Protected Edit fueron suministrados a la plantilla.')
param editAccessConfigured bool = false

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

var baseSecrets = [
  {
    name: 'database-url'
    keyVaultUrl: '${keyVaultUri}secrets/database-url'
    identity: backendIdentity.id
  }
  {
    name: 'secret-key'
    keyVaultUrl: '${keyVaultUri}secrets/secret-key'
    identity: backendIdentity.id
  }
  {
    name: 'bootstrap-admin-password'
    keyVaultUrl: '${keyVaultUri}secrets/bootstrap-admin-password'
    identity: backendIdentity.id
  }
]

var editAccessSecrets = editAccessConfigured ? [
  {
    name: 'edit-access-token-salt'
    keyVaultUrl: '${keyVaultUri}secrets/edit-access-token-salt'
    identity: backendIdentity.id
  }
  {
    name: 'edit-access-token-digest'
    keyVaultUrl: '${keyVaultUri}secrets/edit-access-token-digest'
    identity: backendIdentity.id
  }
] : []

var baseEnvironment = [
  { name: 'APP_ENV', value: 'production' }
  { name: 'APP_NAME', value: 'Nexora Group' }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'SECRET_KEY', secretRef: 'secret-key' }
  { name: 'BOOTSTRAP_ADMIN_PASSWORD', secretRef: 'bootstrap-admin-password' }
  { name: 'BOOTSTRAP_ADMIN_EMAIL', value: bootstrapAdminEmail }
  { name: 'FRONTEND_URL', value: frontendUrl }
  { name: 'EVIDENCE_BACKEND', value: 'azure_blob' }
  { name: 'AZURE_STORAGE_ACCOUNT_NAME', value: storageAccountName }
  { name: 'AZURE_KEY_VAULT_URI', value: keyVaultUri }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
]

var editAccessEnvironment = editAccessConfigured ? [
  { name: 'EDIT_ACCESS_TOKEN_SALT', secretRef: 'edit-access-token-salt' }
  { name: 'EDIT_ACCESS_TOKEN_DIGEST', secretRef: 'edit-access-token-digest' }
] : []

resource backendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-backend-id-${environmentName}'
  location: location
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae-${environmentName}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
  }
}

resource keyVaultExisting 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource storageAccountExisting 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultExisting.id, backendIdentity.id, keyVaultSecretsUserRoleId)
  scope: keyVaultExisting
  properties: {
    principalId: backendIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
  }
}

resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccountExisting.id, backendIdentity.id, storageBlobDataContributorRoleId)
  scope: storageAccountExisting
  properties: {
    principalId: backendIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-backend-${environmentName}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${backendIdentity.id}': {}
    }
  }
  dependsOn: [
    keyVaultRoleAssignment
  ]
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      secrets: concat(baseSecrets, editAccessSecrets)
      registries: []
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(baseEnvironment, editAccessEnvironment)
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

output backendFqdn string = backendApp.properties.configuration.ingress.fqdn
output backendResourceId string = backendApp.id
output backendPrincipalId string = backendIdentity.properties.principalId
output containerAppsEnvironmentId string = containerAppsEnvironment.id
