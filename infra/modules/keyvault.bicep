@description('Prefijo de nombres de recursos')
param namePrefix string

@description('Sufijo de entorno')
param environmentName string

@description('Región de despliegue')
param location string

@description('Sufijo único para evitar colisión de nombre global de Key Vault')
param uniqueSuffix string

@secure()
@description('Cadena de conexión completa a PostgreSQL (postgresql+psycopg://...)')
param databaseUrl string = ''

@secure()
@description('SECRET_KEY de la aplicación backend')
param secretKey string = ''

@secure()
@description('Password del admin de bootstrap (vacío = no se crea el secreto)')
param bootstrapAdminPassword string = ''

@secure()
@description('Salt PBKDF2 de Protected Edit en base64url. Vacío = secreto no creado.')
param editAccessTokenSalt string = ''

@secure()
@description('Digest PBKDF2 de Protected Edit en base64url. Vacío = secreto no creado.')
param editAccessTokenDigest string = ''

var keyVaultName = '${namePrefix}-kv-${uniqueSuffix}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
  tags: {
    environment: environmentName
    project: 'nexora-group'
  }
}

resource secretDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(databaseUrl)) {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: databaseUrl
  }
}

resource secretAppSecretKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(secretKey)) {
  parent: keyVault
  name: 'secret-key'
  properties: {
    value: secretKey
  }
}

resource secretBootstrapAdminPassword 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(bootstrapAdminPassword)) {
  parent: keyVault
  name: 'bootstrap-admin-password'
  properties: {
    value: bootstrapAdminPassword
  }
}

resource secretEditAccessTokenSalt 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(editAccessTokenSalt)) {
  parent: keyVault
  name: 'edit-access-token-salt'
  properties: {
    value: editAccessTokenSalt
  }
}

resource secretEditAccessTokenDigest 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(editAccessTokenDigest)) {
  parent: keyVault
  name: 'edit-access-token-digest'
  properties: {
    value: editAccessTokenDigest
  }
}

output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultId string = keyVault.id
