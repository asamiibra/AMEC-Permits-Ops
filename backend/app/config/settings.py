from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "DEV"
    database_url: str = "sqlite:///./permitops.db"
    frontend_origins: str = "http://localhost:5173"
    mock_systems_root: str = "./mock-systems"
    synthetic_only: bool = True
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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_environment()
    return settings


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
