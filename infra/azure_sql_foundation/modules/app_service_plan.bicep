targetScope = 'resourceGroup'

param location string
param planName string

@allowed([
  'B2'
  'B3'
])
param skuName string

param foundationSourceSha string

@minLength(40)
@maxLength(40)
param appServiceActivationSourceSha string

var planTags = {
  application: 'ProposalOps'
  environment: 'production'
  commissioningMode: 'synthetic-only'
  realDataAllowed: 'false'
  regionIntent: 'qatarcentral'
  managedBy: 'bicep'
  foundationLane: 'pre-phase5'
  foundationRevision: 'R2'
  foundationSourceSha: foundationSourceSha
  appServiceActivationRevision: 'R2R3-B2B3-v1'
  appServiceActivationSourceSha: appServiceActivationSourceSha
  appServiceSku: skuName
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  kind: 'linux'
  tags: planTags
  sku: {
    name: skuName
    tier: 'Basic'
    size: skuName
    family: 'B'
    capacity: 1
  }
  properties: {
    reserved: true
  }
}

output planName string = plan.name
output planId string = plan.id
