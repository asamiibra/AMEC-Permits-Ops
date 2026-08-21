targetScope = 'subscription'

@description('Azure region for the ProposalOps preproduction foundation.')
param location string = 'qatarcentral'

@description('Deployment environment name used in deterministic resource naming.')
param environment string = 'preprod'

@description('Resource group created by the subscription-scope foundation.')
param resourceGroupName string = 'rg-proposalops-preprod-qc'

@description('Enable the App Service sites only when the later application deployment boundary is authorized.')
param deployApps bool = false

@description('Enable PostgreSQL Flexible Server only after Qatar Central access is authorized.')
param deployPostgres bool = false

@description('App Service plan SKU name.')
param appServiceSkuName string = 'B1'

@description('App Service plan SKU tier.')
param appServiceSkuTier string = 'Basic'

@description('Canonical PostgreSQL major version target.')
param postgresMajorVersion string = '16'

@description('Explicit PostgreSQL backup retention target in days.')
param postgresBackupRetentionDays int = 7

@description('Future frontend immutable image reference. No image is deployed by the default parameter set.')
param frontendImage string = 'proposalops/frontend:pending'

@description('Future backend immutable image reference. No image is deployed by the default parameter set.')
param backendImage string = 'proposalops/backend:pending'

@description('Future Entra tenant identifier. The default is synthetic and is not a live registration.')
param entraTenantId string = '11111111-1111-4111-8111-111111111111'

@description('Future Entra web client identifier. The default is synthetic and is not a live registration.')
param entraWebClientId string = '22222222-2222-4222-8222-222222222222'

@description('Future Entra API client identifier. The default is synthetic and is not a live registration.')
param entraApiClientId string = '33333333-3333-4333-8333-333333333333'

@description('Tenant used by Key Vault RBAC configuration when the foundation is later deployed.')
param tenantId string = '00000000-0000-4000-8000-000000000001'

@description('PostgreSQL administrator login for a future explicitly authorized deployment.')
param postgresAdminLogin string = 'proposalopsadmin'

@secure()
@description('No committed password is supplied. A future deployment must provide this value explicitly.')
param postgresAdminPassword string = ''

var nameSuffix = uniqueString(subscription().id, environment)
var resourcePrefix = 'proposalops-${environment}-${nameSuffix}'
var acrName = take(toLower(replace('proposalops${nameSuffix}', '-', '')), 50)
var keyVaultName = take(replace('kv-${resourcePrefix}', '-', ''), 24)
var logAnalyticsName = 'law-${resourcePrefix}'
var appInsightsName = 'appi-${resourcePrefix}'
var planName = 'asp-${resourcePrefix}'
var vnetName = 'vnet-${resourcePrefix}'
var frontendAppName = 'web-${resourcePrefix}'
var backendAppName = 'api-${resourcePrefix}'
var postgresServerName = 'pg-${resourcePrefix}'
var privateDnsZoneName = '${postgresServerName}.postgres.database.azure.com'
var resourceTags = {
  application: 'ProposalOps'
  environment: 'preprod'
  dataMode: 'synthetic-only'
  regionIntent: 'qatarcentral'
  managedBy: 'bicep'
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: resourceTags
}

module network './modules/network.bicep' = {
  name: 'network-${nameSuffix}'
  scope: resourceGroup
  params: {
    location: location
    vnetName: vnetName
    tags: resourceTags
  }
}

module foundation './modules/foundation.bicep' = {
  name: 'foundation-${nameSuffix}'
  scope: resourceGroup
  params: {
    location: location
    acrName: acrName
    keyVaultName: keyVaultName
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
    planName: planName
    appServiceSkuName: appServiceSkuName
    appServiceSkuTier: appServiceSkuTier
    tenantId: tenantId
    tags: resourceTags
  }
}

module appservice './modules/appservice.bicep' = if (deployApps) {
  name: 'appservice-${nameSuffix}'
  scope: resourceGroup
  params: {
    location: location
    planId: foundation.outputs.planId
    acrName: acrName
    appSubnetId: network.outputs.appSubnetId
    frontendAppName: frontendAppName
    backendAppName: backendAppName
    frontendImage: frontendImage
    backendImage: backendImage
    frontendOrigin: 'https://${frontendAppName}.azurewebsites.net'
    entraTenantId: entraTenantId
    entraWebClientId: entraWebClientId
    entraApiClientId: entraApiClientId
    logAnalyticsId: foundation.outputs.logAnalyticsId
    tags: resourceTags
  }
}

module postgres './modules/postgres.bicep' = if (deployPostgres) {
  name: 'postgres-${nameSuffix}'
  scope: resourceGroup
  params: {
    location: location
    serverName: postgresServerName
    postgresMajorVersion: postgresMajorVersion
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    backupRetentionDays: postgresBackupRetentionDays
    postgresSubnetId: network.outputs.postgresSubnetId
    vnetId: network.outputs.vnetId
    privateDnsZoneName: privateDnsZoneName
    tags: resourceTags
  }
}

output plannedResourceGroupName string = resourceGroup.name
output plannedResourceGroupId string = resourceGroup.id
output plannedLocation string = location
output plannedEnvironment string = environment
output plannedAcrName string = acrName
output plannedKeyVaultName string = keyVaultName
output plannedLogAnalyticsName string = logAnalyticsName
output plannedAppInsightsName string = appInsightsName
output plannedAppServicePlanName string = planName
output plannedPostgresServerName string = postgresServerName
output deployAppsByDefault bool = deployApps
output deployPostgresByDefault bool = deployPostgres
