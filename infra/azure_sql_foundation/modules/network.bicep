param location string
param vnetName string
param appServiceSubnetName string
param sqlPrivateEndpointSubnetName string
param tags object

resource vnet 'Microsoft.Network/virtualNetworks@2024-07-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.42.0.0/16'] }
  }
}

resource appServiceSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: appServiceSubnetName
  properties: {
    addressPrefix: '10.42.0.0/26'
    delegations: [{
      name: 'appservice'
      properties: { serviceName: 'Microsoft.Web/serverFarms' }
    }]
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
  }
}

resource sqlPrivateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: sqlPrivateEndpointSubnetName
  properties: {
    addressPrefix: '10.42.1.0/28'
    delegations: []
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output appServiceSubnetId string = appServiceSubnet.id
output appServiceSubnetName string = appServiceSubnet.name
output sqlPrivateEndpointSubnetId string = sqlPrivateEndpointSubnet.id
output sqlPrivateEndpointSubnetName string = sqlPrivateEndpointSubnet.name
