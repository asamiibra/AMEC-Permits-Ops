param location string
param vnetName string
param tags object

var vnetAddressPrefix = '10.42.0.0/16'
var appSubnetName = 'snet-appservice-integration'
var appSubnetPrefix = '10.42.0.0/26'
var postgresSubnetName = 'snet-postgres'
var postgresSubnetPrefix = '10.42.1.0/28'

resource vnet 'Microsoft.Network/virtualNetworks@2024-07-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
  }
}

resource appSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: appSubnetName
  properties: {
    addressPrefix: appSubnetPrefix
    delegations: [
      {
        name: 'appservice'
        properties: {
          serviceName: 'Microsoft.Web/serverFarms'
        }
      }
    ]
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
  }
}

resource postgresSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: vnet
  name: postgresSubnetName
  properties: {
    addressPrefix: postgresSubnetPrefix
    delegations: [
      {
        name: 'postgres-flexible-server'
        properties: {
          serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
        }
      }
    ]
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
  }
}

output vnetId string = vnet.id
output appSubnetId string = appSubnet.id
output postgresSubnetId string = postgresSubnet.id
output appSubnetPrefix string = appSubnetPrefix
output postgresSubnetPrefix string = postgresSubnetPrefix
