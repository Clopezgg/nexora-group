@description('Prefijo de nombres de recursos')
param namePrefix string

@description('Sufijo de entorno')
param environmentName string

@description('Región de despliegue')
param location string

@description('Sufijo único para evitar colisión de nombre global del servidor')
param uniqueSuffix string

@description('Usuario administrador de PostgreSQL')
param administratorLogin string = 'nexoraadmin'

@secure()
@description('Password del administrador de PostgreSQL')
param administratorPassword string

@description('Nombre de la base de datos de aplicación')
param databaseName string = 'nexora'

var serverName = '${namePrefix}-pg-${environmentName}-${uniqueSuffix}'

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: serverName
  location: location
  sku: {
    // Burstable B1ms: el tier más barato con memoria decente para una app pequeña.
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      // Sin VNet integration en esta fase para minimizar costo/complejidad.
      // Acceso público restringido por firewall rules explícitas.
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Permite que otros servicios de Azure (Container Apps sin VNet integration) alcancen el servidor.
// Reemplazar por Private Endpoint / VNet integration en FINAL HARDENING.
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

output serverName string = postgresServer.name
output fqdn string = postgresServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
