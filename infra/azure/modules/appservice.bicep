param location string
param planId string
param acrName string
param appSubnetId string
param frontendAppName string
param backendAppName string
param frontendImage string
param backendImage string
param frontendOrigin string
param entraTenantId string
param entraWebClientId string
param entraApiClientId string
param logAnalyticsId string
param tags object

var acrPullRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)

resource acr 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: acrName
}

resource frontend 'Microsoft.Web/sites@2024-04-01' = {
  name: frontendAppName
  location: location
  kind: 'app,linux,container'
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: planId
    httpsOnly: true
    clientAffinityEnabled: false
    siteConfig: {
      alwaysOn: true
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      acrUseManagedIdentityCreds: true
      linuxFxVersion: 'DOCKER|${frontendImage}'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8080'
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${acr.properties.loginServer}'
        }
      ]
    }
  }
}

resource backend 'Microsoft.Web/sites@2024-04-01' = {
  name: backendAppName
  location: location
  kind: 'app,linux,container'
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: planId
    httpsOnly: true
    clientAffinityEnabled: false
    siteConfig: {
      alwaysOn: true
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      acrUseManagedIdentityCreds: true
      linuxFxVersion: 'DOCKER|${backendImage}'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'true'
        }
        {
          name: 'WEBSITE_SKIP_RUNNING_KUDUAGENT'
          value: 'false'
        }
        {
          name: 'FRONTEND_ORIGINS'
          value: frontendOrigin
        }
        {
          name: 'APP_ENV'
          value: 'AZURE-PREPROD'
        }
        {
          name: 'SYNTHETIC_ONLY'
          value: 'true'
        }
        {
          name: 'REAL_DATA_ALLOWED'
          value: 'false'
        }
        {
          name: 'AUTH_MODE'
          value: 'ENTRA'
        }
        {
          name: 'ENTRA_REQUIRED_SCOPE'
          value: 'access_as_user'
        }
        {
          name: 'ENTRA_TENANT_ID'
          value: entraTenantId
        }
        {
          name: 'ENTRA_WEB_CLIENT_ID'
          value: entraWebClientId
        }
        {
          name: 'ENTRA_API_CLIENT_ID'
          value: entraApiClientId
        }
        {
          name: 'STORAGE_PROVIDER'
          value: 'mock'
        }
        {
          name: 'SYNOLOGY_MODE'
          value: 'SYNTHETIC'
        }
      ]
    }
  }
}

resource frontendAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, frontend.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    roleDefinitionId: acrPullRoleDefinitionId
    principalId: frontend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, backend.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    roleDefinitionId: acrPullRoleDefinitionId
    principalId: backend.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource frontendVnetIntegration 'Microsoft.Web/sites/virtualNetworkConnections@2024-04-01' = {
  parent: frontend
  name: 'virtualNetwork'
  properties: {
    vnetResourceId: appSubnetId
  }
}

resource backendVnetIntegration 'Microsoft.Web/sites/virtualNetworkConnections@2024-04-01' = {
  parent: backend
  name: 'virtualNetwork'
  properties: {
    vnetResourceId: appSubnetId
  }
}

resource frontendScmCredentialsPolicy 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: frontend
  name: 'scm'
  properties: {
    allow: false
  }
}

resource frontendFtpCredentialsPolicy 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: frontend
  name: 'ftp'
  properties: {
    allow: false
  }
}

resource backendScmCredentialsPolicy 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: backend
  name: 'scm'
  properties: {
    allow: false
  }
}

resource backendFtpCredentialsPolicy 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-04-01' = {
  parent: backend
  name: 'ftp'
  properties: {
    allow: false
  }
}

resource frontendDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'appservice-logs'
  scope: frontend
  properties: {
    workspaceId: logAnalyticsId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource backendDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'appservice-logs'
  scope: backend
  properties: {
    workspaceId: logAnalyticsId
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

output frontendId string = frontend.id
output backendId string = backend.id
output frontendPrincipalId string = frontend.identity.principalId
output backendPrincipalId string = backend.identity.principalId
