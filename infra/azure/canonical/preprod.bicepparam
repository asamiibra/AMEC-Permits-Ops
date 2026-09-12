using './main.bicep'

// Non-secret values are fixed to the isolated G8 namespace. Image, Entra,
// database URL, and SQL bootstrap inputs are supplied only at the authorized
// deployment boundary through environment variables.
param location = 'uaenorth'
param environmentName = 'preprod'
param resourceNamePrefix = 'g8p60912'
param appEnvironment = 'AZURE-PREPROD'
param syntheticOnly = true
param realDataAllowed = false
param sourceIntakeMode = 'BRIDGE'
param synologyMode = 'BRIDGE'
param azureDirectSynologySmb = false
param storageProvider = 'azure_blob'
param managedArtifactStoreRequired = true
param apiIngressExternal = true
param deriveApiOriginHostName = true
param apiOriginHostName = ''
param edgeCustomDomainName = ''
param apiImage = readEnvironmentVariable('PROPOSALOPS_PREPROD_API_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param workerImage = readEnvironmentVariable('PROPOSALOPS_PREPROD_WORKER_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param migrationImage = readEnvironmentVariable('PROPOSALOPS_PREPROD_MIGRATION_IMAGE', 'REQUIRED_AT_DEPLOYMENT')
param frontendOrigin = readEnvironmentVariable('PROPOSALOPS_PREPROD_FRONTEND_ORIGIN', 'https://preprod.invalid')
param tenantId = readEnvironmentVariable('PROPOSALOPS_PREPROD_TENANT_ID', '00000000-0000-0000-0000-000000000000')
param sqlAdministratorObjectId = readEnvironmentVariable('PROPOSALOPS_PREPROD_SQL_ADMIN_OBJECT_ID', '00000000-0000-0000-0000-000000000000')
param sqlAdministratorLogin = readEnvironmentVariable('PROPOSALOPS_PREPROD_SQL_ENTRA_LOGIN', 'REQUIRED_AT_DEPLOYMENT')
param sqlServerAdministratorLogin = 'proposalops_g8_sqladmin'
param bridgeTenantId = readEnvironmentVariable('PROPOSALOPS_PREPROD_BRIDGE_TENANT_ID', '00000000-0000-0000-0000-000000000000')
param bridgeClientId = readEnvironmentVariable('PROPOSALOPS_PREPROD_BRIDGE_CLIENT_ID', '00000000-0000-0000-0000-000000000000')
param bridgeAudience = readEnvironmentVariable('PROPOSALOPS_PREPROD_BRIDGE_AUDIENCE', '00000000-0000-0000-0000-000000000000')
param bridgeRequiredRole = 'proposalops.source-intake'
param entraApiClientId = readEnvironmentVariable('PROPOSALOPS_PREPROD_API_CLIENT_ID', '00000000-0000-0000-0000-000000000000')
param entraWebClientId = readEnvironmentVariable('PROPOSALOPS_PREPROD_WEB_CLIENT_ID', '11111111-1111-1111-1111-111111111111')
param databaseUrl = readEnvironmentVariable('PROPOSALOPS_PREPROD_DATABASE_URL', 'mssql+pyodbc://@required-at-deployment/proposalops-preprod?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no')
param databaseMigrationUrl = readEnvironmentVariable('PROPOSALOPS_PREPROD_DATABASE_MIGRATION_URL', 'mssql+pyodbc://@required-at-deployment/proposalops-preprod?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no')
param sqlAdministratorPassword = readEnvironmentVariable('PROPOSALOPS_PREPROD_SQL_PASSWORD', 'REQUIRED_AT_DEPLOYMENT')
param sqlServerName = 'sql-proposalops-g8p60912'
param sqlDatabaseName = 'proposalops-preprod'
param acrName = 'acrg8p60912'
param artifactStorageName = 'stproposalopsg8p60912'
