from pathlib import Path

import pytest

from backend.app.config.settings import Settings


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "infra" / "azure" / "canonical" / "main.bicep"


def _prod_with_blob(**overrides) -> Settings:
    values = {
        "app_env": "PROD",
        "database_url": "mssql+pyodbc://sql.example/proposalops?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no",
        "database_migration_url": "mssql+pyodbc://migration.example/proposalops?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no",
        "frontend_origins": "https://app.example",
        "synthetic_only": False,
        "real_data_allowed": False,
        "auth_mode": "ENTRA",
        "entra_tenant_id": "11111111-1111-4111-8111-111111111111",
        "entra_api_client_id": "22222222-2222-4222-8222-222222222222",
        "entra_web_client_id": "33333333-3333-4333-8333-333333333333",
        "entra_required_scope": "access_as_user",
        "azure_sql_auth_mode": "MANAGED_IDENTITY_ACCESS_TOKEN",
        "azure_sql_uami_client_id": "44444444-4444-4444-8444-444444444444",
        "azure_sql_uami_principal_id": "55555555-5555-4555-8555-555555555555",
        "source_intake_mode": "BRIDGE",
        "azure_direct_synology_smb": False,
        "bridge_tenant_id": "66666666-6666-4666-8666-666666666666",
        "bridge_client_id": "77777777-7777-4777-8777-777777777777",
        "bridge_audience": "22222222-2222-4222-8222-222222222222",
        "managed_artifact_store_required": True,
        "storage_provider": "azure_blob",
        "azure_blob_account_url": "https://stproposalopsproduction.blob.core.windows.net",
        "azure_blob_container": "managed-artifacts",
        "azure_blob_uami_client_id": "88888888-8888-4888-8888-888888888888",
    }
    values.update(overrides)
    return Settings(**values)


def test_prod_azure_blob_is_a_separate_managed_artifact_boundary():
    _prod_with_blob().validate_environment()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("storage_provider", "smb", "STORAGE_PROVIDER=azure_blob"),
        ("azure_blob_account_url", "https://storage.example", "exact HTTPS Azure Blob account URL"),
        ("azure_blob_uami_client_id", "not-a-guid", "AZURE_BLOB_UAMI_CLIENT_ID"),
        ("azure_blob_container", "", "AZURE_BLOB_CONTAINER"),
    ],
)
def test_prod_managed_artifact_provider_is_fail_closed(field, value, message):
    with pytest.raises(ValueError, match=message):
        _prod_with_blob(**{field: value}).validate_environment()


def test_canonical_graph_freezes_g4_topology_controls():
    source = CANONICAL.read_text(encoding="utf-8")
    required = (
        "Microsoft.Cdn/profiles@",
        "Microsoft.Network/frontdoorwebapplicationfirewallpolicies@",
        "mode: 'Prevention'",
        "Microsoft.Storage/storageAccounts@",
        "managed-artifacts",
        "Microsoft.Network/privateDnsZones@",
        "privatelink.database.windows.net",
        "privatelink.vaultcore.azure.net",
        "privatelink.blob.core.windows.net",
        "Microsoft.Insights/diagnosticSettings@",
        "requestedBackupStorageRedundancy: 'Geo'",
        "MANAGED_ARTIFACT_STORE_REQUIRED",
        "STORAGE_PROVIDER', value: 'azure_blob'",
    )
    missing = [marker for marker in required if marker not in source]
    assert not missing, missing
    assert "STORAGE_PROVIDER', value: 'smb'" not in source
    assert "AZURE_DIRECT_SYNOLOGY_SMB', value: 'true'" not in source
