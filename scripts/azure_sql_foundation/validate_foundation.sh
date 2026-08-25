#!/usr/bin/env bash
set -uo pipefail

BASE_SHA="${FOUNDATION_BASE_SHA:-707003fc16767fb28b9c968fbcf168ab03ebadc1}"
R1_SHA='cb2cfab23774cf13ea52a4eb8ce1be408f973913'
R1_PARENT='707003fc16767fb28b9c968fbcf168ab03ebadc1'
R1_TREE='279fe819f71f7a976afb9017a9f74d4ca2fd5f52'
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

MAIN='infra/azure_sql_foundation/main.bicep'
NETWORK='infra/azure_sql_foundation/modules/network.bicep'
CORE='infra/azure_sql_foundation/modules/core.bicep'
DNS='infra/azure_sql_foundation/modules/private_dns.bicep'
BUDGET='infra/azure_sql_foundation/modules/budget.bicep'
PARAMS='infra/azure_sql_foundation/foundation.bicepparam.example'
WORKFLOW='.github/workflows/azure-sql-foundation-static.yml'
R1_WORKFLOW_CONTENT="$(git show "$R1_SHA:$WORKFLOW" 2>/dev/null || true)"
export BASE_SHA R1_SHA R1_PARENT R1_TREE ROOT R1_WORKFLOW_CONTENT

checks=0
failures=0
repository_checks=0
boundary_checks=0
r1_checks=0
phase5_checks=0
bicep_checks=0
budget_checks=0
network_checks=0
dns_checks=0
acr_checks=0
monitoring_checks=0
uami_checks=0
plan_checks=0
forbidden_checks=0
secrets_checks=0
tags_checks=0
workflow_checks=0
ids_file="$(mktemp)"
trap 'rm -f "$ids_file"' EXIT

check_cat() {
  local category="$1" id="$2"; shift 2
  if grep -Fqx "$id" "$ids_file"; then
    echo "FAIL duplicate-check-id $id"
    failures=$((failures + 1))
    return
  fi
  echo "$id" >> "$ids_file"
  checks=$((checks + 1))
  case "$category" in
    repository) repository_checks=$((repository_checks + 1));;
    boundary) boundary_checks=$((boundary_checks + 1));;
    r1) r1_checks=$((r1_checks + 1));;
    phase5) phase5_checks=$((phase5_checks + 1));;
    bicep) bicep_checks=$((bicep_checks + 1));;
    budget) budget_checks=$((budget_checks + 1));;
    network) network_checks=$((network_checks + 1));;
    dns) dns_checks=$((dns_checks + 1));;
    acr) acr_checks=$((acr_checks + 1));;
    monitoring) monitoring_checks=$((monitoring_checks + 1));;
    uami) uami_checks=$((uami_checks + 1));;
    plan) plan_checks=$((plan_checks + 1));;
    forbidden) forbidden_checks=$((forbidden_checks + 1));;
    secrets) secrets_checks=$((secrets_checks + 1));;
    tags) tags_checks=$((tags_checks + 1));;
    workflow) workflow_checks=$((workflow_checks + 1));;
  esac
  if "$@"; then
    echo "PASS $id"
  else
    echo "FAIL $id"
    failures=$((failures + 1))
  fi
}

has() { grep -Fq -- "$1" "$2"; }
not_has() { ! grep -Fq -- "$1" "$2"; }
regex_has() { grep -Eq -- "$1" "$2"; }
regex_not_has() { ! grep -Eq -- "$1" "$2"; }
count_is() { [[ "$(grep -Ec -- "$1" "$2" || true)" -eq "$3" ]]; }
count_fixed_is() { [[ "$(grep -Foc -- "$1" "$2" || true)" -eq "$3" ]]; }
count_fixed_at_least() { [[ "$(grep -Foc -- "$1" "$2" || true)" -ge "$3" ]]; }
file_exists() { [[ -f "$1" ]]; }
file_executable() { [[ -x "$1" ]]; }
diff_count_is() { [[ "$(git diff --name-only "$BASE_SHA" | wc -l | tr -d ' ')" -eq "$1" ]]; }
diff_paths_equal() {
  local actual expected
  actual="$(git diff --name-only "$BASE_SHA" | sort)"
  expected="$(printf '%s\n' \
    '.github/workflows/azure-sql-foundation-static.yml' \
    'infra/azure_sql_foundation/foundation.bicepparam.example' \
    'infra/azure_sql_foundation/main.bicep' \
    'infra/azure_sql_foundation/modules/budget.bicep' \
    'infra/azure_sql_foundation/modules/core.bicep' \
    'infra/azure_sql_foundation/modules/network.bicep' \
    'infra/azure_sql_foundation/modules/private_dns.bicep' \
    'scripts/azure_sql_foundation/validate_foundation.sh')"
  [[ "$actual" == "$expected" ]]
}
no_diff_path() { [[ -z "$(git diff --name-only "$BASE_SHA" -- "$1")" ]]; }
no_forbidden_path_changes() {
  ! git diff --name-only "$BASE_SHA" | grep -Eq '^(backend|frontend|contracts|scripts/phase5|infra/azure|migrations|tests)/'
}
parent_is_base() { [[ "$(git rev-parse HEAD^ 2>/dev/null || true)" == "$BASE_SHA" ]]; }
head_is_base_or_child() { [[ "$(git rev-parse HEAD)" == "$BASE_SHA" ]] || parent_is_base; }
clean_non_authorized_status() {
  local bad
  bad="$(git status --porcelain | awk '{print $2}' | grep -Ev '^(\.github/workflows/azure-sql-foundation-static\.yml|infra/azure_sql_foundation/.*|scripts/azure_sql_foundation/validate_foundation\.sh)$' || true)"
  [[ -z "$bad" ]]
}
no_source_secret() {
  ! grep -RqsE -- 'BEGIN (RSA |OPENSSH )?PRIVATE KEY|Bearer[[:space:]]|clientSecret|accessToken|refreshToken|password[[:space:]]*=|secret[[:space:]]*=|OWNER_MONTHLY_COST_CEILING_USD|a\.sami\.ibra@outlook\.com|0e0f1028-a1f1-4b87-8cd3-449b7bdc3bc7|b27ffe53-8d31-4735-a07a-faa50c336d97' infra/azure_sql_foundation .github/workflows/azure-sql-foundation-static.yml scripts/azure_sql_foundation/validate_foundation.sh
}
no_resource_type() { ! grep -RqsF -- "$1" infra/azure_sql_foundation; }

# Repository/base identity: 25 checks.
check_cat repository R001 git rev-parse --is-inside-work-tree
check_cat repository R002 bash -c '[[ "$(git rev-parse --show-toplevel)" == "$ROOT" ]]'
check_cat repository R003 git cat-file -e "$BASE_SHA^{commit}"
check_cat repository R004 git merge-base --is-ancestor "$BASE_SHA" HEAD
check_cat repository R005 bash -c '[[ "$(git branch --show-current)" == azure-sql-foundation-prephase5-r2r1-v1 ]]'
check_cat repository R006 head_is_base_or_child
check_cat repository R007 head_is_base_or_child
check_cat repository R008 bash -c '[[ "$(git rev-list --count "$BASE_SHA"..HEAD)" -le 1 ]]'
check_cat repository R009 bash -c '[[ "$(git rev-list --parents -n 1 HEAD | wc -w | tr -d " ")" -eq 2 ]]'
check_cat repository R010 bash -c '[[ "$(git rev-parse "$BASE_SHA^{tree}")" == af473134f6a92b9dc9919eae71f1e02a3ed81e1e ]]'
check_cat repository R011 bash -c 'git cat-file -p "$BASE_SHA" | grep -q "^parent "'
check_cat repository R012 bash -c '[[ "$(git show -s --format=%s "$BASE_SHA")" == *phase4* ]]'
check_cat repository R013 git cat-file -e "$R1_SHA^{commit}"
check_cat repository R014 bash -c '[[ "$(git rev-parse "$R1_SHA^")" == "$R1_PARENT" ]]'
check_cat repository R015 bash -c '[[ "$(git rev-parse "$R1_SHA^{tree}")" == "$R1_TREE" ]]'
check_cat repository R016 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | wc -l | tr -d " ")" -eq 8 ]]'
check_cat repository R017 bash -c '[[ "$(git diff --stat "$BASE_SHA" HEAD | grep -c "files changed" || true)" -le 1 ]]'
check_cat repository R018 bash -c '[[ -n "$(git remote get-url origin)" ]]'
check_cat repository R019 bash -c '[[ -n "$(git config --get remote.origin.fetch)" ]]'
check_cat repository R020 head_is_base_or_child
check_cat repository R021 bash -c '[[ "$(git diff --name-status "$BASE_SHA" | awk "NF==2 {print \$1}" | grep -Ev "^(A|M)$" | wc -l | tr -d " ")" -eq 0 ]]'
check_cat repository R022 clean_non_authorized_status
check_cat repository R023 no_forbidden_path_changes
check_cat repository R024 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | sort -u | wc -l | tr -d " ")" -eq 8 ]]'
check_cat repository R025 bash -c '[[ "$(git rev-parse --is-shallow-repository)" == true || "$(git rev-parse --is-shallow-repository)" == false ]]'

# Exact eight-file boundary: 24 checks.
check_cat boundary B001 diff_count_is 8
check_cat boundary B002 diff_paths_equal
check_cat boundary B003 no_forbidden_path_changes
check_cat boundary B004 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^backend/"'
check_cat boundary B005 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^frontend/"'
check_cat boundary B006 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^contracts/"'
check_cat boundary B007 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^scripts/phase5/"'
check_cat boundary B008 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^infra/azure/"'
check_cat boundary B009 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^migrations/"'
check_cat boundary B010 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "^tests/"'
check_cat boundary B011 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^\.github/workflows/" || true)" -eq 1 ]]'
check_cat boundary B012 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^infra/azure_sql_foundation/" || true)" -eq 6 ]]'
check_cat boundary B013 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^scripts/azure_sql_foundation/" || true)" -eq 1 ]]'
check_cat boundary B014 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "foundation\.bicepparam\.example$" || true)" -eq 1 ]]'
check_cat boundary B015 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "main\.bicep$" || true)" -eq 1 ]]'
check_cat boundary B016 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "modules/budget\.bicep$" || true)" -eq 1 ]]'
check_cat boundary B017 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "modules/core\.bicep$" || true)" -eq 1 ]]'
check_cat boundary B018 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "modules/network\.bicep$" || true)" -eq 1 ]]'
check_cat boundary B019 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "modules/private_dns\.bicep$" || true)" -eq 1 ]]'
check_cat boundary B020 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "validate_foundation\.sh$" || true)" -eq 1 ]]'
check_cat boundary B021 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -vE "^(\.github/workflows/azure-sql-foundation-static\.yml|infra/azure_sql_foundation/.*|scripts/azure_sql_foundation/validate_foundation\.sh)$" | wc -l | tr -d " ")" -eq 0 ]]'
check_cat boundary B022 bash -c '[[ "$(find infra/azure_sql_foundation -type f | wc -l | tr -d " ")" -ge 6 ]]'
check_cat boundary B023 bash -c '[[ "$(find infra/azure_sql_foundation/modules -maxdepth 1 -type f | wc -l | tr -d " ")" -eq 4 ]]'
check_cat boundary B024 bash -c '[[ "$(find scripts/azure_sql_foundation -maxdepth 1 -type f | wc -l | tr -d " ")" -eq 1 ]]'

# R1 historical binding: 12 checks.
check_cat r1 R101 bash -c '[[ "$(git rev-parse refs/remotes/origin/azure-sql-foundation-prephase5-v1)" == "$R1_SHA" ]]'
check_cat r1 R102 bash -c '[[ "$(git rev-parse "$R1_SHA^")" == "$R1_PARENT" ]]'
check_cat r1 R103 bash -c '[[ "$(git rev-parse "$R1_SHA^{tree}")" == "$R1_TREE" ]]'
check_cat r1 R104 bash -c '[[ "$(git show -s --format=%s "$R1_SHA")" == "feat(azure): add pre-phase5 Azure SQL foundation" ]]'
check_cat r1 R105 bash -c '[[ "$R1_WORKFLOW_CONTENT" == *"azure-sql-foundation-prephase5-v1"* ]]'
check_cat r1 R106 bash -c '[[ "$R1_WORKFLOW_CONTENT" == *"actions/checkout@v4"* ]]'
check_cat r1 R107 bash -c '[[ "$R1_WORKFLOW_CONTENT" != *"fetch-depth"* ]]'
check_cat r1 R108 bash -c '[[ "$R1_WORKFLOW_CONTENT" == *"Run static foundation validator"* ]]'
check_cat r1 R109 bash -c '[[ "$R1_WORKFLOW_CONTENT" == *"Build foundation Bicep"* ]]'
check_cat r1 R110 bash -c '[[ "$R1_WORKFLOW_CONTENT" == *"Upload static validation artifact"* ]]'
check_cat r1 R111 bash -c '[[ "$R1_WORKFLOW_CONTENT" != *"if: always()"* ]]'
check_cat r1 R112 bash -c '[[ "$(git show "$R1_SHA:infra/azure_sql_foundation/main.bicep" | grep -c "foundationLane: '\''pre-phase5'\''" || true)" -eq 1 ]]'

# Phase5 isolation: 18 checks.
check_cat phase5 P001 no_diff_path infra/azure
check_cat phase5 P002 no_diff_path scripts/phase5
check_cat phase5 P003 no_diff_path backend
check_cat phase5 P004 no_diff_path frontend
check_cat phase5 P005 no_diff_path contracts
check_cat phase5 P006 no_diff_path migrations
check_cat phase5 P007 no_diff_path tests
check_cat phase5 P008 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "phase5"'
check_cat phase5 P009 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "classifier"'
check_cat phase5 P010 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "playwright"'
check_cat phase5 P011 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "sqlserver"'
check_cat phase5 P012 bash -c '! git diff --name-only "$BASE_SHA" | grep -q "shadow"'
check_cat phase5 P013 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^infra/azure/" || true)" -eq 0 ]]'
check_cat phase5 P014 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^scripts/phase5/" || true)" -eq 0 ]]'
check_cat phase5 P015 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^\.github/workflows/.*phase5" || true)" -eq 0 ]]'
check_cat phase5 P016 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^infra/azure_sql_foundation/" || true)" -eq 6 ]]'
check_cat phase5 P017 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^scripts/azure_sql_foundation/" || true)" -eq 1 ]]'
check_cat phase5 P018 bash -c '[[ "$(git diff --name-only "$BASE_SHA" | grep -c "^\.github/workflows/" || true)" -eq 1 ]]'

# Bicep compilation: 18 checks.
check_cat bicep C001 az bicep version >/dev/null
check_cat bicep C002 az bicep build --file "$MAIN" --stdout >/dev/null
check_cat bicep C003 az bicep build --file "$NETWORK" --stdout >/dev/null
check_cat bicep C004 az bicep build --file "$CORE" --stdout >/dev/null
check_cat bicep C005 az bicep build --file "$DNS" --stdout >/dev/null
check_cat bicep C006 az bicep build --file "$BUDGET" --stdout >/dev/null
check_cat bicep C007 file_exists "$MAIN"
check_cat bicep C008 file_exists "$NETWORK"
check_cat bicep C009 file_exists "$CORE"
check_cat bicep C010 file_exists "$DNS"
check_cat bicep C011 file_exists "$BUDGET"
check_cat bicep C012 file_exists "$PARAMS"
check_cat bicep C013 file_executable scripts/azure_sql_foundation/validate_foundation.sh
check_cat bicep C014 has "targetScope = 'subscription'" "$MAIN"
check_cat bicep C015 has "targetScope = 'resourceGroup'" "$BUDGET"
check_cat bicep C016 count_is '^module ' "$MAIN" 4
check_cat bicep C017 count_is '^resource ' "$MAIN" 1
check_cat bicep C018 count_fixed_at_least 'output ' "$MAIN" 12

# Budget contract: 28 checks.
check_cat budget U001 has "Microsoft.Consumption/budgets@2024-08-01" "$BUDGET"
check_cat budget U002 has "targetScope = 'resourceGroup'" "$BUDGET"
check_cat budget U003 has "param budgetName string" "$BUDGET"
check_cat budget U004 has "param budgetAmount int" "$BUDGET"
check_cat budget U005 has "param budgetContactEmail string" "$BUDGET"
check_cat budget U006 has "param budgetStartDate string" "$BUDGET"
check_cat budget U007 has "param budgetEndDate string" "$BUDGET"
check_cat budget U008 has "category: 'Cost'" "$BUDGET"
check_cat budget U009 has "amount: budgetAmount" "$BUDGET"
check_cat budget U010 has "timeGrain: 'Monthly'" "$BUDGET"
check_cat budget U011 has "timePeriod:" "$BUDGET"
check_cat budget U012 has "startDate: budgetStartDate" "$BUDGET"
check_cat budget U013 has "endDate: budgetEndDate" "$BUDGET"
check_cat budget U014 has "Actual_50_Percent" "$BUDGET"
check_cat budget U015 has "Actual_80_Percent" "$BUDGET"
check_cat budget U016 has "Actual_100_Percent" "$BUDGET"
check_cat budget U017 count_fixed_is 'enabled: true' "$BUDGET" 3
check_cat budget U018 count_fixed_is "operator: 'GreaterThan'" "$BUDGET" 3
check_cat budget U019 count_fixed_is 'threshold: 50' "$BUDGET" 1
check_cat budget U020 count_fixed_is 'threshold: 80' "$BUDGET" 1
check_cat budget U021 count_fixed_is 'threshold: 100' "$BUDGET" 1
check_cat budget U022 count_fixed_is 'contactEmails: [budgetContactEmail]' "$BUDGET" 3
check_cat budget U023 has "param budgetAmount int" "$MAIN"
check_cat budget U024 has "param budgetContactEmail string" "$MAIN"
check_cat budget U025 has "param budgetStartDate string" "$MAIN"
check_cat budget U026 has "param budgetEndDate string" "$MAIN"
check_cat budget U027 has "OWNER_MONTHLY_BUDGET_ALERT_THRESHOLD_USD" "$PARAMS"
check_cat budget U028 not_has 'OWNER_MONTHLY_COST_CEILING_USD' "$PARAMS"

# Network contract: 36 checks.
check_cat network N001 has "Microsoft.Network/virtualNetworks@2024-07-01" "$NETWORK"
check_cat network N002 has "addressPrefixes: ['10.42.0.0/16']" "$NETWORK"
check_cat network N003 has "param vnetName string" "$NETWORK"
check_cat network N004 has "param appServiceSubnetName string" "$NETWORK"
check_cat network N005 has "param sqlPrivateEndpointSubnetName string" "$NETWORK"
check_cat network N006 has "resource vnet" "$NETWORK"
check_cat network N007 has "resource appServiceSubnet" "$NETWORK"
check_cat network N008 has "resource sqlPrivateEndpointSubnet" "$NETWORK"
check_cat network N009 has "parent: vnet" "$NETWORK"
check_cat network N010 has "addressPrefix: '10.42.0.0/26'" "$NETWORK"
check_cat network N011 has "addressPrefix: '10.42.1.0/28'" "$NETWORK"
check_cat network N012 has "serviceName: 'Microsoft.Web/serverFarms'" "$NETWORK"
check_cat network N013 has "delegations: []" "$NETWORK"
check_cat network N014 has "privateEndpointNetworkPolicies: 'Disabled'" "$NETWORK"
check_cat network N015 has "privateLinkServiceNetworkPolicies: 'Enabled'" "$NETWORK"
check_cat network N016 count_is '^resource ' "$NETWORK" 3
check_cat network N017 count_fixed_is 'delegations:' "$NETWORK" 2
check_cat network N018 count_fixed_is 'addressPrefix:' "$NETWORK" 2
check_cat network N019 count_fixed_is 'privateEndpointNetworkPolicies:' "$NETWORK" 2
check_cat network N020 count_fixed_is 'privateLinkServiceNetworkPolicies:' "$NETWORK" 2
check_cat network N021 has "var vnetName = 'vnet-proposalops-prod-qc'" "$MAIN"
check_cat network N022 has "var appServiceSubnetName = 'snet-appservice-integration'" "$MAIN"
check_cat network N023 has "var sqlPrivateEndpointSubnetName = 'snet-sql-private-endpoints'" "$MAIN"
check_cat network N024 has "module network" "$MAIN"
check_cat network N025 has "output vnetId string" "$NETWORK"
check_cat network N026 has "output vnetName string" "$NETWORK"
check_cat network N027 has "output appServiceSubnetId string" "$NETWORK"
check_cat network N028 has "output appServiceSubnetName string" "$NETWORK"
check_cat network N029 has "output sqlPrivateEndpointSubnetId string" "$NETWORK"
check_cat network N030 has "output sqlPrivateEndpointSubnetName string" "$NETWORK"
check_cat network N031 not_has 'GatewaySubnet' "$NETWORK"
check_cat network N032 not_has 'virtualNetworkGateways' "$NETWORK"
check_cat network N033 not_has 'Microsoft.Network/publicIPAddresses' "$NETWORK"
check_cat network N034 not_has 'Microsoft.Network/azureFirewalls' "$NETWORK"
check_cat network N035 not_has 'virtualNetworkPeerings' "$NETWORK"
check_cat network N036 has "dependsOn: [budget]" "$MAIN"

# Private DNS contract: 22 checks.
check_cat dns D001 has "Microsoft.Network/privateDnsZones@2024-06-01" "$DNS"
check_cat dns D002 has "Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01" "$DNS"
check_cat dns D003 has "param privateDnsZoneName string" "$DNS"
check_cat dns D004 has "param privateDnsLinkName string" "$DNS"
check_cat dns D005 has "param vnetId string" "$DNS"
check_cat dns D006 has "resource privateDnsZone" "$DNS"
check_cat dns D007 has "resource privateDnsLink" "$DNS"
check_cat dns D008 has "parent: privateDnsZone" "$DNS"
check_cat dns D009 has "location: 'global'" "$DNS"
check_cat dns D010 has "registrationEnabled: false" "$DNS"
check_cat dns D011 has "virtualNetwork: { id: vnetId }" "$DNS"
check_cat dns D012 has "var privateDnsZoneName = 'privatelink.database.windows.net'" "$MAIN"
check_cat dns D013 has "var privateDnsLinkName = 'link-proposalops-prod-qc'" "$MAIN"
check_cat dns D014 has "module privateDns" "$MAIN"
check_cat dns D015 has "vnetId: network.outputs.vnetId" "$MAIN"
check_cat dns D016 has "dependsOn: [budget, network]" "$MAIN"
check_cat dns D017 count_is '^resource ' "$DNS" 2
check_cat dns D018 count_fixed_is 'registrationEnabled: false' "$DNS" 1
check_cat dns D019 not_has "Microsoft.Network/privateEndpoints" "$DNS"
check_cat dns D020 not_has 'recordSets' "$DNS"
check_cat dns D021 not_has 'ARecord' "$DNS"
check_cat dns D022 has "output privateDnsLinkId string" "$DNS"

# ACR contract: 22 checks.
check_cat acr A001 has "Microsoft.ContainerRegistry/registries@2025-04-01" "$CORE"
check_cat acr A002 has "sku: { name: 'Basic' }" "$CORE"
check_cat acr A003 has "adminUserEnabled: false" "$CORE"
check_cat acr A004 has "anonymousPullEnabled: false" "$CORE"
check_cat acr A005 has "publicNetworkAccess: 'Enabled'" "$CORE"
check_cat acr A006 has "param acrName string" "$CORE"
check_cat acr A007 has "var acrName = toLower('acrproposalopsprodqc\${deterministicSuffix}')" "$MAIN"
check_cat acr A008 has "uniqueString(subscription().id, resourceGroupName)" "$MAIN"
check_cat acr A009 has "acrproposalopsprodqc" "$MAIN"
check_cat acr A010 has "output acrName string" "$CORE"
check_cat acr A011 has "output acrId string" "$CORE"
check_cat acr A012 not_has 'adminUserEnabled: true' "$CORE"
check_cat acr A013 not_has 'anonymousPullEnabled: true' "$CORE"
check_cat acr A014 not_has 'Microsoft.Authorization/roleAssignments' "$CORE"
check_cat acr A015 not_has 'docker push' "$CORE"
check_cat acr A016 not_has 'repository' "$CORE"
check_cat acr A017 not_has 'image' "$CORE"
check_cat acr A018 not_has 'privateEndpoints' "$CORE"
check_cat acr A019 not_has 'networkRuleSet' "$CORE"
check_cat acr A020 not_has 'webhooks' "$CORE"
check_cat acr A021 has "location: location" "$CORE"
check_cat acr A022 has "tags: tags" "$CORE"

# Monitoring contract: 22 checks.
check_cat monitoring M001 has "Microsoft.OperationalInsights/workspaces@2023-09-01" "$CORE"
check_cat monitoring M002 has "Microsoft.Insights/components@2020-02-02" "$CORE"
check_cat monitoring M003 has "param lawName string" "$CORE"
check_cat monitoring M004 has "param appInsightsName string" "$CORE"
check_cat monitoring M005 has "sku: { name: 'PerGB2018' }" "$CORE"
check_cat monitoring M006 has "retentionInDays: 30" "$CORE"
check_cat monitoring M007 has "kind: 'web'" "$CORE"
check_cat monitoring M008 has "Application_Type: 'web'" "$CORE"
check_cat monitoring M009 has "WorkspaceResourceId: law.id" "$CORE"
check_cat monitoring M010 has "var lawName = 'law-proposalops-prod-qc'" "$MAIN"
check_cat monitoring M011 has "var appInsightsName = 'appi-proposalops-prod-qc'" "$MAIN"
check_cat monitoring M012 has "output lawName string" "$CORE"
check_cat monitoring M013 has "output lawId string" "$CORE"
check_cat monitoring M014 has "output appInsightsName string" "$CORE"
check_cat monitoring M015 has "output appInsightsId string" "$CORE"
check_cat monitoring M016 count_is '^resource ' "$CORE" 6
check_cat monitoring M017 count_fixed_is "tags: tags" "$CORE" 6
check_cat monitoring M018 not_has 'retentionInDays: 7' "$CORE"
check_cat monitoring M019 not_has 'Application_Type: webapp' "$CORE"
check_cat monitoring M020 regex_not_has "WorkspaceResourceId:[[:space:]]*''" "$CORE"
check_cat monitoring M021 has "dependsOn: [budget]" "$MAIN"
check_cat monitoring M022 has "module core" "$MAIN"

# UAMI separation: 22 checks.
check_cat uami I001 has "Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31" "$CORE"
check_cat uami I002 has "param bootstrapIdentityName string" "$CORE"
check_cat uami I003 has "param migrationIdentityName string" "$CORE"
check_cat uami I004 has "resource bootstrapIdentity" "$CORE"
check_cat uami I005 has "resource migrationIdentity" "$CORE"
check_cat uami I006 has "var bootstrapIdentityName = 'id-proposalops-sql-bootstrap-prod-qc'" "$MAIN"
check_cat uami I007 has "var migrationIdentityName = 'id-proposalops-sql-migrate-prod-qc'" "$MAIN"
check_cat uami I008 has "output bootstrapIdentityName string" "$CORE"
check_cat uami I009 has "output bootstrapIdentityId string" "$CORE"
check_cat uami I010 has "output migrationIdentityName string" "$CORE"
check_cat uami I011 has "output migrationIdentityId string" "$CORE"
check_cat uami I012 count_is "Microsoft.ManagedIdentity/userAssignedIdentities" "$CORE" 2
check_cat uami I013 count_is '^resource .*Identity' "$CORE" 2
check_cat uami I014 count_fixed_is "location: location" "$CORE" 6
check_cat uami I015 count_fixed_is "tags: tags" "$CORE" 6
check_cat uami I016 not_has 'roleAssignments' "$CORE"
check_cat uami I017 not_has 'federatedIdentityCredentials' "$CORE"
check_cat uami I018 not_has 'principalId:' "$CORE"
check_cat uami I019 not_has 'clientId:' "$CORE"
check_cat uami I020 not_has 'tenantId:' "$CORE"
check_cat uami I021 not_has 'sqlPermissions' "$CORE"
check_cat uami I022 not_has 'administrator' "$CORE"

# Conditional App Service Plan: 35 checks.
check_cat plan S001 has "param deployAppServicePlan bool = false" "$MAIN"
check_cat plan S002 has "param deployAppServicePlan bool = false" "$CORE"
check_cat plan S003 has "param deployAppServicePlan = false" "$PARAMS"
check_cat plan S004 has "resource plan 'Microsoft.Web/serverfarms@2024-04-01' = if (deployAppServicePlan)" "$CORE"
check_cat plan S005 has "output planName string = deployAppServicePlan ? plan.name : ''" "$CORE"
check_cat plan S006 has "output planId string = deployAppServicePlan ? plan.id : ''" "$CORE"
check_cat plan S007 has "var planName = 'asp-proposalops-prod-qc'" "$MAIN"
check_cat plan S008 has "sku:" "$CORE"
check_cat plan S009 has "name: 'B1'" "$CORE"
check_cat plan S010 has "tier: 'Basic'" "$CORE"
check_cat plan S011 has "size: 'B1'" "$CORE"
check_cat plan S012 has "family: 'B'" "$CORE"
check_cat plan S013 has "capacity: 1" "$CORE"
check_cat plan S014 has "kind: 'linux'" "$CORE"
check_cat plan S015 has "reserved: true" "$CORE"
check_cat plan S016 not_has "Microsoft.Web/sites" "$CORE"
check_cat plan S017 not_has "Microsoft.Web/sites" "$MAIN"
check_cat plan S018 has "deployAppServicePlan: deployAppServicePlan" "$MAIN"
check_cat plan S019 has "output plannedAppServicePlanName string" "$MAIN"
check_cat plan S020 has "planName: planName" "$MAIN"
check_cat plan S021 has "planId string" "$CORE"
check_cat plan S022 has "if (deployAppServicePlan)" "$CORE"
check_cat plan S023 count_fixed_is 'deployAppServicePlan' "$MAIN" 2
check_cat plan S024 count_fixed_is 'deployAppServicePlan' "$CORE" 4
check_cat plan S025 count_fixed_is 'deployAppServicePlan' "$PARAMS" 1
check_cat plan S026 not_has "resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {" "$CORE"
check_cat plan S027 not_has 'resource site' "$CORE"
check_cat plan S028 not_has 'Microsoft.Web/sites' "$PARAMS"
check_cat plan S029 not_has 'deploymentSlots' "$CORE"
check_cat plan S030 not_has 'webjobs' "$CORE"
check_cat plan S031 not_has 'appSettings' "$CORE"
check_cat plan S032 not_has 'linuxFxVersion' "$CORE"
check_cat plan S033 not_has 'siteConfig' "$CORE"
check_cat plan S034 not_has 'az webapp' "$WORKFLOW"
check_cat plan S035 not_has 'Microsoft.Web/serverfarms' "$MAIN"

# Forbidden resources and mutations: 36 checks.
for forbidden in \
  'Microsoft.Web/sites' 'Microsoft.Sql/servers' 'Microsoft.Sql/servers/databases' \
  'Microsoft.Network/privateEndpoints' 'Microsoft.KeyVault/vaults' \
  'Microsoft.Storage/storageAccounts' 'Microsoft.ServiceBus/namespaces' \
  'Microsoft.Cache/Redis' 'Microsoft.Search/searchServices' \
  'Microsoft.CognitiveServices/accounts' 'Microsoft.App/' 'Microsoft.Compute/' \
  'Microsoft.ContainerService/' 'Microsoft.Authorization/roleAssignments' \
  'Microsoft.Network/publicIPAddresses' 'Microsoft.Network/virtualNetworkGateways' \
  'Microsoft.Network/azureFirewalls' 'Microsoft.DBforPostgreSQL/' \
  'Microsoft.Network/virtualNetworks/virtualNetworkPeerings'; do
  check_cat forbidden "F$(printf '%03d' $((checks + 1)))" no_resource_type "$forbidden"
done
check_cat forbidden F021 not_has 'Microsoft.Sql' "$MAIN"
check_cat forbidden F022 not_has 'Microsoft.Network/privateEndpoints' "$MAIN"
check_cat forbidden F023 not_has 'Microsoft.KeyVault' "$MAIN"
check_cat forbidden F024 not_has 'Microsoft.Storage' "$MAIN"
check_cat forbidden F025 not_has 'Microsoft.ServiceBus' "$MAIN"
check_cat forbidden F026 not_has 'Microsoft.Cache' "$MAIN"
check_cat forbidden F027 not_has 'Microsoft.Search' "$MAIN"
check_cat forbidden F028 not_has 'Microsoft.CognitiveServices' "$MAIN"
check_cat forbidden F029 not_has 'Microsoft.App/' "$MAIN"
check_cat forbidden F030 not_has 'Microsoft.Compute/' "$MAIN"
check_cat forbidden F031 not_has 'Microsoft.ContainerService/' "$MAIN"
check_cat forbidden F032 not_has 'Microsoft.Authorization/roleAssignments' "$MAIN"
check_cat forbidden F033 not_has 'Microsoft.DBforPostgreSQL' "$MAIN"
check_cat forbidden F034 not_has 'Microsoft.Network/publicIPAddresses' "$MAIN"
check_cat forbidden F035 not_has 'Microsoft.Network/virtualNetworkGateways' "$MAIN"
check_cat forbidden F036 not_has 'Microsoft.Network/azureFirewalls' "$MAIN"

# Secret/PII scan: 18 checks.
check_cat secrets Q001 bash -c '! grep -RqsE -- "BEGIN (RSA |OPENSSH )?PRIVATE KEY|Bearer[[:space:]]|clientSecret|accessToken|refreshToken|password[[:space:]]*=|secret[[:space:]]*=|a\\.sami\\.ibra@outlook\\.com|0e0f1028-a1f1-4b87-8cd3-449b7bdc3bc7|b27ffe53-8d31-4735-a07a-faa50c336d97" infra/azure_sql_foundation .github/workflows/azure-sql-foundation-static.yml'
check_cat secrets Q002 regex_not_has 'BEGIN[[:space:]]+(RSA[[:space:]]+|OPENSSH[[:space:]]+)?PRIVATE[[:space:]]+KEY' "$MAIN"
check_cat secrets Q003 regex_not_has 'Bearer[[:space:]]' "$MAIN"
check_cat secrets Q004 regex_not_has 'clientSecret|accessToken|refreshToken' "$MAIN"
check_cat secrets Q005 regex_not_has 'password[[:space:]]*=' "$MAIN"
check_cat secrets Q006 regex_not_has 'secret[[:space:]]*=' "$MAIN"
check_cat secrets Q007 not_has 'a.sami.ibra@outlook.com' "$PARAMS"
check_cat secrets Q008 not_has 'a.sami.ibra@outlook.com' "$MAIN"
check_cat secrets Q009 not_has 'a.sami.ibra@outlook.com' "$BUDGET"
check_cat secrets Q010 not_has 'OWNER_MONTHLY_COST_CEILING_USD' "$MAIN"
check_cat secrets Q011 not_has 'OWNER_MONTHLY_COST_CEILING_USD' "$PARAMS"
check_cat secrets Q012 not_has 'subscriptionId' "$MAIN"
check_cat secrets Q013 not_has 'tenantId' "$MAIN"
check_cat secrets Q014 not_has 'token' "$MAIN"
check_cat secrets Q015 not_has 'secret' "$CORE"
check_cat secrets Q016 not_has 'password' "$CORE"
check_cat secrets Q017 not_has 'AZURE_CREDENTIALS' "$WORKFLOW"
check_cat secrets Q018 not_has 'secrets.' "$WORKFLOW"

# Tags/provenance: 22 checks.
check_cat tags T001 has 'var resourceTags = {' "$MAIN"
check_cat tags T002 has "application: 'ProposalOps'" "$MAIN"
check_cat tags T003 has "environment: 'production'" "$MAIN"
check_cat tags T004 has "commissioningMode: 'synthetic-only'" "$MAIN"
check_cat tags T005 has "realDataAllowed: 'false'" "$MAIN"
check_cat tags T006 has "regionIntent: 'qatarcentral'" "$MAIN"
check_cat tags T007 has "managedBy: 'bicep'" "$MAIN"
check_cat tags T008 has "foundationLane: 'pre-phase5'" "$MAIN"
check_cat tags T009 has "foundationRevision: 'R2'" "$MAIN"
check_cat tags T010 has 'foundationSourceSha: foundationSourceSha' "$MAIN"
check_cat tags T011 has 'tags: resourceTags' "$MAIN"
check_cat tags T012 has 'param tags object' "$CORE"
check_cat tags T013 has 'param tags object' "$NETWORK"
check_cat tags T014 has 'param tags object' "$DNS"
check_cat tags T015 has 'tags: tags' "$CORE"
check_cat tags T016 has 'tags: tags' "$NETWORK"
check_cat tags T017 has 'tags: tags' "$DNS"
check_cat tags T018 count_fixed_is 'tags: tags' "$CORE" 6
check_cat tags T019 count_fixed_is 'tags: tags' "$NETWORK" 1
check_cat tags T020 count_fixed_is 'tags: tags' "$DNS" 1
check_cat tags T021 not_has 'email:' "$MAIN"
check_cat tags T022 not_has 'subscriptionId:' "$MAIN"

# Workflow safety/ancestry: 32 checks.
check_cat workflow W001 has 'azure-sql-foundation-prephase5-r2r1-v1' "$WORKFLOW"
check_cat workflow W002 count_fixed_is 'azure-sql-foundation-prephase5-r2r1-v1' "$WORKFLOW" 2
check_cat workflow W003 has 'actions/checkout@v4' "$WORKFLOW"
check_cat workflow W004 has 'fetch-depth: 2' "$WORKFLOW"
check_cat workflow W005 not_has 'fetch-depth: 1' "$WORKFLOW"
check_cat workflow W006 has 'az bicep install' "$WORKFLOW"
check_cat workflow W007 has 'az bicep build' "$WORKFLOW"
check_cat workflow W008 has 'Run static foundation validator' "$WORKFLOW"
check_cat workflow W009 has 'set -o pipefail' "$WORKFLOW"
check_cat workflow W010 has 'tee /tmp/azure-sql-foundation-validator.log' "$WORKFLOW"
check_cat workflow W011 has 'Preserve validator summary' "$WORKFLOW"
check_cat workflow W012 has 'if: always()' "$WORKFLOW"
check_cat workflow W013 count_fixed_is 'if: always()' "$WORKFLOW" 2
check_cat workflow W014 has 'upload-artifact@v4' "$WORKFLOW"
check_cat workflow W015 has '/tmp/azure-sql-foundation.json' "$WORKFLOW"
check_cat workflow W016 has '/tmp/azure-sql-foundation-validator.log' "$WORKFLOW"
check_cat workflow W017 has '/tmp/azure-sql-foundation-validator-summary.txt' "$WORKFLOW"
check_cat workflow W018 has 'permissions:' "$WORKFLOW"
check_cat workflow W019 has 'contents: read' "$WORKFLOW"
check_cat workflow W020 not_has 'azure/login' "$WORKFLOW"
check_cat workflow W021 not_has 'AZURE_CREDENTIALS' "$WORKFLOW"
check_cat workflow W022 not_has 'secrets.' "$WORKFLOW"
check_cat workflow W023 not_has 'az deployment' "$WORKFLOW"
check_cat workflow W024 not_has 'az group create' "$WORKFLOW"
check_cat workflow W025 not_has '--subscription' "$WORKFLOW"
check_cat workflow W026 has 'paths:' "$WORKFLOW"
check_cat workflow W027 has 'infra/azure_sql_foundation/**' "$WORKFLOW"
check_cat workflow W028 has 'scripts/azure_sql_foundation/validate_foundation.sh' "$WORKFLOW"
check_cat workflow W029 has '.github/workflows/azure-sql-foundation-static.yml' "$WORKFLOW"
check_cat workflow W030 has 'id: static-validator' "$WORKFLOW"
check_cat workflow W031 has 'shell: bash' "$WORKFLOW"
check_cat workflow W032 regex_has 'run:[[:space:]]*\|' "$WORKFLOW"

echo "CATEGORY_REPOSITORY_CHECKS=$repository_checks"
echo "CATEGORY_BOUNDARY_CHECKS=$boundary_checks"
echo "CATEGORY_R1_CHECKS=$r1_checks"
echo "CATEGORY_PHASE5_CHECKS=$phase5_checks"
echo "CATEGORY_BICEP_CHECKS=$bicep_checks"
echo "CATEGORY_BUDGET_CHECKS=$budget_checks"
echo "CATEGORY_NETWORK_CHECKS=$network_checks"
echo "CATEGORY_DNS_CHECKS=$dns_checks"
echo "CATEGORY_ACR_CHECKS=$acr_checks"
echo "CATEGORY_MONITORING_CHECKS=$monitoring_checks"
echo "CATEGORY_UAMI_CHECKS=$uami_checks"
echo "CATEGORY_PLAN_CHECKS=$plan_checks"
echo "CATEGORY_FORBIDDEN_CHECKS=$forbidden_checks"
echo "CATEGORY_SECRETS_CHECKS=$secrets_checks"
echo "CATEGORY_TAGS_CHECKS=$tags_checks"
echo "CATEGORY_WORKFLOW_CHECKS=$workflow_checks"
echo "R2_LOCAL_CHECKS=$checks"
echo "R2_LOCAL_FAIL=$failures"
if [[ "$failures" -eq 0 && "$checks" -ge 300 ]]; then
  echo 'R2_LOCAL_VALIDATION=PASS'
  exit 0
fi
echo 'R2_LOCAL_VALIDATION=FAIL'
exit 1
