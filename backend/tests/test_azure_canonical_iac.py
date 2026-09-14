"""Machine-verifiable guardrails for the canonical Azure topology."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "infra" / "azure" / "canonical" / "main.bicep"
QUALIFICATION = ROOT / "infra" / "azure" / "qualification" / "main.bicep"


def _resource_block(source: str, resource_name: str, next_resource_name: str) -> str:
    start = source.index(f"resource {resource_name} ")
    end = source.index(f"resource {next_resource_name} ", start)
    return source[start:end]


def test_each_sql_client_selector_is_the_identity_attached_to_its_host():
    source = CANONICAL.read_text(encoding="utf-8")
    expected = {
        "apiApp": "apiIdentity",
        "workerApp": "workerIdentity",
        "migrationJob": "migrationIdentity",
    }

    for host, identity in expected.items():
        next_resource = {
            "apiApp": "workerApp",
            "workerApp": "migrationJob",
            "migrationJob": "sqlPrivateEndpoint",
        }[host]
        block = _resource_block(source, host, next_resource)
        assert f"userAssignedIdentities: {{ '${{{identity}.id}}': {{}} }}" in block
        assert f"AZURE_SQL_UAMI_CLIENT_ID', value: {identity}.properties.clientId" in block
        assert f"AZURE_SQL_UAMI_PRINCIPAL_ID', value: {identity}.properties.principalId" in block
        assert "value: sqlIdentity.properties.clientId" not in block
        assert "value: sqlIdentity.properties.principalId" not in block

    api = _resource_block(source, "apiApp", "workerApp")
    worker = _resource_block(source, "workerApp", "migrationJob")
    migration = _resource_block(source, "migrationJob", "sqlPrivateEndpoint")
    assert "apiIdentity.properties.clientId" in api
    assert "workerIdentity.properties.clientId" in worker
    assert "migrationIdentity.properties.clientId" in migration
    assert "apiIdentity.properties.clientId" not in migration
    assert "workerIdentity.properties.clientId" not in migration
    assert "migrationIdentity.properties.clientId" not in api
    assert "migrationIdentity.properties.clientId" not in worker


def test_sql_identity_is_control_plane_only_and_migration_is_not_attached_to_api():
    source = CANONICAL.read_text(encoding="utf-8")
    sql_server = _resource_block(source, "sqlServer", "sqlDatabase")
    api = _resource_block(source, "apiApp", "workerApp")

    assert "SQL_SERVER_CONTROL_PLANE_IDENTITY" in source
    assert "userAssignedIdentities: { '${sqlIdentity.id}': {} }" in sql_server
    assert "userAssignedIdentities: { '${migrationIdentity.id}': {} }" not in api
    assert "userAssignedIdentities: { '${apiIdentity.id}': {} }" in api


def test_acr_network_posture_is_runnable_and_authenticated():
    source = CANONICAL.read_text(encoding="utf-8")
    acr = _resource_block(source, "acr", "artifactStorage")

    assert "sku: { name: 'Standard' }" in acr
    assert "adminUserEnabled: false" in acr
    assert "anonymousPullEnabled: false" in acr
    assert "publicNetworkAccess: 'Enabled'" in acr

    # Keep this invariant generic so a future private-only change cannot
    # reintroduce Standard + disabled public access without its full path.
    if "publicNetworkAccess: 'Disabled'" in acr:
        assert "sku: { name: 'Premium' }" in acr
        assert "Microsoft.Network/privateEndpoints" in source
        assert "privatelink.azurecr.io" in source


def test_g6_qualification_topology_is_isolated_and_credentialless():
    source = QUALIFICATION.read_text(encoding="utf-8")
    required = (
        "purpose: 'G6_QUALIFICATION_ONLY'",
        "production: 'false'",
        "realDataAllowed: 'false'",
        "APP_ENV', value: 'AZURE-PREPROD'",
        "SYNTHETIC_ONLY', value: 'true'",
        "REAL_DATA_ALLOWED', value: 'false'",
        "Microsoft.App/managedEnvironments@",
        "Microsoft.App/jobs@",
        "Microsoft.Network/privateEndpoints@",
        "privatelink.database.windows.net",
        "publicNetworkAccess: 'Disabled'",
        "AZURE_SQL_UAMI_CLIENT_ID', value: runtimeIdentity.properties.clientId",
        "AZURE_SQL_UAMI_CLIENT_ID', value: migrationIdentity.properties.clientId",
        "command: ['python', '-m', 'backend.app.migrate']",
        "backend.app.g6_qualification_runtime",
        "@${runtimeImageDigest}",
        "@${migrationImageDigest}",
    )
    missing = [marker for marker in required if marker not in source]
    assert not missing, missing
    assert "APP_ENV', value: 'PROD'" not in source
    assert "SYNTHETIC_ONLY', value: 'false'" not in source
    assert "REAL_DATA_ALLOWED', value: 'true'" not in source
    assert "DATABASE_URL', value: credentiallessDatabaseUrl" in source
    assert "publicNetworkAccess: 'Enabled'" in _resource_block(source, "acr", "vnet")
    assert re.search(r"mssql\+pyodbc://[^\s'\"]*:[^\s'\"]*@", source) is None


def test_canonical_front_door_uses_private_aca_origin_without_api_cache():
    source = CANONICAL.read_text(encoding="utf-8")
    environment = _resource_block(source, "containerAppsEnvironment", "apiApp")
    origin_group = _resource_block(source, "edgeOriginGroup", "edgeOrigin")
    origin = _resource_block(source, "edgeOrigin", "edgeCustomDomain")
    route = _resource_block(source, "edgeRoute", "edgeWafPolicy")
    security = _resource_block(source, "edgeSecurityPolicy", "apiDiagnostics")

    assert "publicNetworkAccess: 'Disabled'" in environment
    assert "internal: true" in environment
    assert "probePath: '/health/ready'" in origin_group
    assert "cacheConfiguration" not in route
    assert "sharedPrivateLinkResource" in origin
    assert "privateLink: { id: containerAppsEnvironment.id }" in origin
    assert "groupId: 'managedEnvironments'" in origin
    assert "empty(edgeCustomDomainName) ? 'Enabled' : 'Disabled'" in route
    assert "empty(edgeCustomDomainName) ? [{ id: edgeEndpoint.id }] : [{ id: edgeCustomDomain.id }]" in security
    assert "param clamavImage string" in source
    assert "name: 'clamav'" in source
    assert "CONTRACT_UPLOAD_SCANNER', value: 'clamav'" in source
    assert "CONTRACT_UPLOAD_CLAMAV_HOST', value: '127.0.0.1'" in source
    assert "CONTRACT_UPLOAD_CLAMAV_PORT', value: '3310'" in source
    assert "param workerContractReconciliationEnabled bool = true" in source
    assert "WORKER_CONTRACT_RECONCILIATION_ENABLED', value: string(workerContractReconciliationEnabled)" in source
