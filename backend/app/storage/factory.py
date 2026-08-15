from __future__ import annotations

from pathlib import Path

from ..config.settings import get_settings, repo_root
from .errors import StorageError, StorageErrorCode
from .mock import MockBinaryStore
from .port import BinaryStorePort
from .smb import SMBConfig, SMBBinaryStore


def create_binary_store() -> BinaryStorePort:
    settings = get_settings()
    provider = settings.storage_provider.lower()
    if provider == "mock":
        if settings.app_env.upper() in {"PROD", "PRODUCTION"}:
            raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "The mock binary store is forbidden in production")
        root = Path(settings.mock_systems_root)
        if not root.is_absolute():
            root = repo_root() / root
        return MockBinaryStore(root / "synology", provider_id="mock-test", share_id="synthetic")
    if provider == "smb":
        return SMBBinaryStore(SMBConfig(
            server=settings.smb_server,
            port=settings.smb_port,
            share=settings.smb_share,
            root=settings.smb_root,
            username=settings.smb_username,
            password=settings.smb_password,
            auth_mode=settings.smb_auth_mode,
            require_signing=settings.smb_require_signing,
            require_encryption=settings.smb_require_encryption,
            connect_timeout_seconds=settings.smb_connect_timeout_seconds,
            operation_timeout_seconds=settings.smb_operation_timeout_seconds,
            environment=settings.app_env,
        ))
    raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Unsupported STORAGE_PROVIDER")

