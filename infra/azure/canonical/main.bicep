targetScope = 'resourceGroup'

@description('Canonical production region for ProposalOps.')
param location string = 'uaenorth'

@description('Deployment environment tag and resource-name namespace.')
param environmentName string = 'production'

@description('Resource-name namespace. Production defaults preserve the accepted names.')
param resourceNamePrefix string = 'production'

@description('Application environment value injected into runtime containers.')
param appEnvironment string = 'PROD'

@description('Whether the environment may process only synthetic content.')
param syntheticOnly bool = false

@description('Whether real data is allowed in the environment.')
param realDataAllowed bool = false

@description('Source intake protocol for the environment.')
param sourceIntakeMode string = 'BRIDGE'

@description('Synology integration mode for the environment.')
param synologyMode string = 'BRIDGE'

@description('Whether Azure may connect directly to Synology SMB.')
param azureDirectSynologySmb bool = false

@description('Storage provider used for managed generated artifacts.')
param storageProvider string = 'azure_blob'

@description('Whether the managed artifact store is required.')
param managedArtifactStoreRequired bool = true

@description('Whether the API ingress is externally reachable for the governed edge.')
param apiIngressExternal bool = true

@description('Derive the edge origin from the API Container App ingress FQDN.')
param deriveApiOriginHostName bool = false

@description('Resource group name used when composing private resource IDs.')
param resourceGroupName string = resourceGroup().name

@description('Exact immutable API image reference, including digest.')
param apiImage string

@description('Exact immutable worker image reference, including digest.')
param workerImage string

@description('Exact immutable migration image reference, including digest.')
param migrationImage string

@description('Exact immutable ClamAV sidecar image reference for Contract uploads.')
param clamavImage string

@description('Exact immutable frontend image reference, including digest.')
param frontendImage string

@description('Optional HTTPS hostname used by Azure Front Door to reach the API origin.')
param apiOriginHostName string = ''

@description('Optional production custom domain for the WAF-protected edge. DNS and certificate validation remain deployment-boundary actions.')
param edgeCustomDomainName string = ''

@description('Frontend origin allowed by the API CORS policy.')
param frontendOrigin string

@description('Enable Proposal Intelligence in the production API.')
param aiFeatureEnabled bool = true
@description('Enable external inference through the commissioned Azure OpenAI Responses provider.')
param aiExternalInferenceEnabled bool = true
@description('Real business content remains forbidden for the Owner-test release.')
param aiRealContentAllowed bool = false
@description('Immutable D4 commissioning record identifier.')
param aiD4CommissioningId string
@description('Azure OpenAI account resource group containing the commissioned deployment.')
param aiResourceGroupName string
@description('Azure OpenAI account containing the commissioned deployment.')
param aiAccountName string
@description('Approved Azure OpenAI Responses endpoint.')
param aiAzureOpenaiEndpoint string
param aiAzureOpenaiDeployment string = 'd3-gpt54mini-20260317'
param aiAzureOpenaiExpectedModel string = 'gpt-5.4-mini'
param aiAzureOpenaiExpectedVersion string = '2026-03-17'
param aiAzureOpenaiRegion string = 'eastus'
param aiAzureOpenaiDeploymentType string = 'DataZoneStandard'
param aiMaxInputTokenUpperBound int = 8192
param aiMaxOutputTokens int = 1024
param aiMaxRequestsPerUserPerMinute int = 20
param aiMaxRequestsPerUserPerHour int = 200
param aiMaxRequestsPerProjectPerHour int = 500
param aiMaxRequestsGlobalPerHour int = 5000
param aiMaxEstimatedCostUsdPerRequest string = '1'
param aiMaxEstimatedCostUsdPerDay string = '100'
param aiInputPriceUsdPer1mTokens string = '1'
param aiOutputPriceUsdPer1mTokens string = '1'
param aiPricingSourceReference string = 'azure-openai-d3-gpt54mini-20260317'
param aiD3SyntheticProjectIds string

@description('Entra tenant ID for application and SQL identity binding.')
param tenantId string

@description('Object ID of the approved Entra administrator for Azure SQL.')
param sqlAdministratorObjectId string

@description('Display name of the approved Entra administrator for Azure SQL.')
param sqlAdministratorLogin string

@description('Distinct SQL control-plane administrator login; never the Entra administrator login.')
param sqlServerAdministratorLogin string = 'proposalops_sql_control_plane'

@description('Tenant ID used by the Qatar Source Intake Bridge machine identity.')
param bridgeTenantId string

@description('Client ID used by the Qatar Source Intake Bridge machine identity.')
param bridgeClientId string

@description('Audience accepted for Qatar Source Intake Bridge tokens; normally the API client ID.')
param bridgeAudience string

@description('Application role required on Qatar Source Intake Bridge tokens.')
param bridgeRequiredRole string = 'proposalops.source-intake'

@description('Entra API application client ID.')
param entraApiClientId string

@description('Entra web application client ID.')
param entraWebClientId string

@secure()
@description('Runtime Azure SQL connection URL without inline credentials.')
param databaseUrl string

@secure()
@description('Dedicated migration-authority Azure SQL connection URL without inline credentials.')
param databaseMigrationUrl string

@secure()
@description('Required only by the Azure SQL resource API; local SQL authentication is disabled after provisioning.')
param sqlAdministratorPassword string

@description('Azure SQL logical server name.')
param sqlServerName string = 'sql-proposalops-production-uaenorth'

@description('Azure SQL database name.')
param sqlDatabaseName string = 'proposalops'

@description('Azure Container Registry name.')
param acrName string = 'acrproposalopsproduction'

@description('Azure Storage account for ProposalOps-generated managed artifacts.')
param artifactStorageName string = 'stproposalopsproduction'

var tags = {
  application: 'ProposalOps'
  environment: environmentName
  regionIntent: 'uaenorth'
  topology: 'azure-container-apps-azure-sql'
  managedBy: 'bicep'
}
var vnetName = 'vnet-proposalops-${resourceNamePrefix}-uaenorth'
var acaEnvironmentName = 'cae-proposalops-${resourceNamePrefix}-uaenorth'
var logAnalyticsName = 'law-proposalops-${resourceNamePrefix}-uaenorth'
var appInsightsName = 'appi-proposalops-${resourceNamePrefix}-uaenorth'
var keyVaultName = 'kv-proposalops-${resourceNamePrefix}'
var apiIdentityName = 'uami-proposalops-api-${resourceNamePrefix}'
var workerIdentityName = 'uami-proposalops-worker-${resourceNamePrefix}'
var migrationIdentityName = 'uami-proposalops-migration-${resourceNamePrefix}'
var sqlIdentityName = 'uami-proposalops-sql-${resourceNamePrefix}'
var aiIdentityName = 'uami-proposalops-ai-${resourceNamePrefix}'
var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var cognitiveServicesOpenAiUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
var frontDoorProfileName = 'afd-proposalops-${resourceNamePrefix}-uaenorth'
var frontDoorEndpointName = 'afde-proposalops-${resourceNamePrefix}-uaenorth'
var frontDoorWafPolicyName = 'waf-proposalops-${resourceNamePrefix}'
var sqlPrivateDnsZoneName = 'privatelink.database.windows.net'
var keyVaultPrivateDnsZoneName = 'privatelink.vaultcore.azure.net'
var blobPrivateDnsZoneName = 'privatelink.blob.core.windows.net'
var resolvedApiOriginHostName = deriveApiOriginHostName ? apiApp.properties.configuration.ingress.fqdn : apiOriginHostName


resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Standard' }
  tags: tags
  properties: {
    adminUserEnabled: false
    // G4 does not require a private-only registry.  Temporary Azure uses an
    // authenticated public endpoint; image pulls remain managed-identity
    // authenticated and anonymous pulls stay disabled.
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource artifactStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: artifactStorageName
  location: location
  sku: { name: 'Standard_ZRS' }
  kind: 'StorageV2'
  tags: tags
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

resource artifactBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: artifactStorage
  properties: {
    changeFeed: { enabled: true }
    containerDeleteRetentionPolicy: { enabled: true, days: 30 }
    deleteRetentionPolicy: { allowPermanentDelete: false, days: 30, enabled: true }
    isVersioningEnabled: true
  }
}

resource artifactContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: 'managed-artifacts'
  parent: artifactBlobService
  properties: { publicAccess: 'None' }
}

resource artifactManagementPolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  name: 'default'
  parent: artifactStorage
  properties: {
    policy: {
      rules: [
        {
          enabled: true
          name: 'managed-artifact-retention'
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: { delete: { daysAfterModificationGreaterThan: 3650 } }
            }
            filters: { blobTypes: ['blockBlob'], prefixMatch: ['managed-artifacts/'] }
          }
        }
      ]
    }
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.42.0.0/16'] }
    subnets: [
      {
        name: 'aca-infrastructure'
        properties: {
          addressPrefix: '10.42.0.0/23'
          delegations: [{ name: 'aca', properties: { serviceName: 'Microsoft.App/environments' } }]
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: '10.42.2.0/24'
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

resource keyVaultPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: keyVaultPrivateDnsZoneName
  location: 'global'
  tags: tags
}

resource blobPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: blobPrivateDnsZoneName
  location: 'global'
  tags: tags
}

resource sqlPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  name: 'vnet-link'
  parent: sqlPrivateDnsZone
  location: 'global'
  properties: { registrationEnabled: false, virtualNetwork: { id: vnet.id } }
}

resource keyVaultPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  name: 'vnet-link'
  parent: keyVaultPrivateDnsZone
  location: 'global'
  properties: { registrationEnabled: false, virtualNetwork: { id: vnet.id } }
}

resource blobPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  name: 'vnet-link'
  parent: blobPrivateDnsZone
  location: 'global'
  properties: { registrationEnabled: false, virtualNetwork: { id: vnet.id } }
}

resource apiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: apiIdentityName
  location: location
  tags: tags
}

resource workerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: workerIdentityName
  location: location
  tags: tags
}

resource migrationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: migrationIdentityName
  location: location
  tags: tags
}

resource sqlIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: sqlIdentityName
  location: location
  tags: tags
}

resource aiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: aiIdentityName
  location: location
  tags: tags
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    publicNetworkAccess: 'Disabled'
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
  }
}

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: sqlServerName
  location: location
  // SQL_SERVER_CONTROL_PLANE_IDENTITY: this UAMI is for the Azure SQL
  // resource's control-plane operations only. It is not a client token
  // selector for apiApp, workerApp, or migrationJob.
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${sqlIdentity.id}': {} }
  }
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
  sku: { name: 'GP_S_Gen5', tier: 'GeneralPurpose' }
  tags: tags
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    requestedBackupStorageRedundancy: 'Geo'
    zoneRedundant: true
    isLedgerOn: false
  }
}

resource sqlShortTermRetention 'Microsoft.Sql/servers/databases/backupShortTermRetentionPolicies@2023-08-01-preview' = {
  name: 'default'
  parent: sqlDatabase
  properties: { retentionDays: 35, diffBackupIntervalInHours: 24 }
}

resource sqlLongTermRetention 'Microsoft.Sql/servers/databases/backupLongTermRetentionPolicies@2023-08-01-preview' = {
  name: 'default'
  parent: sqlDatabase
  properties: { weeklyRetention: 'P1W', monthlyRetention: 'P12M', yearlyRetention: 'P5Y', weekOfYear: 1 }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: acaEnvironmentName
  location: location
  tags: tags
  properties: {
    publicNetworkAccess: 'Disabled'
    zoneRedundant: true
    vnetConfiguration: {
      infrastructureSubnetId: resourceId(resourceGroupName, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'aca-infrastructure')
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

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-proposalops-api-${resourceNamePrefix}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: union({ '${apiIdentity.id}': {} }, { '${aiIdentity.id}': {} })
  }
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: apiIngressExternal
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [{ server: acr.properties.loginServer, identity: apiIdentity.id }]
    }
    template: {
      containers: [{
        name: 'api'
        image: apiImage
        env: [
          { name: 'APP_ENV', value: appEnvironment }
          { name: 'AUTH_MODE', value: 'ENTRA' }
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_API_CLIENT_ID', value: entraApiClientId }
          { name: 'ENTRA_WEB_CLIENT_ID', value: entraWebClientId }
          { name: 'ENTRA_REQUIRED_SCOPE', value: 'access_as_user' }
          { name: 'SYNTHETIC_ONLY', value: string(syntheticOnly) }
          { name: 'REAL_DATA_ALLOWED', value: string(realDataAllowed) }
          { name: 'AZURE_SQL_AUTH_MODE', value: 'MANAGED_IDENTITY_ACCESS_TOKEN' }
          // The API token selector must match the UAMI attached to apiApp.
          { name: 'AZURE_SQL_UAMI_CLIENT_ID', value: apiIdentity.properties.clientId }
          { name: 'AZURE_SQL_UAMI_PRINCIPAL_ID', value: apiIdentity.properties.principalId }
          { name: 'DATABASE_URL', value: databaseUrl }
          { name: 'DATABASE_MIGRATION_URL', value: databaseMigrationUrl }
          { name: 'FRONTEND_ORIGINS', value: frontendOrigin }
          { name: 'STORAGE_PROVIDER', value: storageProvider }
          { name: 'MANAGED_ARTIFACT_STORE_REQUIRED', value: string(managedArtifactStoreRequired) }
          { name: 'CONTRACT_UPLOAD_SCANNER', value: 'clamav' }
          { name: 'CONTRACT_UPLOAD_CLAMAV_HOST', value: 'localhost' }
          { name: 'CONTRACT_UPLOAD_CLAMAV_PORT', value: '3310' }
          { name: 'AZURE_BLOB_ACCOUNT_URL', value: 'https://${artifactStorage.name}.blob.core.windows.net' }
          { name: 'AZURE_BLOB_CONTAINER', value: artifactContainer.name }
          { name: 'AZURE_BLOB_UAMI_CLIENT_ID', value: apiIdentity.properties.clientId }
          { name: 'SYNOLOGY_MODE', value: synologyMode }
          { name: 'SOURCE_INTAKE_MODE', value: sourceIntakeMode }
          { name: 'BRIDGE_TENANT_ID', value: bridgeTenantId }
          { name: 'BRIDGE_CLIENT_ID', value: bridgeClientId }
          { name: 'BRIDGE_AUDIENCE', value: bridgeAudience }
          { name: 'BRIDGE_REQUIRED_ROLE', value: bridgeRequiredRole }
          { name: 'AZURE_DIRECT_SYNOLOGY_SMB', value: string(azureDirectSynologySmb) }
          { name: 'AI_FEATURE_ENABLED', value: string(aiFeatureEnabled) }
          { name: 'AI_EXTERNAL_INFERENCE_ENABLED', value: string(aiExternalInferenceEnabled) }
          { name: 'AI_REAL_CONTENT_ALLOWED', value: string(aiRealContentAllowed) }
          { name: 'AI_D4_COMMISSIONING_ID', value: aiD4CommissioningId }
          { name: 'AI_AZURE_OPENAI_ENDPOINT', value: aiAzureOpenaiEndpoint }
          { name: 'AI_AZURE_OPENAI_DEPLOYMENT', value: aiAzureOpenaiDeployment }
          { name: 'AI_AZURE_OPENAI_EXPECTED_MODEL', value: aiAzureOpenaiExpectedModel }
          { name: 'AI_AZURE_OPENAI_EXPECTED_VERSION', value: aiAzureOpenaiExpectedVersion }
          { name: 'AI_AZURE_OPENAI_REGION', value: aiAzureOpenaiRegion }
          { name: 'AI_AZURE_OPENAI_DEPLOYMENT_TYPE', value: aiAzureOpenaiDeploymentType }
          { name: 'AI_UAMI_CLIENT_ID', value: aiIdentity.properties.clientId }
          { name: 'AI_UAMI_PRINCIPAL_ID', value: aiIdentity.properties.principalId }
          { name: 'AI_AZURE_TENANT_ID', value: tenantId }
          { name: 'AI_MAX_INPUT_TOKEN_UPPER_BOUND', value: string(aiMaxInputTokenUpperBound) }
          { name: 'AI_MAX_OUTPUT_TOKENS', value: string(aiMaxOutputTokens) }
          { name: 'AI_MAX_REQUESTS_PER_USER_PER_MINUTE', value: string(aiMaxRequestsPerUserPerMinute) }
          { name: 'AI_MAX_REQUESTS_PER_USER_PER_HOUR', value: string(aiMaxRequestsPerUserPerHour) }
          { name: 'AI_MAX_REQUESTS_PER_PROJECT_PER_HOUR', value: string(aiMaxRequestsPerProjectPerHour) }
          { name: 'AI_MAX_REQUESTS_GLOBAL_PER_HOUR', value: string(aiMaxRequestsGlobalPerHour) }
          { name: 'AI_MAX_ESTIMATED_COST_USD_PER_REQUEST', value: string(aiMaxEstimatedCostUsdPerRequest) }
          { name: 'AI_MAX_ESTIMATED_COST_USD_PER_DAY', value: string(aiMaxEstimatedCostUsdPerDay) }
          { name: 'AI_INPUT_PRICE_USD_PER_1M_TOKENS', value: string(aiInputPriceUsdPer1mTokens) }
          { name: 'AI_OUTPUT_PRICE_USD_PER_1M_TOKENS', value: string(aiOutputPriceUsdPer1mTokens) }
          { name: 'AI_PRICING_SOURCE_REFERENCE', value: aiPricingSourceReference }
          { name: 'AI_D3_SYNTHETIC_PROJECT_IDS', value: aiD3SyntheticProjectIds }
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        ]
        resources: {
          cpu: 1
          memory: '2Gi'
        }
      }, {
        name: 'clamav'
        image: clamavImage
        resources: {
          cpu: 1
          memory: '1Gi'
        }
      }]
      scale: { minReplicas: 2, maxReplicas: 10 }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-proposalops-frontend-${resourceNamePrefix}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${apiIdentity.id}': {} }
  }
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
      registries: [{ server: acr.properties.loginServer, identity: apiIdentity.id }]
    }
    template: {
      containers: [{
        name: 'frontend'
        image: frontendImage
        resources: { cpu: 1, memory: '1Gi' }
      }]
      scale: { minReplicas: 2, maxReplicas: 4 }
    }
  }
}

resource workerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-proposalops-worker-${resourceNamePrefix}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${workerIdentity.id}': {} }
  }
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [{ server: acr.properties.loginServer, identity: workerIdentity.id }]
    }
    template: {
      containers: [{
        name: 'worker'
        image: workerImage
        command: ['python', '-m', 'backend.app.worker']
        env: [
          { name: 'APP_ENV', value: appEnvironment }
          { name: 'AUTH_MODE', value: 'ENTRA' }
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_API_CLIENT_ID', value: entraApiClientId }
          { name: 'ENTRA_WEB_CLIENT_ID', value: entraWebClientId }
          { name: 'ENTRA_REQUIRED_SCOPE', value: 'access_as_user' }
          { name: 'SYNTHETIC_ONLY', value: string(syntheticOnly) }
          { name: 'REAL_DATA_ALLOWED', value: string(realDataAllowed) }
          { name: 'AZURE_SQL_AUTH_MODE', value: 'MANAGED_IDENTITY_ACCESS_TOKEN' }
          // The worker token selector must match the UAMI attached to workerApp.
          { name: 'AZURE_SQL_UAMI_CLIENT_ID', value: workerIdentity.properties.clientId }
          { name: 'AZURE_SQL_UAMI_PRINCIPAL_ID', value: workerIdentity.properties.principalId }
          { name: 'DATABASE_URL', value: databaseUrl }
          { name: 'DATABASE_MIGRATION_URL', value: databaseMigrationUrl }
          { name: 'FRONTEND_ORIGINS', value: frontendOrigin }
          { name: 'STORAGE_PROVIDER', value: storageProvider }
          { name: 'MANAGED_ARTIFACT_STORE_REQUIRED', value: string(managedArtifactStoreRequired) }
          { name: 'AZURE_BLOB_ACCOUNT_URL', value: 'https://${artifactStorage.name}.blob.core.windows.net' }
          { name: 'AZURE_BLOB_CONTAINER', value: artifactContainer.name }
          { name: 'AZURE_BLOB_UAMI_CLIENT_ID', value: workerIdentity.properties.clientId }
          { name: 'SYNOLOGY_MODE', value: synologyMode }
          { name: 'SOURCE_INTAKE_MODE', value: sourceIntakeMode }
          { name: 'BRIDGE_TENANT_ID', value: bridgeTenantId }
          { name: 'BRIDGE_CLIENT_ID', value: bridgeClientId }
          { name: 'BRIDGE_AUDIENCE', value: bridgeAudience }
          { name: 'BRIDGE_REQUIRED_ROLE', value: bridgeRequiredRole }
          { name: 'AZURE_DIRECT_SYNOLOGY_SMB', value: string(azureDirectSynologySmb) }
          { name: 'AI_FEATURE_ENABLED', value: string(aiFeatureEnabled) }
          { name: 'AI_EXTERNAL_INFERENCE_ENABLED', value: string(aiExternalInferenceEnabled) }
          { name: 'AI_REAL_CONTENT_ALLOWED', value: string(aiRealContentAllowed) }
          { name: 'AI_D4_COMMISSIONING_ID', value: aiD4CommissioningId }
          { name: 'AI_AZURE_OPENAI_ENDPOINT', value: aiAzureOpenaiEndpoint }
          { name: 'AI_AZURE_OPENAI_DEPLOYMENT', value: aiAzureOpenaiDeployment }
          { name: 'AI_AZURE_OPENAI_EXPECTED_MODEL', value: aiAzureOpenaiExpectedModel }
          { name: 'AI_AZURE_OPENAI_EXPECTED_VERSION', value: aiAzureOpenaiExpectedVersion }
          { name: 'AI_AZURE_OPENAI_REGION', value: aiAzureOpenaiRegion }
          { name: 'AI_AZURE_OPENAI_DEPLOYMENT_TYPE', value: aiAzureOpenaiDeploymentType }
          { name: 'AI_UAMI_CLIENT_ID', value: aiIdentity.properties.clientId }
          { name: 'AI_UAMI_PRINCIPAL_ID', value: aiIdentity.properties.principalId }
          { name: 'AI_AZURE_TENANT_ID', value: tenantId }
          { name: 'AI_D3_SYNTHETIC_PROJECT_IDS', value: aiD3SyntheticProjectIds }
        ]
        resources: {
          cpu: 1
          memory: '1Gi'
        }
      }]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource migrationJob 'Microsoft.App/jobs@2024-03-01' = {
  name: 'caj-proposalops-migration-${resourceNamePrefix}'
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
        image: migrationImage
        command: ['python', '-m', 'backend.app.migrate']
        env: [
          { name: 'APP_ENV', value: appEnvironment }
          { name: 'AUTH_MODE', value: 'ENTRA' }
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_API_CLIENT_ID', value: entraApiClientId }
          { name: 'ENTRA_WEB_CLIENT_ID', value: entraWebClientId }
          { name: 'ENTRA_REQUIRED_SCOPE', value: 'access_as_user' }
          { name: 'SYNTHETIC_ONLY', value: string(syntheticOnly) }
          { name: 'REAL_DATA_ALLOWED', value: string(realDataAllowed) }
          { name: 'AZURE_SQL_AUTH_MODE', value: 'MANAGED_IDENTITY_ACCESS_TOKEN' }
          // The migration token selector must match the UAMI attached to migrationJob.
          { name: 'AZURE_SQL_UAMI_CLIENT_ID', value: migrationIdentity.properties.clientId }
          { name: 'AZURE_SQL_UAMI_PRINCIPAL_ID', value: migrationIdentity.properties.principalId }
          { name: 'DATABASE_URL', value: databaseUrl }
          { name: 'DATABASE_MIGRATION_URL', value: databaseMigrationUrl }
          { name: 'FRONTEND_ORIGINS', value: frontendOrigin }
          { name: 'STORAGE_PROVIDER', value: storageProvider }
          { name: 'MANAGED_ARTIFACT_STORE_REQUIRED', value: string(managedArtifactStoreRequired) }
          { name: 'AZURE_BLOB_ACCOUNT_URL', value: 'https://${artifactStorage.name}.blob.core.windows.net' }
          { name: 'AZURE_BLOB_CONTAINER', value: artifactContainer.name }
          { name: 'AZURE_BLOB_UAMI_CLIENT_ID', value: migrationIdentity.properties.clientId }
          { name: 'SYNOLOGY_MODE', value: synologyMode }
          { name: 'SOURCE_INTAKE_MODE', value: sourceIntakeMode }
          { name: 'BRIDGE_TENANT_ID', value: bridgeTenantId }
          { name: 'BRIDGE_CLIENT_ID', value: bridgeClientId }
          { name: 'BRIDGE_AUDIENCE', value: bridgeAudience }
          { name: 'BRIDGE_REQUIRED_ROLE', value: bridgeRequiredRole }
          { name: 'AZURE_DIRECT_SYNOLOGY_SMB', value: string(azureDirectSynologySmb) }
          { name: 'AI_FEATURE_ENABLED', value: string(aiFeatureEnabled) }
          { name: 'AI_EXTERNAL_INFERENCE_ENABLED', value: string(aiExternalInferenceEnabled) }
          { name: 'AI_REAL_CONTENT_ALLOWED', value: string(aiRealContentAllowed) }
          { name: 'AI_D4_COMMISSIONING_ID', value: aiD4CommissioningId }
          { name: 'AI_AZURE_OPENAI_ENDPOINT', value: aiAzureOpenaiEndpoint }
          { name: 'AI_AZURE_OPENAI_DEPLOYMENT', value: aiAzureOpenaiDeployment }
          { name: 'AI_AZURE_OPENAI_EXPECTED_MODEL', value: aiAzureOpenaiExpectedModel }
          { name: 'AI_AZURE_OPENAI_EXPECTED_VERSION', value: aiAzureOpenaiExpectedVersion }
          { name: 'AI_AZURE_OPENAI_REGION', value: aiAzureOpenaiRegion }
          { name: 'AI_AZURE_OPENAI_DEPLOYMENT_TYPE', value: aiAzureOpenaiDeploymentType }
          { name: 'AI_UAMI_CLIENT_ID', value: aiIdentity.properties.clientId }
          { name: 'AI_UAMI_PRINCIPAL_ID', value: aiIdentity.properties.principalId }
          { name: 'AI_AZURE_TENANT_ID', value: tenantId }
          { name: 'AI_D3_SYNTHETIC_PROJECT_IDS', value: aiD3SyntheticProjectIds }
        ]
        resources: {
          cpu: 1
          memory: '1Gi'
        }
      }]
    }
  }
}

resource sqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${sqlServerName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: resourceId(resourceGroupName, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'private-endpoints') }
    privateLinkServiceConnections: [{
      name: 'sql'
      properties: {
        privateLinkServiceId: sqlServer.id
        groupIds: ['sqlServer']
      }
    }]
  }
}

resource keyVaultPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${keyVaultName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: resourceId(resourceGroupName, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'private-endpoints') }
    privateLinkServiceConnections: [{
      name: 'keyvault'
      properties: {
        privateLinkServiceId: keyVault.id
        groupIds: ['vault']
      }
    }]
  }
}

resource artifactStoragePrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${artifactStorageName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: resourceId(resourceGroupName, 'Microsoft.Network/virtualNetworks/subnets', vnetName, 'private-endpoints') }
    privateLinkServiceConnections: [{
      name: 'blob'
      properties: {
        privateLinkServiceId: artifactStorage.id
        groupIds: ['blob']
      }
    }]
  }
}

resource sqlPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  name: 'default'
  parent: sqlPrivateEndpoint
  properties: { privateDnsZoneConfigs: [{ name: 'sql', properties: { privateDnsZoneId: sqlPrivateDnsZone.id } }] }
}

resource keyVaultPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  name: 'default'
  parent: keyVaultPrivateEndpoint
  properties: { privateDnsZoneConfigs: [{ name: 'keyvault', properties: { privateDnsZoneId: keyVaultPrivateDnsZone.id } }] }
}

resource artifactStoragePrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  name: 'default'
  parent: artifactStoragePrivateEndpoint
  properties: { privateDnsZoneConfigs: [{ name: 'blob', properties: { privateDnsZoneId: blobPrivateDnsZone.id } }] }
}

resource edgeProfile 'Microsoft.Cdn/profiles@2024-02-01' = {
  name: frontDoorProfileName
  location: 'global'
  sku: { name: 'Premium_AzureFrontDoor' }
  tags: tags
}

resource edgeEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2024-02-01' = {
  name: frontDoorEndpointName
  parent: edgeProfile
  location: 'global'
  properties: { enabledState: 'Enabled' }
}

resource edgeOriginGroup 'Microsoft.Cdn/profiles/originGroups@2024-02-01' = {
  name: 'api-origin-group'
  parent: edgeProfile
  properties: {
    healthProbeSettings: {
      probeIntervalInSeconds: 30
      probePath: '/health/ready'
      probeProtocol: 'Https'
      probeRequestType: 'GET'
    }
    loadBalancingSettings: { additionalLatencyInMilliseconds: 0, sampleSize: 4, successfulSamplesRequired: 3 }
    sessionAffinityState: 'Disabled'
  }
}

resource edgeOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2024-02-01' = {
  name: 'api-origin'
  parent: edgeOriginGroup
  properties: {
    enabledState: 'Enabled'
    enforceCertificateNameCheck: true
    hostName: resolvedApiOriginHostName
    httpPort: 80
    httpsPort: 443
    originHostHeader: resolvedApiOriginHostName
    priority: 1
    weight: 1000
  }
}

resource frontendOriginGroup 'Microsoft.Cdn/profiles/originGroups@2024-02-01' = {
  name: 'frontend-origin-group'
  parent: edgeProfile
  properties: {
    healthProbeSettings: { probeIntervalInSeconds: 30, probePath: '/health', probeProtocol: 'Https', probeRequestType: 'GET' }
    loadBalancingSettings: { additionalLatencyInMilliseconds: 0, sampleSize: 4, successfulSamplesRequired: 3 }
    sessionAffinityState: 'Disabled'
  }
}

resource frontendEdgeOrigin 'Microsoft.Cdn/profiles/originGroups/origins@2024-02-01' = {
  name: 'frontend-origin'
  parent: frontendOriginGroup
  properties: {
    enabledState: 'Enabled'
    enforceCertificateNameCheck: true
    hostName: frontendApp.properties.configuration.ingress.fqdn
    httpPort: 80
    httpsPort: 443
    originHostHeader: frontendApp.properties.configuration.ingress.fqdn
    priority: 1
    weight: 1000
  }
}

resource edgeCustomDomain 'Microsoft.Cdn/profiles/customDomains@2024-02-01' = if (!empty(edgeCustomDomainName)) {
  name: 'production-api-domain'
  parent: edgeProfile
  properties: {
    hostName: edgeCustomDomainName
    tlsSettings: {
      certificateType: 'ManagedCertificate'
      minimumTlsVersion: 'TLS12'
    }
  }
}

resource edgeRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2024-02-01' = {
  name: 'api-route'
  parent: edgeEndpoint
  dependsOn: [edgeOrigin]
  properties: {
    customDomains: empty(edgeCustomDomainName) ? [] : [{ id: edgeCustomDomain.id }]
    enabledState: 'Enabled'
    forwardingProtocol: 'HttpsOnly'
    httpsRedirect: 'Enabled'
    linkToDefaultDomain: 'Enabled'
    originGroup: { id: edgeOriginGroup.id }
    patternsToMatch: ['/api/*']
    ruleSets: []
    supportedProtocols: ['Https']
  }
}

resource frontendEdgeRoute 'Microsoft.Cdn/profiles/afdEndpoints/routes@2024-02-01' = {
  name: 'frontend-route'
  parent: edgeEndpoint
  dependsOn: [frontendEdgeOrigin]
  properties: {
    cacheConfiguration: { compressionSettings: { isCompressionEnabled: true, contentTypesToCompress: ['text/html', 'text/css', 'application/javascript', 'application/json'] }, queryStringCachingBehavior: 'UseQueryString' }
    customDomains: empty(edgeCustomDomainName) ? [] : [{ id: edgeCustomDomain.id }]
    enabledState: 'Enabled'
    forwardingProtocol: 'HttpsOnly'
    httpsRedirect: 'Enabled'
    linkToDefaultDomain: 'Enabled'
    originGroup: { id: frontendOriginGroup.id }
    patternsToMatch: ['/*']
    ruleSets: []
    supportedProtocols: ['Https']
  }
}

resource edgeWafPolicy 'Microsoft.Network/frontdoorwebapplicationfirewallpolicies@2022-05-01' = {
  name: frontDoorWafPolicyName
  location: 'global'
  sku: { name: 'Premium_AzureFrontDoor' }
  tags: tags
  properties: {
    customRules: { rules: [] }
    managedRules: {
      managedRuleSets: [
        { ruleSetAction: 'Block', ruleSetType: 'DefaultRuleSet', ruleSetVersion: '2.1' }
        { ruleSetAction: 'Block', ruleSetType: 'Microsoft_BotManagerRuleSet', ruleSetVersion: '1.1' }
      ]
    }
    policySettings: { enabledState: 'Enabled', mode: 'Prevention', requestBodyCheck: 'Enabled' }
  }
}

resource edgeSecurityPolicy 'Microsoft.Cdn/profiles/securityPolicies@2024-02-01' = {
  name: 'api-waf-association'
  parent: edgeProfile
  properties: {
    parameters: {
      type: 'WebApplicationFirewall'
      associations: [{
        domains: [{ id: edgeEndpoint.id }]
        patternsToMatch: ['/*']
      }]
      wafPolicy: { id: edgeWafPolicy.id }
    }
  }
}

resource apiDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'platform-to-log-analytics'
  scope: apiApp
  properties: { workspaceId: logAnalytics.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}

resource workerDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'platform-to-log-analytics'
  scope: workerApp
  properties: { workspaceId: logAnalytics.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}

resource sqlDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'platform-to-log-analytics'
  scope: sqlServer
  // Azure SQL does not support the generic allLogs category group in every
  // region/API combination. Keep only the supported metrics category here;
  // resource-log categories must be added only after provider discovery.
  properties: { workspaceId: logAnalytics.id, metrics: [{ category: 'AllMetrics', enabled: true }] }
}

resource keyVaultDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'platform-to-log-analytics'
  scope: keyVault
  properties: { workspaceId: logAnalytics.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}

resource artifactStorageDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'platform-to-log-analytics'
  scope: artifactStorage
  properties: { workspaceId: logAnalytics.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}

resource edgeDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'platform-to-log-analytics'
  scope: edgeProfile
  properties: { workspaceId: logAnalytics.id, logs: [{ categoryGroup: 'allLogs', enabled: true }], metrics: [{ category: 'AllMetrics', enabled: true }] }
}

resource apiAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, apiIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: { principalId: apiIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: acrPullRoleDefinitionId }
}

resource workerAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, workerIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: { principalId: workerIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: acrPullRoleDefinitionId }
}

resource migrationAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, migrationIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: { principalId: migrationIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: acrPullRoleDefinitionId }
}

resource apiKeyVaultRead 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, apiIdentity.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: { principalId: apiIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: keyVaultSecretsUserRoleDefinitionId }
}

resource workerKeyVaultRead 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, workerIdentity.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: { principalId: workerIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: keyVaultSecretsUserRoleDefinitionId }
}

resource migrationKeyVaultRead 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, migrationIdentity.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: { principalId: migrationIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: keyVaultSecretsUserRoleDefinitionId }
}

resource apiArtifactWrite 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(artifactStorage.id, apiIdentity.id, storageBlobDataContributorRoleDefinitionId)
  scope: artifactStorage
  properties: { principalId: apiIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: storageBlobDataContributorRoleDefinitionId }
}

resource workerArtifactWrite 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(artifactStorage.id, workerIdentity.id, storageBlobDataContributorRoleDefinitionId)
  scope: artifactStorage
  properties: { principalId: workerIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: storageBlobDataContributorRoleDefinitionId }
}

resource migrationArtifactWrite 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(artifactStorage.id, migrationIdentity.id, storageBlobDataContributorRoleDefinitionId)
  scope: artifactStorage
  properties: { principalId: migrationIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: storageBlobDataContributorRoleDefinitionId }
}

module aiAuthorization './ai-role-assignment.bicep' = {
  name: 'proposalops-ai-authorization-${resourceNamePrefix}'
  scope: resourceGroup(aiResourceGroupName)
  params: {
    aiAccountName: aiAccountName
    aiPrincipalId: aiIdentity.properties.principalId
    roleDefinitionId: cognitiveServicesOpenAiUserRoleDefinitionId
  }
}

output canonicalTopology object = {
  region: location
  compute: 'Azure Container Apps'
  api: apiApp.name
  frontend: frontendApp.name
  worker: workerApp.name
  migrationJob: migrationJob.name
  registry: acr.name
  database: sqlServer.name
  databaseEngine: 'Azure SQL'
  secrets: keyVault.name
  managedArtifactStore: artifactStorage.name
  managedArtifactContainer: artifactContainer.name
  identities: [apiIdentity.name, workerIdentity.name, migrationIdentity.name, sqlIdentity.name, aiIdentity.name]
  ai: { endpoint: aiAzureOpenaiEndpoint, deployment: aiAzureOpenaiDeployment, model: aiAzureOpenaiExpectedModel, version: aiAzureOpenaiExpectedVersion, region: aiAzureOpenaiRegion, deploymentType: aiAzureOpenaiDeploymentType, identity: aiIdentity.name, d4CommissioningId: aiD4CommissioningId }
  privateNetwork: vnet.name
  privateEndpoints: [sqlPrivateEndpoint.name, keyVaultPrivateEndpoint.name, artifactStoragePrivateEndpoint.name]
  privateDnsZones: [sqlPrivateDnsZone.name, keyVaultPrivateDnsZone.name, blobPrivateDnsZone.name]
  observability: [logAnalytics.name, appInsights.name]
  publicIngress: 'Azure Front Door Premium with WAF Prevention'
  edgeEndpoint: edgeEndpoint.name
  edgeCustomDomain: edgeCustomDomainName
}
