targetScope = 'resourceGroup'

@description('The exact preproduction AI UAMI name.')
param aiIdentityName string = 'uami-proposalops-ai-preprod'
@description('The exact preproduction Azure OpenAI account name.')
param openAiAccountName string
@description('The exact deployment name frozen by AI-D2.')
param deploymentName string = 'proposalops-gpt51-methodology-v1'
@description('The approved Entra tenant.')
param tenantId string
@description('The Azure region for the actual model account.')
param modelRegion string = 'eastus'
@description('The exact deployed model name.')
param modelName string = 'gpt-5.4-mini'
@description('The exact deployed model version.')
param modelVersion string = '2026-03-17'
@description('The synchronous deployment SKU.')
param deploymentSku string = 'DataZoneStandard'
@description('The capacity units allocated to the deployment.')
param deploymentCapacity int = 10

resource aiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: aiIdentityName
  location: resourceGroup().location
}

resource openAi 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiAccountName
  location: modelRegion
  kind: 'OpenAI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${aiIdentity.id}': {}
    }
  }
  properties: {
    customSubDomainName: openAiAccountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
  sku: {
    name: 'S0'
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAi
  name: deploymentName
  sku: {
    name: deploymentSku
    capacity: deploymentCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

resource openAiUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
}

resource inferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, aiIdentityName, openAiUserRole.id)
  scope: openAi
  properties: {
    roleDefinitionId: openAiUserRole.id
    principalId: aiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output aiIdentityResourceId string = aiIdentity.id
output aiIdentityClientId string = aiIdentity.properties.clientId
output aiIdentityPrincipalId string = aiIdentity.properties.principalId
output tenant string = tenantId
output openAiResourceId string = openAi.id
output endpoint string = openAi.properties.endpoint
output deployment string = deployment.name
