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
    synology_endpoint: str = ""
    synology_share: str = ""
    synology_secret_ref: str = ""

    # Permanent document-binary provider. MOCK is test-only; production must
    # select SMB and obtain credentials from the deployment secret manager.
    storage_provider: str = "mock"
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

    def validate_environment(self) -> None:
        environment = self.app_env.upper()

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
            origin = self.origins[0]
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
                raise ValueError(
                    "AZURE-PREPROD FRONTEND_ORIGINS must be one exact HTTPS origin"
                )
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

            if self.monitoring_mode.upper() not in {"DISABLED", "APPLICATION_INSIGHTS"}:
                raise ValueError("MONITORING_MODE must be DISABLED or APPLICATION_INSIGHTS")
            if self.monitoring_mode.upper() == "APPLICATION_INSIGHTS" and not self.applicationinsights_connection_string:
                raise ValueError("APPLICATIONINSIGHTS_CONNECTION_STRING is required when monitoring is enabled")

            # Azure A1 is the application/control plane only.
            # Direct Synology/SMB access from Azure is prohibited.
            if self.synology_mode.upper() != "SYNTHETIC":
                raise ValueError(
                    "AZURE-PREPROD requires SYNOLOGY_MODE=SYNTHETIC"
                )

            if (
                self.synology_endpoint
                or self.synology_share
                or self.synology_secret_ref
            ):
                raise ValueError(
                    "AZURE-PREPROD forbids Synology connection configuration"
                )

            if self.storage_provider.lower() != "mock":
                raise ValueError(
                    "AZURE-PREPROD requires STORAGE_PROVIDER=mock"
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

            if self.auth_mode.upper() == "DEV_HEADER":
                raise ValueError(
                    "PROD requires a configured non-development "
                    "authentication mode"
                )

            if self.database_url.lower().startswith("sqlite"):
                raise ValueError("PROD requires a server database, not SQLite")
            if self.database_url.lower().startswith("mssql+"):
                self._validate_mssql_url(self.database_url)

            if self.synology_mode.upper() != "REAL":
                raise ValueError(
                    "PROD requires SYNOLOGY_MODE=REAL"
                )

            if (
                not self.synology_endpoint
                or not self.synology_share
                or not self.synology_secret_ref
            ):
                raise ValueError(
                    "PROD requires Synology endpoint, share, "
                    "and secret reference"
                )

            if self.storage_provider.lower() != "smb":
                raise ValueError(
                    "PROD requires STORAGE_PROVIDER=smb; "
                    "mock fallback is forbidden"
                )

            if (
                not self.smb_server
                or not self.smb_share
                or not self.smb_username
            ):
                raise ValueError(
                    "PROD requires an SMB server, share and service identity"
                )

            if self.smb_auth_mode.lower() not in {
                "ntlm",
                "kerberos",
                "negotiate",
            }:
                raise ValueError(
                    "PROD requires an explicit supported "
                    "SMB authentication mode"
                )

            if (
                self.smb_auth_mode.lower() == "negotiate"
                and os.getenv(
                    "SMB_ALLOW_NEGOTIATE",
                    "false",
                ).lower()
                != "true"
            ):
                raise ValueError(
                    "SMB negotiate fallback requires explicit "
                    "SMB_ALLOW_NEGOTIATE=true"
                )

            if self.smb_server.replace(".", "").isdigit():
                raise ValueError(
                    "Kerberos-capable production SMB configuration "
                    "must use an approved hostname"
                )

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
