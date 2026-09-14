targetScope = 'resourceGroup'

param aiAccountName string
param aiPrincipalId string
param roleDefinitionId string

resource aiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: aiAccountName
}

resource aiOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiAccount.id, aiPrincipalId, roleDefinitionId)
  scope: aiAccount
  properties: {
    principalId: aiPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: roleDefinitionId
  }
}
