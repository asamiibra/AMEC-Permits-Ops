param privateDnsZoneName string
param privateDnsLinkName string
param vnetId string
param tags object

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: privateDnsZoneName
  tags: tags
  properties: {}
}

resource privateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: privateDnsZone
  name: privateDnsLinkName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

output privateDnsZoneName string = privateDnsZone.name
output privateDnsZoneId string = privateDnsZone.id
output privateDnsLinkName string = privateDnsLink.name
output privateDnsLinkId string = privateDnsLink.id
