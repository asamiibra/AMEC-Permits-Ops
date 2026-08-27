targetScope = 'subscription'

@description('Azure region for the production ProposalOps foundation.')
param location string = 'qatarcentral'
@description('Production resource group name.')
param resourceGroupName string = 'rg-proposalops-prod-qc'
@description('Resource-group Cost Management budget name.')
param budgetName string = 'budget-proposalops-prod-qc'
@minValue(1)
@description('Owner-provided monthly USD budget alert threshold. Supply at deployment time.')
param budgetAmount int
@description('Owner-provided valid budget notification email. Supply at deployment time.')
param budgetContactEmail string
@description('First day of the current budget period, in YYYY-MM-DD format.')
param budgetStartDate string
@description('End date for the budget period, in YYYY-MM-DD format.')
param budgetEndDate string
@description('Exact committed foundation source SHA used for provenance tags.')
param foundationSourceSha string
@description('Whether to deploy the deferred Linux Basic App Service Plan. Must remain false unless explicitly activated.')
param deployAppServicePlan bool = false
@allowed([
  'B2'
  'B3'
])
@description('Explicit Basic Linux App Service Plan SKU for activation.')
param appServicePlanSku string
@minLength(40)
@maxLength(40)
@description('Exact source SHA for this App Service activation candidate.')
param appServiceActivationSourceSha string

var resourceTags = {
  application: 'ProposalOps'
  environment: 'production'
  commissioningMode: 'synthetic-only'
  realDataAllowed: 'false'
  regionIntent: 'qatarcentral'
  managedBy: 'bicep'
  foundationLane: 'pre-phase5'
  foundationRevision: 'R2'
  foundationSourceSha: foundationSourceSha
}
var deterministicSuffix = uniqueString(subscription().id, resourceGroupName)
var acrName = toLower('acrproposalopsprodqc${deterministicSuffix}')
var vnetName = 'vnet-proposalops-prod-qc'
var appServiceSubnetName = 'snet-appservice-integration'
var sqlPrivateEndpointSubnetName = 'snet-sql-private-endpoints'
var privateDnsZoneName = 'privatelink.database.windows.net'
var privateDnsLinkName = 'link-proposalops-prod-qc'
var lawName = 'law-proposalops-prod-qc'
var appInsightsName = 'appi-proposalops-prod-qc'
var planName = 'asp-proposalops-prod-qc'
var bootstrapIdentityName = 'id-proposalops-sql-bootstrap-prod-qc'
var migrationIdentityName = 'id-proposalops-sql-migrate-prod-qc'

resource resourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: resourceTags
}

module budget './modules/budget.bicep' = {
  name: 'budget-proposalops-prod-qc'
  scope: resourceGroup
  params: {
    budgetName: budgetName
    budgetAmount: budgetAmount
    budgetContactEmail: budgetContactEmail
    budgetStartDate: budgetStartDate
    budgetEndDate: budgetEndDate
  }
}

module network './modules/network.bicep' = {
  name: 'network-proposalops-prod-qc'
  scope: resourceGroup
  dependsOn: [budget]
  params: {
    location: location
    vnetName: vnetName
    appServiceSubnetName: appServiceSubnetName
    sqlPrivateEndpointSubnetName: sqlPrivateEndpointSubnetName
    tags: resourceTags
  }
}

module privateDns './modules/private_dns.bicep' = {
  name: 'private-dns-proposalops-prod-qc'
  scope: resourceGroup
  dependsOn: [budget, network]
  params: {
    privateDnsZoneName: privateDnsZoneName
    privateDnsLinkName: privateDnsLinkName
    vnetId: network.outputs.vnetId
    tags: resourceTags
  }
}

module core './modules/core.bicep' = {
  name: 'core-proposalops-prod-qc'
  scope: resourceGroup
  dependsOn: [budget]
  params: {
    location: location
    acrName: acrName
    lawName: lawName
    appInsightsName: appInsightsName
    bootstrapIdentityName: bootstrapIdentityName
    migrationIdentityName: migrationIdentityName
    tags: resourceTags
  }
}

module appServicePlan './modules/app_service_plan.bicep' = if (deployAppServicePlan) {
  name: 'app-service-plan-proposalops-prod-qc'
  scope: resourceGroup
  dependsOn: [budget]
  params: {
    location: location
    planName: planName
    skuName: appServicePlanSku
    foundationSourceSha: foundationSourceSha
    appServiceActivationSourceSha: appServiceActivationSourceSha
  }
}

output plannedResourceGroupName string = resourceGroup.name
output plannedBudgetName string = budget.outputs.budgetName
output plannedVnetName string = network.outputs.vnetName
output plannedAppServiceSubnetName string = network.outputs.appServiceSubnetName
output plannedSqlPrivateEndpointSubnetName string = network.outputs.sqlPrivateEndpointSubnetName
output plannedPrivateDnsZoneName string = privateDns.outputs.privateDnsZoneName
output plannedAcrName string = core.outputs.acrName
output plannedLogAnalyticsName string = core.outputs.lawName
output plannedApplicationInsightsName string = core.outputs.appInsightsName
output plannedAppServicePlanName string = deployAppServicePlan ? appServicePlan.outputs.planName : ''
output plannedBootstrapIdentityName string = core.outputs.bootstrapIdentityName
output plannedMigrationIdentityName string = core.outputs.migrationIdentityName
