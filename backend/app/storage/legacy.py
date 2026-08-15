"""Compatibility seam for the pre-storage-service synthetic fixture flows.

The legacy project-folder workflows predate the provider-neutral service and
still need their fixture-specific methods during the transition. They are
explicitly blocked when a real SMB provider is selected, so they can never
silently become a local-disk production fallback.
"""

import os
from pathlib import Path

from ..adapters.synology.adapter import MockSynologyAdapter
from ..config.settings import get_settings, repo_root
from .errors import StorageError, StorageErrorCode


def legacy_synthetic_adapter() -> MockSynologyAdapter:
    settings = get_settings()
    if settings.storage_provider.lower() != "mock" or settings.app_env.upper() in {"PROD", "PRODUCTION"}:
        raise StorageError(StorageErrorCode.CONFIGURATION_ERROR, "Legacy synthetic storage is unavailable when STORAGE_PROVIDER is not mock")
    root = Path(os.getenv("SYNTHETIC_SOR_ROOT", settings.mock_systems_root)) if (os.getenv("VERCEL") and settings.synthetic_only) else Path(settings.mock_systems_root)
    if not root.is_absolute():
        root = repo_root() / root
    return MockSynologyAdapter(str(root / "synology"))
