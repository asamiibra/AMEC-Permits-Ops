using './main.bicep'

// Non-secret production decisions are pinned here. Images, Entra identifiers,
// SQL URLs, and the approved real-data setting enter only at the authorized
// deployment boundary through environment variables.
param location = 'uaenorth'
param environmentName = 'production'
param resourceNamePrefix = 'production'
param appEnvironment = 'PROD'
param syntheticOnly = false
param realDataAllowed = false
param sourceIntakeMode = 'BRIDGE'
param synologyMode = 'BRIDGE'
param azureDirectSynologySmb = false
param storageProvider = 'azure_blob'
param managedArtifactStoreRequired = true
param apiIngressExternal = true
param deriveApiOriginHostName = true
param apiOriginHostName = ''
param edgeCustomDomainName = 'www.amecidsystem.com'
param workerContinuous = true
param workerContractReconciliationEnabled = true
param apiImage = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_API_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param workerImage = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_WORKER_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param migrationImage = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_MIGRATION_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param clamavImage = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_CLAMAV_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param frontendOrigin = 'https://www.amecidsystem.com'
param tenantId = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_TENANT_ID', 'REQUIRED_AT_DEPLOYMENT')
param sqlAdministratorObjectId = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_SQL_ADMIN_OBJECT_ID', 'REQUIRED_AT_DEPLOYMENT')
param sqlAdministratorLogin = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_SQL_ENTRA_LOGIN', 'REQUIRED_AT_DEPLOYMENT')
param bridgeTenantId = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_BRIDGE_TENANT_ID', 'REQUIRED_AT_DEPLOYMENT')
param bridgeClientId = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_BRIDGE_CLIENT_ID', 'REQUIRED_AT_DEPLOYMENT')
param bridgeAudience = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_BRIDGE_AUDIENCE', 'REQUIRED_AT_DEPLOYMENT')
param entraApiClientId = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_API_CLIENT_ID', 'REQUIRED_AT_DEPLOYMENT')
param entraWebClientId = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_WEB_CLIENT_ID', 'REQUIRED_AT_DEPLOYMENT')
param databaseUrl = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_DATABASE_URL', 'REQUIRED_AT_DEPLOYMENT')
param databaseMigrationUrl = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_DATABASE_MIGRATION_URL', 'REQUIRED_AT_DEPLOYMENT')
param sqlAdministratorPassword = readEnvironmentVariable('PROPOSALOPS_PRODUCTION_SQL_PASSWORD', 'REQUIRED_AT_DEPLOYMENT')
