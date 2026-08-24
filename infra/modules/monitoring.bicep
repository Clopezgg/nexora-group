@description('Prefijo de nombres de recursos, p.ej. nexora')
param namePrefix string

@description('Sufijo de entorno, p.ej. dev')
param environmentName string

@description('Región de despliegue')
param location string

@description('Días de retención de logs (mínimo razonable para costo bajo)')
param retentionInDays int = 30

@description('Cap diario de ingestión de Log Analytics en GB, para controlar costo (-1 = sin cap)')
param dailyQuotaGb int = 1

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-log-${environmentName}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    workspaceCapping: {
      dailyQuotaGb: dailyQuotaGb
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-appi-${environmentName}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    // Sampling fijo para mantener el volumen de telemetría bajo y el costo controlado.
    SamplingPercentage: 20
  }
}

output logAnalyticsWorkspaceId string = logAnalytics.id
output logAnalyticsCustomerId string = logAnalytics.properties.customerId
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey

@secure()
// listKeys() debe resolverse aquí, dentro del mismo scope de resource group que
// el workspace: llamarlo desde main.bicep (scope suscripción) sobre un output
// de string falla porque ARM no puede calcularlo al inicio del deployment.
output logAnalyticsSharedKey string = logAnalytics.listKeys().primarySharedKey
