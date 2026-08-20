from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "DEV"
    database_url: str = "sqlite:///./permitops.db"
    frontend_origins: str = "http://localhost:5173"
    mock_systems_root: str = "./mock-systems"
    synthetic_only: bool = True
    real_data_allowed: bool = False
    auth_mode: str = "DEV_HEADER"
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

    def validate_environment(self) -> None:
        environment = self.app_env.upper()

        if environment in {"DEV", "TEST"} and not self.synthetic_only:
            raise ValueError("DEV and TEST require SYNTHETIC_ONLY=true")

        if environment == "AZURE-PREPROD":
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

            if not self.database_url.lower().startswith(
                "postgresql+psycopg://"
            ):
                raise ValueError(
                    "AZURE-PREPROD requires PostgreSQL via "
                    "postgresql+psycopg://"
                )

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
                raise ValueError(
                    "PROD requires PostgreSQL, not SQLite"
                )

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
