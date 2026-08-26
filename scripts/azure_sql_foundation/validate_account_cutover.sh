#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# Account identifiers that must never be embedded in reusable Azure SQL foundation
# IaC. This deny-list intentionally grows across account cutovers; retired values are
# retained so a future copy/paste cannot silently reactivate them.
DENIED_LITERALS=(
  '61080f8b-16cb-4abc-bb8c-5d8e59ab15bf'  # retired ProposalOps subscription
  '0e0f1028-a1f1-4b87-8cd3-449b7bdc3bc7'  # historical test subscription
  'b27ffe53-8d31-4735-a07a-faa50c336d97'  # retired tenant
  '2bea2887-9255-4273-a73f-43ae33813455'  # current subscription; runtime binding only
  '2a82f16d-87fa-4036-97a9-17d94060eddd'  # current tenant; runtime binding only
  'a.sami.ibra@outlook.com'                # retired owner email
  'a.sami.ibra@gmail.com'                  # current owner email; deployment-time input only
  'ProposalOps Preprod QC'                 # retired display name
  'AMEC Subscription'                      # current display name; not IaC identity
)

SCAN_PATHS=(
  infra/azure_sql_foundation
  .github/workflows/azure-sql-foundation-static.yml
)

failures=0
for literal in "${DENIED_LITERALS[@]}"; do
  if grep -RFn -- "$literal" "${SCAN_PATHS[@]}"; then
    echo "FAIL account-specific literal found in reusable foundation source" >&2
    failures=$((failures + 1))
  fi
done

# The historical validator is allowed to contain retired fingerprints because they
# are deny-list controls. Prove the original controls are still present.
VALIDATOR='scripts/azure_sql_foundation/validate_foundation.sh'
for literal in \
  '0e0f1028-a1f1-4b87-8cd3-449b7bdc3bc7' \
  'b27ffe53-8d31-4735-a07a-faa50c336d97' \
  'a.sami.ibra@outlook.com'; do
  grep -Fq -- "$literal" "$VALIDATOR" || {
    echo "FAIL retired deny-list fingerprint disappeared from historical validator: $literal" >&2
    failures=$((failures + 1))
  }
done

# Current account values must be bound outside reusable foundation IaC. The new
# account cutover branch deliberately does not write subscription/tenant/email into
# Bicep, tags, workflow, or parameter examples.
for literal in \
  '2bea2887-9255-4273-a73f-43ae33813455' \
  '2a82f16d-87fa-4036-97a9-17d94060eddd' \
  'a.sami.ibra@gmail.com' \
  'AMEC Subscription'; do
  if grep -RFn -- "$literal" infra/azure_sql_foundation .github/workflows/azure-sql-foundation-static.yml; then
    echo "FAIL current account identifier leaked into reusable foundation: $literal" >&2
    failures=$((failures + 1))
  fi
done

# Canonical topology must survive the account cutover unchanged.
grep -Fq "param location string = 'qatarcentral'" infra/azure_sql_foundation/main.bicep
grep -Fq "param resourceGroupName string = 'rg-proposalops-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var vnetName = 'vnet-proposalops-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var appServiceSubnetName = 'snet-appservice-integration'" infra/azure_sql_foundation/main.bicep
grep -Fq "var sqlPrivateEndpointSubnetName = 'snet-sql-private-endpoints'" infra/azure_sql_foundation/main.bicep
grep -Fq "var privateDnsZoneName = 'privatelink.database.windows.net'" infra/azure_sql_foundation/main.bicep
grep -Fq "var privateDnsLinkName = 'link-proposalops-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var lawName = 'law-proposalops-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var appInsightsName = 'appi-proposalops-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var planName = 'asp-proposalops-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var bootstrapIdentityName = 'id-proposalops-sql-bootstrap-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "var migrationIdentityName = 'id-proposalops-sql-migrate-prod-qc'" infra/azure_sql_foundation/main.bicep
grep -Fq "addressPrefixes: ['10.42.0.0/16']" infra/azure_sql_foundation/modules/network.bicep
grep -Fq "addressPrefix: '10.42.0.0/26'" infra/azure_sql_foundation/modules/network.bicep
grep -Fq "addressPrefix: '10.42.1.0/28'" infra/azure_sql_foundation/modules/network.bicep
grep -Fq "serviceName: 'Microsoft.Web/serverFarms'" infra/azure_sql_foundation/modules/network.bicep
grep -Fq "registrationEnabled: false" infra/azure_sql_foundation/modules/private_dns.bicep
grep -Fq "location: 'global'" infra/azure_sql_foundation/modules/private_dns.bicep

# The account cutover itself is read-only with respect to Azure/Entra.
if grep -RInE 'azure/login|az[[:space:]]+login|az[[:space:]]+account[[:space:]]+set|az[[:space:]]+deployment.+create|az[[:space:]]+group[[:space:]]+create|az[[:space:]]+provider[[:space:]]+register' \
  .github/workflows/azure-account-cutover-foundation-validation.yml \
  scripts/azure_sql_foundation/validate_account_cutover.sh; then
  echo 'FAIL mutation/login command found in cutover validation lane' >&2
  failures=$((failures + 1))
fi

printf 'ACCOUNT_IDENTIFIERS_DENIED=%s\n' "${#DENIED_LITERALS[@]}"
printf 'ACCOUNT_CUTOVER_FAILURE_COUNT=%s\n' "$failures"
if [[ "$failures" -ne 0 ]]; then
  echo 'AZURE_FOUNDATION_ACCOUNT_CUTOVER=FAIL'
  exit 1
fi

echo 'AZURE_FOUNDATION_ACCOUNT_CUTOVER=PASS'
