targetScope = 'resourceGroup'

@description('The exact preproduction AI UAMI name.')
param aiIdentityName string = 'uami-proposalops-ai-preprod'
@description('The existing Microsoft Foundry account name.')
param aiAccountName string
@description('The existing Microsoft Foundry project name.')
param projectName string
@description('The approved Entra tenant.')
param tenantId string

resource aiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: aiIdentityName
  location: resourceGroup().location
}

resource aiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: aiAccountName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: aiAccount
  name: projectName
}

resource foundryUserRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: '53ca6127-db72-4b80-b1b0-d745d6d5456d'
}

resource inferenceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, aiIdentityName, foundryUserRole.id)
  scope: aiProject
  properties: {
    roleDefinitionId: foundryUserRole.id
    principalId: aiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output aiIdentityResourceId string = aiIdentity.id
output aiIdentityClientId string = aiIdentity.properties.clientId
output aiIdentityPrincipalId string = aiIdentity.properties.principalId
output tenant string = tenantId
output aiAccountResourceId string = aiAccount.id
output projectResourceId string = aiProject.id
output endpoint string = 'https://${aiAccountName}.services.ai.azure.com/api/projects/${projectName}'
output accessMode string = 'INSTANT'
output model string = 'gpt-5-mini'
output modelVersion string = '2025-08-07'
