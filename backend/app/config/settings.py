from functools import lru_cache
import os
from pathlib import Path
from uuid import UUID
from urllib.parse import parse_qs, urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "DEV"
    database_url: str = "sqlite:///./permitops.db"
    database_migration_url: str = ""
    azure_sql_auth_mode: str = "DIRECT_ODBC_MSI"
    azure_sql_uami_client_id: str = ""
    azure_sql_uami_principal_id: str = ""
    frontend_origins: str = "http://localhost:5173"
    mock_systems_root: str = "./mock-systems"
    synthetic_only: bool = True
    real_data_allowed: bool = False
    auth_mode: str = "DEV_HEADER"

    # Microsoft Entra ID configuration for Azure preprod.
    # These are identifiers only; no client secret is stored in the web app.
    entra_tenant_id: str = ""
    entra_api_client_id: str = ""
    entra_web_client_id: str = ""
    entra_required_scope: str = "access_as_user"

    synology_mode: str = "SYNTHETIC"
    source_intake_mode: str = "LOCAL"
    bridge_tenant_id: str = ""
    bridge_client_id: str = ""
    bridge_audience: str = ""
    bridge_required_role: str = "proposalops.source-intake"
    bridge_package_signing_public_key: str = ""
    bridge_allowed_source_identities: str = "QATAR_SYNOLOGY_SYNTHETIC_FIXTURE"
    bridge_allowed_source_path_prefixes: str = "synthetic://qatar-synology/"
    bridge_max_payload_bytes: int = 1048576
    synology_endpoint: str = ""
    synology_share: str = ""
    synology_secret_ref: str = ""
    # Source intake is bridge-owned; the Azure application never reaches
    # Synology directly, including during production canary operation.
    azure_direct_synology_smb: bool = False

    # Permanent document-binary provider. MOCK is test-only; production uses
    # the private Azure Blob managed-artifact provider or an explicitly
    # approved future provider.
    storage_provider: str = "mock"
    managed_artifact_store_required: bool = False
    azure_blob_account_url: str = ""
    azure_blob_container: str = "managed-artifacts"
    azure_blob_uami_client_id: str = ""
    smb_server: str = ""
    smb_port: int = 445
    smb_share: str = ""
    smb_root: str = ""
    smb_username: str = ""
    smb_password: str = ""
    smb_auth_mode: str = "ntlm"
    smb_require_signing: bool = False
    smb_require_encryption: bool = False
    smb_connect_timeout_seconds: float = 10
    smb_operation_timeout_seconds: float = 60

    # Optional owner/external source root. It is intentionally separate from
    # the managed root and is never used as a write destination.
    smb_external_server: str = ""
    smb_external_port: int = 445
    smb_external_share: str = ""
    smb_external_root: str = ""
    smb_external_username: str = ""
    smb_external_password: str = ""
    smb_external_auth_mode: str = "ntlm"
    smb_external_require_signing: bool = False
    smb_external_require_encryption: bool = False

    # This is deliberately an environment/configuration value. The checked-in
    # default is a synthetic test mapping; production folders must be supplied
    # by deployment configuration and are never accepted from the browser.
    master_sor_mapping_json: str = (
        '{"MASTER_FORM":"master-content/forms",'
        '"MASTER_REPORT":"master-content/reports",'
        '"MASTER_ENGINEERING_WORK":"master-content/engineering-works"}'
    )
    master_sor_max_file_size: int = 10485760
    master_sor_allowed_extensions: str = (
        ".pdf,.docx,.doc,.xlsx,.xls,.txt,.csv,.jpg,.jpeg,.png"
    )
    log_level: str = "INFO"
    monitoring_mode: str = "DISABLED"
    applicationinsights_connection_string: str = ""

    # AI-D2/D3 has two independent deployment gates. The feature may be
    # present in the product while external inference remains disabled until
    # the separately governed D4 commissioning record is present.
    ai_feature_enabled: bool = False
    ai_external_inference_enabled: bool = False
    ai_d4_commissioning_id: str = ""
    ai_real_content_allowed: bool = False
    ai_azure_openai_endpoint: str = ""
    ai_azure_openai_deployment: str = "d3-gpt54mini-20260317"
    ai_azure_openai_expected_model: str = "gpt-5.4-mini"
    ai_azure_openai_expected_version: str = "2026-03-17"
    ai_azure_openai_region: str = "eastus"
    ai_azure_openai_deployment_type: str = "DataZoneStandard"
    ai_uami_client_id: str = ""
    ai_uami_principal_id: str = ""
    ai_azure_tenant_id: str = ""
    ai_identity_timeout_seconds: float = 5
    ai_provider_connect_timeout_seconds: float = 5
    ai_provider_read_timeout_seconds: float = 60
    ai_provider_write_timeout_seconds: float = 10
    ai_max_context_items: int = 8
    ai_max_context_utf8_bytes: int = 16384
    ai_max_input_token_upper_bound: int = 0
    ai_max_output_tokens: int = 0
    ai_max_requests_per_user_per_minute: int = 0
    ai_max_requests_per_user_per_hour: int = 0
    ai_max_requests_per_project_per_hour: int = 0
    ai_max_requests_global_per_hour: int = 0
    ai_max_estimated_cost_usd_per_request: float = 0.0
    ai_max_estimated_cost_usd_per_day: float = 0.0
    ai_input_price_usd_per_1m_tokens: float = 0.0
    ai_output_price_usd_per_1m_tokens: float = 0.0
    ai_pricing_source_reference: str = ""
    ai_d3_synthetic_project_ids: str = ""

    @property
    def ai_d3_project_ids(self) -> frozenset[str]:
        return frozenset(item.strip() for item in self.ai_d3_synthetic_project_ids.split(",") if item.strip())

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.frontend_origins.split(",")
            if item.strip()
        ]

    @staticmethod
    def _require_guid(value: str, setting_name: str) -> None:
        try:
            UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(
                f"AZURE-PREPROD requires {setting_name} to be a valid GUID"
            ) from exc

    @staticmethod
    def _validate_mssql_url(database_url: str, setting_name: str = "DATABASE_URL") -> None:
        parsed = urlsplit(database_url)
        if not parsed.scheme.lower().startswith("mssql+"):
            raise ValueError(
                f"{setting_name} must use mssql+pyodbc:// for Azure SQL"
            )
        query = {key.lower(): value[-1] for key, value in parse_qs(parsed.query, keep_blank_values=True).items()}
        if query.get("encrypt", "").lower() != "yes":
            raise ValueError(f"{setting_name} requires Encrypt=yes")
        if query.get("trustservercertificate", "").lower() != "no":
            raise ValueError(f"{setting_name} requires TrustServerCertificate=no")

    @staticmethod
    def _validate_credential_free_url(database_url: str, setting_name: str) -> None:
        parsed = urlsplit(database_url)
        forbidden_auth_keywords = (
            "uid=",
            "pwd=",
            "authentication=",
            "trusted_connection=",
        )
        if (
            parsed.username
            or parsed.password
            or any(keyword in database_url.lower() for keyword in forbidden_auth_keywords)
        ):
            raise ValueError(
                f"{setting_name} forbids URL credentials, UID, PWD, Authentication, "
                "and Trusted_Connection"
            )

    def _validate_ai_d4_lock(self) -> None:
        if self.ai_external_inference_enabled and not self.ai_feature_enabled:
            raise ValueError("AI_EXTERNAL_INFERENCE_ENABLED requires AI_FEATURE_ENABLED=true")
        if not self.ai_external_inference_enabled:
            return
        if not self.ai_d4_commissioning_id.strip():
            raise ValueError("AI_D4_COMMISSIONING_ID is required when external inference is enabled")
        if not self.synthetic_only or self.real_data_allowed or self.ai_real_content_allowed:
            raise ValueError("D4 external inference requires synthetic-only and real-content=false")
        for setting_name, value in (
            ("AI_UAMI_CLIENT_ID", self.ai_uami_client_id),
            ("AI_UAMI_PRINCIPAL_ID", self.ai_uami_principal_id),
            ("AI_AZURE_TENANT_ID", self.ai_azure_tenant_id),
        ):
            if not value:
                raise ValueError(f"{setting_name} is required when external inference is enabled")
            self._require_guid(value, setting_name)
        expected_binding = {
            "AI_AZURE_OPENAI_DEPLOYMENT": "d3-gpt54mini-20260317",
            "AI_AZURE_OPENAI_EXPECTED_MODEL": "gpt-5.4-mini",
            "AI_AZURE_OPENAI_EXPECTED_VERSION": "2026-03-17",
            "AI_AZURE_OPENAI_REGION": "eastus",
            "AI_AZURE_OPENAI_DEPLOYMENT_TYPE": "DataZoneStandard",
        }
        for setting_name, expected in expected_binding.items():
            if getattr(self, setting_name.lower()) != expected:
                raise ValueError(f"{setting_name} must equal the D4 commissioned binding {expected}")
        from ..ai.runtime_binding import AIRuntimeBinding

        AIRuntimeBinding.from_settings(self).validate()
        for setting_name, value in (
            ("AI_MAX_INPUT_TOKEN_UPPER_BOUND", self.ai_max_input_token_upper_bound),
            ("AI_MAX_OUTPUT_TOKENS", self.ai_max_output_tokens),
            ("AI_MAX_REQUESTS_PER_USER_PER_MINUTE", self.ai_max_requests_per_user_per_minute),
            ("AI_MAX_REQUESTS_PER_USER_PER_HOUR", self.ai_max_requests_per_user_per_hour),
            ("AI_MAX_REQUESTS_PER_PROJECT_PER_HOUR", self.ai_max_requests_per_project_per_hour),
            ("AI_MAX_REQUESTS_GLOBAL_PER_HOUR", self.ai_max_requests_global_per_hour),
            ("AI_MAX_ESTIMATED_COST_USD_PER_REQUEST", self.ai_max_estimated_cost_usd_per_request),
            ("AI_MAX_ESTIMATED_COST_USD_PER_DAY", self.ai_max_estimated_cost_usd_per_day),
            ("AI_INPUT_PRICE_USD_PER_1M_TOKENS", self.ai_input_price_usd_per_1m_tokens),
            ("AI_OUTPUT_PRICE_USD_PER_1M_TOKENS", self.ai_output_price_usd_per_1m_tokens),
        ):
            if value <= 0:
                raise ValueError(f"{setting_name} must be greater than zero for D4")
        if not self.ai_pricing_source_reference.strip():
            raise ValueError("AI_PRICING_SOURCE_REFERENCE is required for D4")
        if not self.ai_d3_project_ids:
            raise ValueError("AI_D3_SYNTHETIC_PROJECT_IDS is required for D4")
        if self.ai_uami_client_id.lower() == self.azure_sql_uami_client_id.lower() and self.azure_sql_uami_client_id:
            raise ValueError("AI and SQL managed identities must be separate")
        if self.ai_uami_principal_id.lower() == self.azure_sql_uami_principal_id.lower() and self.azure_sql_uami_principal_id:
            raise ValueError("AI and SQL managed identities must be separate")
        if self.ai_max_context_items != 8 or self.ai_max_context_utf8_bytes != 16384:
            raise ValueError("D4 context bounds are frozen")

    @staticmethod
    def _validate_exact_https_origin(origin: str, setting_name: str) -> None:
        parsed_origin = urlsplit(origin)
        if (
            parsed_origin.scheme != "https"
            or not parsed_origin.netloc
            or parsed_origin.path not in {"", "/"}
            or parsed_origin.query
            or parsed_origin.fragment
            or "*" in origin
            or parsed_origin.hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            raise ValueError(f"{setting_name} must be one exact HTTPS origin")

    def _validate_bridge_contract(self) -> None:
        if self.source_intake_mode.upper() != "BRIDGE":
            raise ValueError("PROD requires SOURCE_INTAKE_MODE=BRIDGE")
        if self.azure_direct_synology_smb:
            raise ValueError("PROD bridge intake requires AZURE_DIRECT_SYNOLOGY_SMB=false")
        for setting_name, value in (
            ("BRIDGE_TENANT_ID", self.bridge_tenant_id),
            ("BRIDGE_CLIENT_ID", self.bridge_client_id),
        ):
            if not value:
                raise ValueError(f"{setting_name} is required for bridge intake")
            self._require_guid(value, setting_name)
        if not self.bridge_audience.strip():
            raise ValueError("BRIDGE_AUDIENCE is required for bridge intake")
        if self.bridge_audience.strip() != self.entra_api_client_id.strip():
            raise ValueError("BRIDGE_AUDIENCE must equal ENTRA_API_CLIENT_ID")
        if not self.bridge_required_role.strip():
            raise ValueError("BRIDGE_REQUIRED_ROLE is required for bridge intake")

        authoritative_source_fields = (
            ("SYNOLOGY_ENDPOINT", self.synology_endpoint),
            ("SYNOLOGY_SHARE", self.synology_share),
            ("SYNOLOGY_SECRET_REF", self.synology_secret_ref),
            ("SMB_EXTERNAL_SERVER", self.smb_external_server),
            ("SMB_EXTERNAL_SHARE", self.smb_external_share),
            ("SMB_EXTERNAL_USERNAME", self.smb_external_username),
            ("SMB_EXTERNAL_PASSWORD", self.smb_external_password),
        )
        configured = [name for name, value in authoritative_source_fields if value]
        if configured:
            raise ValueError(
                "PROD bridge intake forbids Azure-side authoritative source credentials: "
                + ", ".join(configured)
            )

    def validate_environment(self) -> None:
        environment = self.app_env.upper()

        self._validate_ai_d4_lock()

        allowed_environments = {
            "DEV",
            "TEST",
            "AZURE-PREPROD",
            "PROD",
        }

        if environment not in allowed_environments:
            raise ValueError(
                "APP_ENV must be one of DEV, TEST, azure-preprod, or PROD"
            )

        if environment in {"DEV", "TEST"} and not self.synthetic_only:
            raise ValueError(
                "DEV and TEST require SYNTHETIC_ONLY=true"
            )

        if environment == "AZURE-PREPROD":
            if os.getenv("FRONTEND_ORIGINS") is None:
                raise ValueError(
                    "AZURE-PREPROD requires explicit FRONTEND_ORIGINS"
                )
            if len(self.origins) != 1:
                raise ValueError(
                    "AZURE-PREPROD requires exactly one FRONTEND_ORIGINS value"
                )
            self._validate_exact_https_origin(self.origins[0], "AZURE-PREPROD FRONTEND_ORIGINS")
            if not self.synthetic_only:
                raise ValueError(
                    "AZURE-PREPROD requires SYNTHETIC_ONLY=true"
                )

            if self.real_data_allowed:
                raise ValueError(
                    "AZURE-PREPROD requires REAL_DATA_ALLOWED=false"
                )

            if self.auth_mode.upper() != "ENTRA":
                raise ValueError(
                    "AZURE-PREPROD requires AUTH_MODE=ENTRA"
                )

            if not self.entra_tenant_id:
                raise ValueError(
                    "AZURE-PREPROD requires ENTRA_TENANT_ID"
                )

            self._require_guid(
                self.entra_tenant_id,
                "ENTRA_TENANT_ID",
            )

            if not self.entra_api_client_id:
                raise ValueError(
                    "AZURE-PREPROD requires ENTRA_API_CLIENT_ID"
                )

            self._require_guid(
                self.entra_api_client_id,
                "ENTRA_API_CLIENT_ID",
            )

            if not self.entra_web_client_id:
                raise ValueError(
                    "AZURE-PREPROD requires ENTRA_WEB_CLIENT_ID"
                )

            self._require_guid(
                self.entra_web_client_id,
                "ENTRA_WEB_CLIENT_ID",
            )

            if (
                self.entra_api_client_id.lower()
                == self.entra_web_client_id.lower()
            ):
                raise ValueError(
                    "AZURE-PREPROD requires separate Entra "
                    "API and web client IDs"
                )

            if self.entra_required_scope != "access_as_user":
                raise ValueError(
                    "AZURE-PREPROD requires "
                    "ENTRA_REQUIRED_SCOPE=access_as_user"
                )

            if not self.database_url.lower().startswith("mssql+pyodbc://"):
                raise ValueError(
                    "AZURE-PREPROD requires mssql+pyodbc:// for Azure SQL"
                )
            self._validate_mssql_url(self.database_url)

            if self.azure_sql_auth_mode.upper() != "MANAGED_IDENTITY_ACCESS_TOKEN":
                raise ValueError(
                    "AZURE-PREPROD requires "
                    "AZURE_SQL_AUTH_MODE=MANAGED_IDENTITY_ACCESS_TOKEN"
                )
            for setting_name, value in (
                ("AZURE_SQL_UAMI_CLIENT_ID", self.azure_sql_uami_client_id),
                ("AZURE_SQL_UAMI_PRINCIPAL_ID", self.azure_sql_uami_principal_id),
            ):
                if not value:
                    raise ValueError(f"AZURE-PREPROD requires {setting_name}")
                self._require_guid(value, setting_name)
            self._validate_credential_free_url(self.database_url, "DATABASE_URL")

            if not self.database_migration_url.strip():
                raise ValueError("AZURE-PREPROD requires DATABASE_MIGRATION_URL")
            if not self.database_migration_url.lower().startswith("mssql+pyodbc://"):
                raise ValueError(
                    "AZURE-PREPROD DATABASE_MIGRATION_URL must use mssql+pyodbc://"
                )
            self._validate_mssql_url(
                self.database_migration_url,
                "DATABASE_MIGRATION_URL",
            )
            self._validate_credential_free_url(
                self.database_migration_url,
                "DATABASE_MIGRATION_URL",
            )

            if self.monitoring_mode.upper() not in {"DISABLED", "APPLICATION_INSIGHTS"}:
                raise ValueError("MONITORING_MODE must be DISABLED or APPLICATION_INSIGHTS")
            if self.monitoring_mode.upper() == "APPLICATION_INSIGHTS" and not self.applicationinsights_connection_string:
                raise ValueError("APPLICATIONINSIGHTS_CONNECTION_STRING is required when monitoring is enabled")

            # Azure preproduction uses the same bridge contract as production,
            # but only synthetic bridge fixtures are permitted at this gate.
            if self.synology_mode.upper() != "BRIDGE":
                raise ValueError("AZURE-PREPROD requires SYNOLOGY_MODE=BRIDGE")

            if self.azure_direct_synology_smb:
                raise ValueError("AZURE-PREPROD requires AZURE_DIRECT_SYNOLOGY_SMB=false")

            self._validate_bridge_contract()

            if self.managed_artifact_store_required:
                if self.storage_provider.lower() != "azure_blob":
                    raise ValueError(
                        "AZURE-PREPROD requires STORAGE_PROVIDER=azure_blob "
                        "when managed artifact storage is required"
                    )
                blob_url = urlsplit(self.azure_blob_account_url)
                if (
                    blob_url.scheme != "https"
                    or not blob_url.hostname
                    or not blob_url.hostname.endswith(".blob.core.windows.net")
                    or blob_url.path not in {"", "/"}
                    or blob_url.query
                    or blob_url.fragment
                ):
                    raise ValueError(
                        "AZURE-PREPROD requires an exact HTTPS Azure Blob account URL"
                    )
                if not self.azure_blob_container.strip():
                    raise ValueError(
                        "AZURE-PREPROD requires AZURE_BLOB_CONTAINER"
                    )
                if not self.azure_blob_uami_client_id:
                    raise ValueError(
                        "AZURE-PREPROD requires AZURE_BLOB_UAMI_CLIENT_ID"
                    )
                self._require_guid(
                    self.azure_blob_uami_client_id,
                    "AZURE_BLOB_UAMI_CLIENT_ID",
                )

            if (
                self.smb_server
                or self.smb_share
                or self.smb_username
                or self.smb_password
            ):
                raise ValueError(
                    "AZURE-PREPROD forbids SMB connection configuration"
                )

            if (
                self.smb_external_server
                or self.smb_external_share
                or self.smb_external_username
                or self.smb_external_password
            ):
                raise ValueError(
                    "AZURE-PREPROD forbids external SMB "
                    "connection configuration"
                )

        if environment == "PROD":
            if self.synthetic_only:
                raise ValueError(
                    "PROD requires SYNTHETIC_ONLY=false"
                )

            if self.auth_mode.upper() != "ENTRA":
                raise ValueError("PROD requires AUTH_MODE=ENTRA")
            if len(self.origins) != 1:
                raise ValueError("PROD requires exactly one FRONTEND_ORIGINS value")
            self._validate_exact_https_origin(self.origins[0], "PROD FRONTEND_ORIGINS")
            for setting_name, value in (
                ("ENTRA_TENANT_ID", self.entra_tenant_id),
                ("ENTRA_API_CLIENT_ID", self.entra_api_client_id),
                ("ENTRA_WEB_CLIENT_ID", self.entra_web_client_id),
            ):
                if not value:
                    raise ValueError(f"PROD requires {setting_name}")
                self._require_guid(value, setting_name)
            if self.entra_api_client_id.lower() == self.entra_web_client_id.lower():
                raise ValueError("PROD requires separate Entra API and web client IDs")
            if self.entra_required_scope != "access_as_user":
                raise ValueError("PROD requires ENTRA_REQUIRED_SCOPE=access_as_user")

            self._validate_bridge_contract()

            if not self.database_url.lower().startswith("mssql+pyodbc://"):
                raise ValueError("PROD requires mssql+pyodbc:// for Azure SQL")
            self._validate_mssql_url(self.database_url)
            if self.azure_sql_auth_mode.upper() != "MANAGED_IDENTITY_ACCESS_TOKEN":
                raise ValueError("PROD requires AZURE_SQL_AUTH_MODE=MANAGED_IDENTITY_ACCESS_TOKEN")
            for setting_name, value in (
                ("AZURE_SQL_UAMI_CLIENT_ID", self.azure_sql_uami_client_id),
                ("AZURE_SQL_UAMI_PRINCIPAL_ID", self.azure_sql_uami_principal_id),
            ):
                if not value:
                    raise ValueError(f"PROD requires {setting_name}")
                self._require_guid(value, setting_name)
            if not self.database_migration_url.strip():
                raise ValueError("PROD requires DATABASE_MIGRATION_URL")
            if not self.database_migration_url.lower().startswith("mssql+pyodbc://"):
                raise ValueError("PROD DATABASE_MIGRATION_URL must use mssql+pyodbc://")
            self._validate_mssql_url(self.database_migration_url, "DATABASE_MIGRATION_URL")

            self._validate_credential_free_url(self.database_url, "DATABASE_URL")
            self._validate_credential_free_url(self.database_migration_url, "DATABASE_MIGRATION_URL")

            if self.managed_artifact_store_required:
                if self.storage_provider.lower() != "azure_blob":
                    raise ValueError(
                        "PROD requires STORAGE_PROVIDER=azure_blob when managed artifact storage is launch-required"
                    )
                blob_url = urlsplit(self.azure_blob_account_url)
                if (
                    blob_url.scheme != "https"
                    or not blob_url.hostname
                    or not blob_url.hostname.endswith(".blob.core.windows.net")
                    or blob_url.path not in {"", "/"}
                    or blob_url.query
                    or blob_url.fragment
                ):
                    raise ValueError(
                        "PROD requires an exact HTTPS Azure Blob account URL when managed artifact storage is launch-required"
                    )
                if not self.azure_blob_container.strip():
                    raise ValueError("PROD requires AZURE_BLOB_CONTAINER when managed artifact storage is launch-required")
                if not self.azure_blob_uami_client_id:
                    raise ValueError("PROD requires AZURE_BLOB_UAMI_CLIENT_ID when managed artifact storage is launch-required")
                self._require_guid(self.azure_blob_uami_client_id, "AZURE_BLOB_UAMI_CLIENT_ID")

        if environment != "PROD" and any(
            token in self.database_url.lower()
            for token in (
                "ministry",
                "qatar.gov",
                "municipality.gov",
            )
        ):
            raise ValueError(
                "Non-PROD environments cannot use a production authority URL"
            )

        if os.getenv("VERCEL") and environment in {"TEST", "PROD"}:
            if not os.getenv("DATABASE_URL"):
                raise ValueError(
                    "Vercel TEST/PROD runtime requires DATABASE_URL"
                )

            if self.database_url.lower().startswith("sqlite"):
                raise ValueError(
                    "Vercel TEST/PROD runtime requires PostgreSQL, not SQLite"
                )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_environment()
    return settings


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
