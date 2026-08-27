param location string
param acrName string
param lawName string
param appInsightsName string
param bootstrapIdentityName string
param migrationIdentityName string
param tags object

resource acr 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
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
    WorkspaceResourceId: law.id
  }
}

resource bootstrapIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: bootstrapIdentityName
  location: location
  tags: tags
}

resource migrationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: migrationIdentityName
  location: location
  tags: tags
}

output acrName string = acr.name
output acrId string = acr.id
output lawName string = law.name
output lawId string = law.id
output appInsightsName string = appInsights.name
output appInsightsId string = appInsights.id
output bootstrapIdentityName string = bootstrapIdentity.name
output bootstrapIdentityId string = bootstrapIdentity.id
output migrationIdentityName string = migrationIdentity.name
output migrationIdentityId string = migrationIdentity.id
