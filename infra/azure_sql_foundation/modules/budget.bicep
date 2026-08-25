targetScope = 'resourceGroup'

param budgetName string
param budgetAmount int
param budgetContactEmail string
param budgetStartDate string
param budgetEndDate string

resource budget 'Microsoft.Consumption/budgets@2024-08-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: budgetAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: budgetStartDate
      endDate: budgetEndDate
    }
    notifications: {
      Actual_50_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 50
        contactEmails: [budgetContactEmail]
      }
      Actual_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: [budgetContactEmail]
      }
      Actual_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        contactEmails: [budgetContactEmail]
      }
    }
  }
}

output budgetName string = budget.name
output budgetId string = budget.id
