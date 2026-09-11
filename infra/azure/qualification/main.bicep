targetScope = 'resourceGroup'

@description('Unique execution identifier for this isolated G6 qualification.')
param qualificationId string

@description('Exact post-fix release SHA used to build the qualification image.')
param releaseSha string

@description('Qualification deployment region. This is not the production topology.')
param location string = 'uaenorth'

@description('Exact digest for the runtime qualification image, without a tag.')
param runtimeImageDigest string

@description('Exact digest for the migration qualification image, without a tag.')
param migrationImageDigest string

@description('Repository path containing the immutable qualification images.')
param imageRepository string = 'proposalops/g6-qualification'

@description('Entra tenant used by the application configuration and SQL token checks.')
param tenantId string

@description('Application Entra client ID used only for configuration validation.')
param entraApiClientId string

@description('Web Entra client ID used only for configuration validation.')
param entraWebClientId string

@description('Approved qualification-only Entra administrator object ID for SQL bootstrap.')
param sqlAdministratorObjectId string

@description('Display name of the approved qualification-only SQL Entra administrator.')
param sqlAdministratorLogin string

@description('SQL login required by the control-plane API; must differ from the Entra administrator.')
param sqlServerAdministratorLogin string = 'proposalops_g6_sqladmin'

@secure()
@description('Required by the Azure SQL control-plane API; application URLs remain credentialless.')
param sqlAdministratorPassword string

var shortId = take(uniqueString(resourceGroup().id, qualificationId), 12)
var tags = {
  application: 'ProposalOps'
  environment: 'qualification'
  purpose: 'G6_QUALIFICATION_ONLY'
  production: 'false'
  realDataAllowed: 'false'
  qualificationId: qualificationId
  releaseSha: releaseSha
  managedBy: 'bicep'
}
var vnetName = 'g6-vnet-${shortId}'
var acaEnvironmentName = 'g6-cae-${shortId}'
var logAnalyticsName = 'g6-law-${shortId}'
var acrName = 'g6acr${shortId}'
var sqlServerName = 'g6sql-${shortId}'
var sqlDatabaseName = 'g6-qualification'
var runtimeIdentityName = 'g6-runtime-${shortId}'
var migrationIdentityName = 'g6-migration-${shortId}'
var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var sqlPrivateDnsZoneName = 'privatelink.database.windows.net'
var imageRuntime = '${acr.properties.loginServer}/${imageRepository}@${runtimeImageDigest}'
var imageMigration = '${acr.properties.loginServer}/${imageRepository}@${migrationImageDigest}'
var credentiallessDatabaseUrl = 'mssql+pyodbc://@${sqlServer.properties.fullyQualifiedDomainName}/${sqlDatabaseName}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'
var commonEnvironment = [
  { name: 'APP_ENV', value: 'AZURE-PREPROD' }
  { name: 'AUTH_MODE', value: 'ENTRA' }
  { name: 'ENTRA_TENANT_ID', value: tenantId }
  { name: 'ENTRA_API_CLIENT_ID', value: entraApiClientId }
  { name: 'ENTRA_WEB_CLIENT_ID', value: entraWebClientId }
  { name: 'ENTRA_REQUIRED_SCOPE', value: 'access_as_user' }
  { name: 'SYNTHETIC_ONLY', value: 'true' }
  { name: 'REAL_DATA_ALLOWED', value: 'false' }
  { name: 'AZURE_SQL_AUTH_MODE', value: 'MANAGED_IDENTITY_ACCESS_TOKEN' }
  { name: 'DATABASE_URL', value: credentiallessDatabaseUrl }
  { name: 'DATABASE_MIGRATION_URL', value: credentiallessDatabaseUrl }
  { name: 'QUALIFICATION_ID', value: qualificationId }
  { name: 'RELEASE_SHA', value: releaseSha }
  { name: 'G6_QUALIFICATION_ONLY', value: 'true' }
]

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Standard' }
  tags: tags
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    // Temporary qualification uses the authenticated public endpoint. ACR
    // credentials are never placed in the job definition.
    publicNetworkAccess: 'Enabled'
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.60.0.0/16'] }
    subnets: [
      {
        name: 'aca-infrastructure'
        properties: {
          addressPrefix: '10.60.0.0/23'
          delegations: [{ name: 'aca', properties: { serviceName: 'Microsoft.App/environments' } }]
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: '10.60.2.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

resource sqlPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: sqlPrivateDnsZoneName
  location: 'global'
  tags: tags
}

resource sqlPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  name: 'g6-vnet-link'
  parent: sqlPrivateDnsZone
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: runtimeIdentityName
  location: location
  tags: tags
}

resource migrationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: migrationIdentityName
  location: location
  tags: tags
}

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: sqlServerName
  location: location
  tags: tags
  properties: {
    administratorLogin: sqlServerAdministratorLogin
    administratorLoginPassword: sqlAdministratorPassword
    publicNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
    restrictOutboundNetworkAccess: 'Enabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
      login: sqlAdministratorLogin
      principalType: 'User'
      sid: sqlAdministratorObjectId
      tenantId: tenantId
    }
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  name: sqlDatabaseName
  parent: sqlServer
  location: location
  sku: { name: 'Basic', tier: 'Basic' }
  tags: tags
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    requestedBackupStorageRedundancy: 'Local'
    isLedgerOn: false
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: acaEnvironmentName
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: resourceId(resourceGroup().name, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'aca-infrastructure')
      internal: true
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource runtimeJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'g6-runtime-${shortId}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${runtimeIdentity.id}': {} }
  }
  tags: tags
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 0
      registries: [{ server: acr.properties.loginServer, identity: runtimeIdentity.id }]
    }
    template: {
      containers: [{
        name: 'runtime'
        image: imageRuntime
        command: ['python', '-m', 'backend.app.g6_qualification_runtime']
        env: concat(commonEnvironment, [
          { name: 'AZURE_SQL_UAMI_CLIENT_ID', value: runtimeIdentity.properties.clientId }
          { name: 'AZURE_SQL_UAMI_PRINCIPAL_ID', value: runtimeIdentity.properties.principalId }
        ])
        resources: { cpu: 1, memory: '2Gi' }
      }]
    }
  }
}

resource migrationJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'g6-migration-${shortId}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${migrationIdentity.id}': {} }
  }
  tags: tags
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 0
      registries: [{ server: acr.properties.loginServer, identity: migrationIdentity.id }]
    }
    template: {
      containers: [{
        name: 'migration'
        image: imageMigration
        command: ['python', '-m', 'backend.app.migrate']
        env: concat(commonEnvironment, [
          { name: 'AZURE_SQL_UAMI_CLIENT_ID', value: migrationIdentity.properties.clientId }
          { name: 'AZURE_SQL_UAMI_PRINCIPAL_ID', value: migrationIdentity.properties.principalId }
        ])
        resources: { cpu: 1, memory: '2Gi' }
      }]
    }
  }
}

resource sqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'g6-pe-${shortId}'
  location: location
  tags: tags
  properties: {
    subnet: { id: resourceId(resourceGroup().name, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'private-endpoints') }
    privateLinkServiceConnections: [{
      name: 'sql'
      properties: {
        privateLinkServiceId: sqlServer.id
        groupIds: ['sqlServer']
      }
    }]
  }
}

resource sqlPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  name: 'default'
  parent: sqlPrivateEndpoint
  properties: {
    privateDnsZoneConfigs: [{
      name: 'sql'
      properties: { privateDnsZoneId: sqlPrivateDnsZone.id }
    }]
  }
}

resource runtimeAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, runtimeIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

resource migrationAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, migrationIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    principalId: migrationIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

resource sqlDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'g6-to-log-analytics'
  scope: sqlServer
  properties: {
    workspaceId: logAnalytics.id
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
    metrics: [{ category: 'AllMetrics', enabled: true }]
  }
}

output qualificationId string = qualificationId
output qualificationResourceGroup string = resourceGroup().name
output qualificationReleaseSha string = releaseSha
output acrResourceId string = acr.id
output acrLoginServer string = acr.properties.loginServer
output sqlServerResourceId string = sqlServer.id
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output sqlDatabaseResourceId string = sqlDatabase.id
output privateEndpointResourceId string = sqlPrivateEndpoint.id
output sqlPrivateDnsZoneResourceId string = sqlPrivateDnsZone.id
output runtimeIdentityResourceId string = runtimeIdentity.id
output runtimeIdentityClientId string = runtimeIdentity.properties.clientId
output runtimeIdentityPrincipalId string = runtimeIdentity.properties.principalId
output migrationIdentityResourceId string = migrationIdentity.id
output migrationIdentityClientId string = migrationIdentity.properties.clientId
output migrationIdentityPrincipalId string = migrationIdentity.properties.principalId
output runtimeJobResourceId string = runtimeJob.id
output migrationJobResourceId string = migrationJob.id
output databaseUrl string = credentiallessDatabaseUrl
