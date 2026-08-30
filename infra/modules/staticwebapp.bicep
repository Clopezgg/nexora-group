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
    // El repositorio no se liga aquí: el frontend se publica con el token
    // obtenido por OIDC. La aplicación productiva consume el HTTPS directo
    // de Container Apps; el workflow elimina cualquier linked backend
    // residual para evitar un proxy /api ambiguo.
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
  }
}

output staticWebAppName string = staticWebApp.name
output defaultHostname string = staticWebApp.properties.defaultHostname
output staticWebAppId string = staticWebApp.id
