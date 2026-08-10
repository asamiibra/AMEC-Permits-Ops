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
    # This is deliberately an environment/configuration value. The checked-in
    # default is a synthetic test mapping; production folders must be supplied
    # by deployment configuration and are never accepted from the browser.
    master_sor_mapping_json: str = '{"MASTER_FORM":"master-content/forms","MASTER_REPORT":"master-content/reports","MASTER_ENGINEERING_WORK":"master-content/engineering-works"}'
    master_sor_max_file_size: int = 10485760
    master_sor_allowed_extensions: str = ".pdf,.docx,.doc,.xlsx,.xls,.txt,.csv"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]

    def validate_environment(self) -> None:
        if self.app_env.upper() in {"DEV", "TEST"} and not self.synthetic_only:
            raise ValueError("DEV and TEST require SYNTHETIC_ONLY=true")
        if self.app_env.upper() != "PROD" and any(token in self.database_url.lower() for token in ("ministry", "qatar.gov", "municipality.gov")):
            raise ValueError("Non-PROD environments cannot use a production authority URL")
        if os.getenv("VERCEL") and self.app_env.upper() in {"TEST", "PROD"}:
            if not os.getenv("DATABASE_URL"):
                raise ValueError("Vercel TEST/PROD runtime requires DATABASE_URL")
            if self.database_url.lower().startswith("sqlite"):
                raise ValueError("Vercel TEST/PROD runtime requires PostgreSQL, not SQLite")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_environment()
    return settings


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
