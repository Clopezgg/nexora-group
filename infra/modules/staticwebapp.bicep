@description('Prefijo de nombres de recursos')
param namePrefix string

@description('Sufijo de entorno')
param environmentName string

@description('Región de despliegue (Static Web Apps solo está disponible en un subconjunto de regiones)')
param location string

resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: '${namePrefix}-frontend-${environmentName}'
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    // Sin repositoryUrl/branch/buildProperties: no se liga el repo aquí para no
    // requerir un GitHub PAT en el template. El deploy real se hace vía el
    // Azure/static-web-apps-deploy-action en CI, usando el deployment token
    // (ver output deploymentTokenHint y el workflow de deploy).
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

output staticWebAppName string = staticWebApp.name
output defaultHostname string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
