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
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    // Standard habilita el backend enlazado de Container Apps. El repositorio
    // no se liga aquí: el frontend se publica con el token obtenido por OIDC.
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

output staticWebAppName string = staticWebApp.name
output defaultHostname string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
