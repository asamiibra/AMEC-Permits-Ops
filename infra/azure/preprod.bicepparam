using './main.bicep'

param location = 'qatarcentral'
param environment = 'preprod'
param resourceGroupName = 'rg-proposalops-preprod-qc'
param deployApps = false
param deployPostgres = false
param appServiceSkuName = 'B1'
param appServiceSkuTier = 'Basic'
param postgresMajorVersion = '16'
param postgresBackupRetentionDays = 7
