@description('Prefijo de nombres de recursos')
param namePrefix string

@description('Región de despliegue')
param location string

@minLength(6)
@description('Sufijo único para evitar colisión de nombre global de la storage account')
param uniqueSuffix string

@description('Nombre del contenedor de blobs para evidencias/documentos')
param evidenceContainerName string = 'evidence'

// Nombre de storage account: solo minúsculas/números, <= 24 caracteres.
var storageAccountName = toLower('${namePrefix}st${uniqueSuffix}')

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  // LRS + Standard: nivel de redundancia mínimo razonable para costo bajo.
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Cool'
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource evidenceContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: evidenceContainerName
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output evidenceContainerName string = evidenceContainer.name
