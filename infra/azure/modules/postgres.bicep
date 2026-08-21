param location string
param serverName string
param postgresMajorVersion string
param administratorLogin string
@secure()
param administratorLoginPassword string
param backupRetentionDays int = 7
param postgresSubnetId string
param vnetId string
param privateDnsZoneName string
param tags object

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: privateDnsZoneName
  location: 'global'
  tags: tags
}

resource privateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: privateDnsZone
  name: 'proposalops-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnetId
    }
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: 'Standard_D2s_v3'
    tier: 'GeneralPurpose'
  }
  properties: {
    version: postgresMajorVersion
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: 128
      autoGrow: 'Enabled'
      type: 'Premium_LRS'
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: postgresSubnetId
      privateDnsZoneArmResourceId: privateDnsZone.id
      publicNetworkAccess: 'Disabled'
    }
  }
  dependsOn: [
    privateDnsLink
  ]
}

resource proposalOpsDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'proposalops'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

output postgresId string = postgres.id
output privateDnsZoneId string = privateDnsZone.id
