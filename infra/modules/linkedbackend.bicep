@description('Nombre del recurso Azure Static Web Apps')
param staticWebAppName string

@description('Resource ID del Container App que atiende /api')
param backendResourceId string

@description('Región del Container App enlazado')
param backendRegion string

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' existing = {
  name: staticWebAppName
}

resource linkedBackend 'Microsoft.Web/staticSites/linkedBackends@2023-12-01' = {
  parent: staticWebApp
  name: 'nexora-api'
  properties: {
    backendResourceId: backendResourceId
    region: backendRegion
  }
}

output linkedBackendId string = linkedBackend.id
