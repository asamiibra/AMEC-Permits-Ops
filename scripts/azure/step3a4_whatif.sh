#!/usr/bin/env bash
set -euo pipefail

SUB_NAME="ProposalOps Preprod QC"
SUB_ID="61080f8b-16cb-4abc-bb8c-5d8e59ab15bf"
TENANT_ID="b27ffe53-8d31-4735-a07a-faa50c336d97"
LOCATION="qatarcentral"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARAMETER_FILE="$ROOT_DIR/infra/azure/preprod.bicepparam"

echo "SUBSCRIPTION_NAME=$SUB_NAME"
echo "SUBSCRIPTION_ID=$SUB_ID"
echo "TENANT_ID=$TENANT_ID"
echo "LOCATION=$LOCATION"
echo "AZURE_RESOURCES_CREATED=false"
echo "AZURE_RESOURCES_UPDATED=false"
echo "AZURE_RESOURCES_DELETED=false"
echo "PROVIDERS_REGISTERED_BY_THIS_STEP=false"

account_json="$(az account show --subscription "$SUB_ID" --output json)"
ACCOUNT_SUBSCRIPTION_ID="$(printf '%s' "$account_json" | jq -r '.id')"
ACCOUNT_TENANT_ID="$(printf '%s' "$account_json" | jq -r '.tenantId')"
test "$ACCOUNT_SUBSCRIPTION_ID" = "$SUB_ID"
test "$ACCOUNT_TENANT_ID" = "$TENANT_ID"
echo "ACCOUNT_SUBSCRIPTION_ID=$ACCOUNT_SUBSCRIPTION_ID"
echo "ACCOUNT_TENANT_ID=$ACCOUNT_TENANT_ID"

az version --output json
az bicep version

AZ_CLI_VERSION="$(az version --query '"azure-cli"' --output tsv)"
echo "AZURE_CLI_VERSION=$AZ_CLI_VERSION"
if ! python3 - "$AZ_CLI_VERSION" <<'PY'
import sys

try:
    parts = sys.argv[1].split('.')
    version = tuple(int(part) for part in parts[:3])
except (ValueError, IndexError):
    raise SystemExit(2)

if len(version) < 3:
    version = version + (0,) * (3 - len(version))

raise SystemExit(0 if version >= (2, 76, 0) else 1)
PY
then
  echo "STEP_3A_4B_STATUS=ENV_BLOCKED_AZURE_CLI_TOO_OLD"
  exit 1
fi
echo "AZURE_CLI_VALIDATION_LEVEL_SUPPORT=PASS"

echo "APP_SERVICE_B1_QATAR="
az appservice list-locations \
  --sku B1 \
  --linux-workers-enabled true \
  --subscription "$SUB_ID" \
  --output json \
  | jq --arg location "$LOCATION" '[.[] | select(.name == $location)]'

providers=(
  Microsoft.Resources
  Microsoft.Network
  Microsoft.Web
  Microsoft.ContainerRegistry
  Microsoft.KeyVault
  Microsoft.OperationalInsights
  Microsoft.Insights
  Microsoft.DBforPostgreSQL
)

all_foundation_registered=true
for namespace in "${providers[@]}"; do
  state="$(az provider show \
    --namespace "$namespace" \
    --subscription "$SUB_ID" \
    --query registrationState \
    --output tsv 2>/dev/null || true)"
  state="${state:-UNKNOWN}"
  echo "PROVIDER_STATE_${namespace//./_}=$state"
  if [ "$state" != "Registered" ]; then
    all_foundation_registered=false
  fi
done

echo "WHATIF_TEMPLATE_EXECUTED=true"
az deployment sub what-if \
  --name proposalops-step3a4-template \
  --location "$LOCATION" \
  --parameters "$PARAMETER_FILE" \
  --validation-level Template \
  --no-pretty-print \
  --subscription "$SUB_ID"

if [ "$all_foundation_registered" = true ]; then
  echo "WHATIF_PROVIDER_NORBAC=EXECUTED"
  az deployment sub what-if \
    --name proposalops-step3a4-provider-norbac \
    --location "$LOCATION" \
    --parameters "$PARAMETER_FILE" \
    --validation-level ProviderNoRbac \
    --no-pretty-print \
    --subscription "$SUB_ID"
else
  echo "WHATIF_PROVIDER_NORBAC=ENV_BLOCKED_UNREGISTERED_PROVIDER"
fi
