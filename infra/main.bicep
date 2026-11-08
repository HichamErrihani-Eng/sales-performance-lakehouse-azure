// Infrastructure du projet Sales Performance Lakehouse (Azure)
// Déploiement : az deployment group create -g rg_sales_lakehouse -f infra/main.bicep -p infra/main.parameters.json

@description('Région Azure')
param location string = 'uksouth'

@description('Suffixe unique des noms de ressources')
param suffix string = 'hicham-sales'

@description('Identifiant (object id) Entra de l\'administrateur, qui reçoit le rôle Agent des secrets Key Vault')
param adminObjectId string

@description('Login administrateur SQL')
param sqlAdminLogin string = 'sqladmin'

@secure()
@description('Mot de passe administrateur SQL (stocké ensuite dans Key Vault)')
param sqlAdminPassword string

var storageName = toLower(replace('st${suffix}', '-', ''))
var containers = ['landing', 'bronze', 'silver', 'gold']

// Rôles intégrés Azure
var roleBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var roleKvSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'
var roleKvSecretsOfficer = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'

// ---------- Azure SQL (offre gratuite, Serverless, AdventureWorksLT) ----------
resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: 'sql-${suffix}'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource allowAzureServices 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = {
  parent: sqlServer
  name: 'AllowAllWindowsAzureIps'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: 'sqldb-adventureworks'
  location: location
  sku: { name: 'GP_S_Gen5_2', tier: 'GeneralPurpose', family: 'Gen5', capacity: 2 }
  properties: {
    sampleName: 'AdventureWorksLT'
    useFreeLimit: true
    freeLimitExhaustionBehavior: 'AutoPause'
    autoPauseDelay: 60
    minCapacity: json('0.5')
  }
}

// ---------- Data Lake Gen2 ----------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    isHnsEnabled: true
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource lakeContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for c in containers: {
  parent: blobService
  name: c
  properties: { publicAccess: 'None' }
}]

// ---------- Key Vault (mode RBAC) ----------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${suffix}'
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 7
  }
}

resource sqlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'sql-admin-password'
  properties: { value: sqlAdminPassword }
}

// ---------- Data Factory avec identité managée ----------
resource adf 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: 'adf-${suffix}'
  location: location
  identity: { type: 'SystemAssigned' }
}

// ---------- Droits (RBAC au plus juste) ----------
resource adfToLake 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, adf.id, roleBlobDataContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleBlobDataContributor)
    principalId: adf.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource adfToKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, adf.id, roleKvSecretsUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKvSecretsUser)
    principalId: adf.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource adminToKv 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, adminObjectId, roleKvSecretsOfficer)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKvSecretsOfficer)
    principalId: adminObjectId
    principalType: 'User'
  }
}

output storageAccount string = storage.name
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output dataFactory string = adf.name
output keyVaultUri string = keyVault.properties.vaultUri
