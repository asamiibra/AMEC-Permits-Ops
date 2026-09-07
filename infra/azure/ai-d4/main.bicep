targetScope = 'resourceGroup'

@description('The exact preproduction AI UAMI name.')
param aiIdentityName string = 'uami-proposalops-ai-preprod'
@description('A deterministic globally unique Azure OpenAI account name.')
param openAiAccountName string
@description('The exact deployment name frozen by AI-D4/D5.')
param deploymentName string = 'proposalops-gpt51-methodology-v1'
@description('The approved Entra tenant.')
param tenantId string
@description('The minimum currently valid GlobalStandard capacity proven before deployment.')
param globalStandardCapacity int
@description('The currently resolved Cognitive Services OpenAI User role definition resource ID.')
param openAiUserRoleDefinitionId string

resource aiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: aiIdentityName
  location: resourceGroup().location
}

resource openAi 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiAccountName
  location: 'uaenorth'
  kind: 'OpenAI'
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
    name: 'GlobalStandard'
    capacity: globalStandardCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.1'
      version: '2025-11-13'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

resource openAiUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: last(split(openAiUserRoleDefinitionId, '/'))
}

resource inferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, aiIdentity.id, openAiUserRole.id)
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
