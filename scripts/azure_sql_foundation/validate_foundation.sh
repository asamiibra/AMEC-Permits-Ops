#!/usr/bin/env bash
set -uo pipefail

BASE_SHA="${FOUNDATION_BASE_SHA:-707003fc16767fb28b9c968fbcf168ab03ebadc1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
MAIN=infra/azure_sql_foundation/main.bicep
NETWORK=infra/azure_sql_foundation/modules/network.bicep
CORE=infra/azure_sql_foundation/modules/core.bicep
DNS=infra/azure_sql_foundation/modules/private_dns.bicep
BUDGET=infra/azure_sql_foundation/modules/budget.bicep
PARAMS=infra/azure_sql_foundation/foundation.bicepparam.example
WORKFLOW=.github/workflows/azure-sql-foundation-static.yml
checks=0
failures=0
ids_file="$(mktemp)"
trap 'rm -f "$ids_file"' EXIT

check() {
  local id="$1"; shift
  if grep -Fqx "$id" "$ids_file"; then echo "FAIL duplicate-check-id $id"; failures=$((failures+1)); return; fi
  echo "$id" >> "$ids_file"; checks=$((checks+1))
  if "$@"; then echo "PASS $id"; else echo "FAIL $id"; failures=$((failures+1)); fi
}
has() { grep -Fq -- "$1" "$2"; }
not_has() { ! grep -Fq -- "$1" "$2"; }
count_is() { [[ "$(grep -Ec -- "$1" "$2")" -eq "$3" ]]; }
count_at_least() { [[ "$(grep -Foc -- "$1" "$2")" -ge "$3" ]]; }
count_fixed_is() { [[ "$(grep -Foc -- "$1" "$2")" -eq "$3" ]]; }
path_count_is() { [[ "$(git diff --name-only "$BASE_SHA" | wc -l | tr -d ' ')" -eq "$1" ]]; }
changed_count_is() { [[ "$(git diff --name-only "$BASE_SHA" | grep -c "$1" || true)" -eq "$2" ]]; }
no_forbidden_paths() { ! git diff --name-only "$BASE_SHA" | grep -E '^(backend|frontend|contracts|scripts/phase5|infra/azure|migrations|tests)/'; }
base_or_parent_ok() { [[ "$(git rev-parse HEAD)" == "$BASE_SHA" ]] || [[ "$(git log -1 --format=%P)" == "$BASE_SHA" ]]; }
allowed_status_only() {
  local bad
  bad="$(git status --porcelain | awk '{print $2}' | grep -Ev '^(\.github/workflows/azure-sql-foundation-static\.yml|infra/azure_sql_foundation/|scripts/azure_sql_foundation/)' || true)"
  [[ -z "$bad" ]]
}
exact_boundary() {
  local actual expected
  actual="$(git diff --name-only "$BASE_SHA" | sort)"
  expected="$(printf '%s\n' '.github/workflows/azure-sql-foundation-static.yml' 'infra/azure_sql_foundation/foundation.bicepparam.example' 'infra/azure_sql_foundation/main.bicep' 'infra/azure_sql_foundation/modules/budget.bicep' 'infra/azure_sql_foundation/modules/core.bicep' 'infra/azure_sql_foundation/modules/network.bicep' 'infra/azure_sql_foundation/modules/private_dns.bicep' 'scripts/azure_sql_foundation/validate_foundation.sh')"
  [[ "$actual" == "$expected" ]]
}

check S001 git rev-parse --is-inside-work-tree
check S002 bash -c "[[ \"$(git rev-parse --show-toplevel)\" == \"$ROOT\" ]]"
check S003 git cat-file -e "$BASE_SHA^{commit}"
check S004 git merge-base --is-ancestor "$BASE_SHA" HEAD
check S005 bash -c "[[ \"$(git branch --show-current)\" == azure-sql-foundation-prephase5-v1 ]]"
check S006 base_or_parent_ok
check S007 path_count_is 8
check S008 exact_boundary
check S009 no_forbidden_paths
check S010 bash -c "! git diff --name-only \"$BASE_SHA\" | grep -vE '^(\.github/workflows/azure-sql-foundation-static\.yml|infra/azure_sql_foundation/|scripts/azure_sql_foundation/)'"
check S011 changed_count_is '^infra/azure_sql_foundation/modules/' 4
check S012 changed_count_is '^scripts/azure_sql_foundation/' 1
check S013 changed_count_is '^\.github/workflows/' 1
check S014 allowed_status_only
check S015 bash -c "! git diff --name-only \"$BASE_SHA\" | grep -F 'infra/azure/'"
check F001 test -f "$MAIN"
check F002 test -f "$NETWORK"
check F003 test -f "$CORE"
check F004 test -f "$DNS"
check F005 test -f "$BUDGET"
check F006 test -f "$PARAMS"
check F007 test -f "$WORKFLOW"
check F008 test -x scripts/azure_sql_foundation/validate_foundation.sh
check C001 az bicep build --file "$MAIN" --stdout >/dev/null
check C002 az bicep build --file "$NETWORK" --stdout >/dev/null
check C003 az bicep build --file "$CORE" --stdout >/dev/null
check C004 az bicep build --file "$DNS" --stdout >/dev/null
check C005 az bicep build --file "$BUDGET" --stdout >/dev/null

while IFS='|' read -r id needle file; do
  [[ -z "$id" ]] && continue
  check "$id" has "$needle" "$file"
done <<CHECKS
M001|targetScope = 'subscription'|$MAIN
M002|Microsoft.Resources/resourceGroups@2025-04-01|$MAIN
M003|module budget|$MAIN
M004|Microsoft.Consumption/budgets@2024-08-01|$BUDGET
M005|targetScope = 'resourceGroup'|$BUDGET
M006|budgetAmount int|$MAIN
M007|budgetContactEmail string|$MAIN
M008|budgetStartDate string|$MAIN
M009|budgetEndDate string|$MAIN
M010|foundationSourceSha string|$MAIN
M011|qatarcentral|$MAIN
M012|production|$MAIN
M013|synthetic-only|$MAIN
M014|realDataAllowed: 'false'|$MAIN
M015|regionIntent: 'qatarcentral'|$MAIN
M016|managedBy: 'bicep'|$MAIN
M017|foundationLane: 'pre-phase5'|$MAIN
M018|foundationSourceSha: foundationSourceSha|$MAIN
M019|uniqueString(subscription().id, resourceGroupName)|$MAIN
M020|acrproposalopsprodqc|$MAIN
M021|rg-proposalops-prod-qc|$MAIN
M022|budget-proposalops-prod-qc|$MAIN
M023|vnet-proposalops-prod-qc|$MAIN
M024|snet-appservice-integration|$MAIN
M025|snet-sql-private-endpoints|$MAIN
M026|privatelink.database.windows.net|$MAIN
M027|link-proposalops-prod-qc|$MAIN
M028|law-proposalops-prod-qc|$MAIN
M029|appi-proposalops-prod-qc|$MAIN
M030|asp-proposalops-prod-qc|$MAIN
M031|id-proposalops-sql-bootstrap-prod-qc|$MAIN
M032|id-proposalops-sql-migrate-prod-qc|$MAIN
M033|Actual_50_Percent|$BUDGET
M034|Actual_80_Percent|$BUDGET
M035|Actual_100_Percent|$BUDGET
M036|threshold: 50|$BUDGET
M037|threshold: 80|$BUDGET
M038|threshold: 100|$BUDGET
M039|contactEmails|$BUDGET
M040|module network|$MAIN
M041|module privateDns|$MAIN
M042|module core|$MAIN
M043|dependsOn: [budget]|$MAIN
M044|dependsOn: [budget, network]|$MAIN
M045|network.outputs.vnetId|$MAIN
M046|output plannedResourceGroupName|$MAIN
M047|output plannedMigrationIdentityName|$MAIN
N001|Microsoft.Network/virtualNetworks@2024-07-01|$NETWORK
N002|10.42.0.0/16|$NETWORK
N003|10.42.0.0/26|$NETWORK
N004|10.42.1.0/28|$NETWORK
N005|Microsoft.Web/serverFarms|$NETWORK
N006|delegations: []|$NETWORK
N007|appServiceSubnetName|$NETWORK
N008|sqlPrivateEndpointSubnetName|$NETWORK
N009|privateEndpointNetworkPolicies: 'Disabled'|$NETWORK
N010|privateLinkServiceNetworkPolicies: 'Enabled'|$NETWORK
N011|resource vnet|$NETWORK
N012|resource appServiceSubnet|$NETWORK
N013|resource sqlPrivateEndpointSubnet|$NETWORK
N014|serviceName: 'Microsoft.Web/serverFarms'|$NETWORK
N015|output vnetId string|$NETWORK
N016|output vnetName string|$NETWORK
N017|output appServiceSubnetId string|$NETWORK
N018|output appServiceSubnetName string|$NETWORK
N019|output sqlPrivateEndpointSubnetId string|$NETWORK
N020|output sqlPrivateEndpointSubnetName|$NETWORK
N021|parent: vnet|$NETWORK
N022|addressSpace|$NETWORK
N023|addressPrefixes|$NETWORK
N024|properties: { serviceName|$NETWORK
N025|tags: tags|$NETWORK
D001|Microsoft.Network/privateDnsZones@2024-06-01|$DNS
D002|privateDnsZoneName|$DNS
D003|virtualNetworkLinks@2024-06-01|$DNS
D004|registrationEnabled: false|$DNS
D005|virtualNetwork: { id: vnetId }|$DNS
D006|location: 'global'|$DNS
D007|resource privateDnsZone|$DNS
D008|resource privateDnsLink|$DNS
D009|parent: privateDnsZone|$DNS
D010|output privateDnsZoneName string|$DNS
D011|output privateDnsZoneId string|$DNS
D012|output privateDnsLinkName string|$DNS
D013|output privateDnsLinkId string|$DNS
D014|tags: tags|$DNS
D015|properties: {}|$DNS
K001|Microsoft.ContainerRegistry/registries@2025-04-01|$CORE
K002|name: 'Basic'|$CORE
K003|adminUserEnabled: false|$CORE
K004|anonymousPullEnabled: false|$CORE
K005|publicNetworkAccess: 'Enabled'|$CORE
K006|Microsoft.OperationalInsights/workspaces@2023-09-01|$CORE
K007|name: 'PerGB2018'|$CORE
K008|retentionInDays: 30|$CORE
K009|Microsoft.Insights/components@2020-02-02|$CORE
K010|Application_Type: 'web'|$CORE
K011|WorkspaceResourceId: law.id|$CORE
K012|Microsoft.Web/serverfarms@2024-04-01|$CORE
K013|kind: 'linux'|$CORE
K014|name: 'B1'|$CORE
K015|tier: 'Basic'|$CORE
K016|capacity: 1|$CORE
K017|reserved: true|$CORE
K018|Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31|$CORE
K019|resource acr|$CORE
K020|resource law|$CORE
K021|resource appInsights|$CORE
K022|resource plan|$CORE
K023|resource bootstrapIdentity|$CORE
K024|resource migrationIdentity|$CORE
K025|bootstrapIdentityName|$CORE
K026|migrationIdentityName|$CORE
K027|output acrName string|$CORE
K028|output lawName string|$CORE
K029|output appInsightsName string|$CORE
K030|output planName string|$CORE
K031|output bootstrapIdentityName string|$CORE
K032|output migrationIdentityName string|$CORE
K033|tags: tags|$CORE
K034|properties: { reserved: true }|$CORE
K035|sku: { name: 'Basic' }|$CORE
K036|sku: { name: 'PerGB2018'|$CORE
K037|location: location|$CORE
K038|WorkspaceResourceId|$CORE
P001|readEnvironmentVariable('OWNER_MONTHLY_COST_CEILING_USD')|$PARAMS
P002|readEnvironmentVariable('BUDGET_CONTACT_EMAIL')|$PARAMS
P003|<FOUNDATION_SOURCE_SHA>|$PARAMS
P004|using './main.bicep'|$PARAMS
P005|qatarcentral|$PARAMS
P006|rg-proposalops-prod-qc|$PARAMS
P007|budget-proposalops-prod-qc|$PARAMS
P008|2026-08-01|$PARAMS
P009|2036-08-01|$PARAMS
P010|Owner-approved environment|$PARAMS
P011|budgetAmount|$PARAMS
P012|budgetContactEmail|$PARAMS
P013|foundationSourceSha|$PARAMS
P014|budgetStartDate|$PARAMS
P015|budgetEndDate|$PARAMS
CHECKS

for forbidden in 'Microsoft.Sql/servers' 'Microsoft.Sql/servers/databases' 'Microsoft.Network/privateEndpoints' 'Microsoft.Web/sites' 'Microsoft.KeyVault/vaults' 'Microsoft.Storage/storageAccounts' 'Microsoft.ServiceBus/namespaces' 'Microsoft.Cache/Redis' 'Microsoft.Search/searchServices' 'Microsoft.CognitiveServices/accounts' 'Microsoft.App/' 'Microsoft.Compute/' 'Microsoft.ContainerService/' 'publicIPAddresses' 'virtualNetworkGateways' 'Microsoft.DBforPostgreSQL' 'Microsoft.Authorization/roleAssignments' 'Microsoft.Network/networkSecurityGroups' 'virtualNetworkPeerings'; do
  id="X$(printf '%03d' $((checks+1)))"
  check "$id" bash -c "! grep -RqsF -- '$forbidden' infra/azure_sql_foundation"
done
for secret_pattern in 'BEGIN PRIVATE KEY' 'Bearer ' 'clientSecret' 'accessToken' 'password=' 'secret=' 'subscriptionId=' 'tenantId=' 'BUDGET_CONTACT_EMAIL='; do
  id="Q$(printf '%03d' $((checks+1)))"
  check "$id" bash -c "! grep -RqsE -- '$secret_pattern' infra/azure_sql_foundation"
done
check X021 not_has Synology "$MAIN"
check X022 not_has SMB "$MAIN"
check X023 not_has Phase6 "$MAIN"
check X024 not_has 'docker push' "$MAIN"
check X025 not_has 'Microsoft.DBforPostgreSQL' "$MAIN"
check X026 not_has 'Microsoft.Sql' "$MAIN"
check X027 not_has 'Microsoft.Network/privateEndpoints' "$MAIN"
check X028 not_has 'Microsoft.Web/sites' "$MAIN"
check X029 not_has 'Microsoft.KeyVault' "$MAIN"
check X030 not_has roleAssignments "$MAIN"
check X031 not_has federatedIdentityCredentials "$MAIN"
check X032 not_has administratorLogin "$MAIN"
check X033 not_has postgres "$MAIN"
check X034 not_has deployApps "$MAIN"
check X035 not_has deployPostgres "$MAIN"

check W001 has azure-sql-foundation-prephase5-v1 "$WORKFLOW"
check W002 has 'infra/azure_sql_foundation/**' "$WORKFLOW"
check W003 has scripts/azure_sql_foundation/validate_foundation.sh "$WORKFLOW"
check W004 has 'az bicep build' "$WORKFLOW"
check W005 has validate_foundation.sh "$WORKFLOW"
check W006 has upload-artifact "$WORKFLOW"
check W007 has 'contents: read' "$WORKFLOW"
check W008 not_has azure/login "$WORKFLOW"
check W009 not_has AZURE_CREDENTIALS "$WORKFLOW"
check W010 not_has secrets. "$WORKFLOW"
check W011 not_has 'az deployment' "$WORKFLOW"
check W012 not_has 'az group create' "$WORKFLOW"
check W013 not_has --subscription "$WORKFLOW"
check W014 has permissions: "$WORKFLOW"
check W015 has paths: "$WORKFLOW"

check R001 count_is '^resource ' "$MAIN" 1
check R002 count_is '^module ' "$MAIN" 4
check R003 count_is '^output ' "$MAIN" 12
check R004 count_is "resource .*'Microsoft.Network/virtualNetworks/subnets" "$NETWORK" 2
check R005 count_is "resource .*'Microsoft.ManagedIdentity/userAssignedIdentities" "$CORE" 2
check R006 count_is 'threshold: 50' "$BUDGET" 1
check R007 count_is 'threshold: 80' "$BUDGET" 1
check R008 count_is 'threshold: 100' "$BUDGET" 1
check R009 count_is 'contactEmails:' "$BUDGET" 3
check R010 count_is Actual_50_Percent "$BUDGET" 1
check R011 count_is Actual_80_Percent "$BUDGET" 1
check R012 count_is Actual_100_Percent "$BUDGET" 1
check R013 count_at_least 'Microsoft.' "$MAIN" 1
check R014 count_at_least foundationSourceSha "$MAIN" 2
check R015 count_at_least resourceTags "$MAIN" 1
check R016 count_at_least qatarcentral "$MAIN" 1
check R017 count_at_least synthetic-only "$MAIN" 1
check R018 count_is "realDataAllowed: 'false'" "$MAIN" 1
check R019 count_is WorkspaceResourceId "$CORE" 1
check R020 count_is 'registrationEnabled: false' "$DNS" 1
check R021 count_fixed_is 'delegations: []' "$NETWORK" 1
check R022 count_is 'Microsoft.Web/serverFarms' "$NETWORK" 1
check R023 count_is 'Microsoft.ManagedIdentity/userAssignedIdentities' "$CORE" 2
check R024 count_is 'Microsoft.Network/privateDnsZones' "$DNS" 2
check R025 count_at_least B1 "$CORE" 2
check R026 count_is PerGB2018 "$CORE" 1
check R027 count_is 'retentionInDays: 30' "$CORE" 1
check R028 count_is 'anonymousPullEnabled: false' "$CORE" 1
check R029 count_is 'adminUserEnabled: false' "$CORE" 1
check R030 count_is "publicNetworkAccess: 'Enabled'" "$CORE" 1

echo "LOCAL_FOUNDATION_CHECKS=$checks"
echo "LOCAL_FOUNDATION_FAIL=$failures"
if [[ "$failures" -eq 0 && "$checks" -ge 150 ]]; then
  echo 'LOCAL_FOUNDATION_VALIDATION=PASS'; exit 0
fi
echo 'LOCAL_FOUNDATION_VALIDATION=FAIL'; exit 1
