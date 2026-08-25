from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.storage import (
    MockBinaryStore,
    SMBSourceConfig,
    SMBSourceStore,
    SourceCapabilities,
    SourcePage,
    StorageHealth,
    StorageLocator,
    StorageStat,
    StorageTarget,
    create_binary_store,
)
from backend.app.storage.factory import create_external_source_store
from backend.app.storage.path_policy import normalize_relative_path


class FakeSource:
    def __init__(self, files: dict[str, bytes] | None = None):
        self.files = files or {"root/report.txt": b"synthetic report"}
        self.modified = {path: "v1" for path in self.files}
        self.server_ids = {path: f"id:{path}" for path in self.files}
        self.open_count = 0
        self.mutate_on_open = False
        self.fail_names: set[str] = set()

    def _stat(self, path: str) -> StorageStat:
        if path not in self.files:
            raise FileNotFoundError(path)
        locator = StorageLocator("synthetic-source", "synthetic", path)
        return StorageStat(locator, len(self.files[path]), modified_at=self.modified[path], server_file_id=self.server_ids[path])

    def health(self):
        return StorageHealth("HEALTHY", "synthetic-source")

    def capabilities(self):
        return SourceCapabilities()

    def stat(self, locator):
        return self._stat(locator.relative_path)

    def open_read(self, locator, *, offset=None, length=None):
        self.open_count += 1
        if self.mutate_on_open:
            self.modified[locator.relative_path] = "v2"
        data = self.files[locator.relative_path]
        start = offset or 0
        return io.BytesIO(data[start:] if length is None else data[start:start + length])

    def list(self, prefix, *, cursor=None, max_entries_per_page=100):
        base = prefix.relative_path.rstrip("/") + "/"
        names = sorted(path[len(base):] for path in self.files if path.startswith(base) and "/" not in path[len(base):])
        start = 0 if cursor is None else int(cursor.removeprefix("opaque:"))
        selected = names[start:start + max_entries_per_page]
        failed = len([name for name in selected if name in self.fail_names])
        complete = start + len(selected) >= len(names) and failed == 0
        return SourcePage([self._stat(f"{prefix.relative_path.rstrip('/')}/{name}") for name in selected if name not in self.fail_names], None if complete else f"opaque:{start + len(selected)}", complete, failed, ("ENTRY_STAT_FAILED",) if failed else (), len(selected))


def secure_config(**overrides):
    values = {
        "server": "synology.invalid",
        "share": "AMEC",
        "username": "readonly",
        "password": "synthetic-only-placeholder",
    }
    values.update(overrides)
    return SMBSourceConfig(**values)


def test_external_source_is_not_a_managed_write_store():
    source = SMBSourceStore(secure_config())
    mutation_names = ("write_temporary", "finalize", "mkdirs", "cleanup_temporary", "rename", "remove", "delete", "create", "append")
    assert all(not hasattr(source, name) for name in mutation_names)
    assert not isinstance(source, MockBinaryStore)


def test_external_capabilities_are_read_only_and_secure():
    capabilities = SMBSourceStore(secure_config()).capabilities()
    assert capabilities == SourceCapabilities()
    assert capabilities.read and capabilities.stat and capabilities.list and capabilities.range_read
    assert not capabilities.write_new and not capabilities.mkdir and not capabilities.safe_finalize
    assert not capabilities.atomic_or_safe_rename_with_no_replace and not capabilities.delete and not capabilities.writeback
    assert capabilities.signing_required and capabilities.encryption_required
    assert not capabilities.anonymous and not capabilities.guest


def test_managed_factory_remains_write_capable(tmp_path: Path, monkeypatch):
    settings = SimpleNamespace(storage_provider="mock", app_env="TEST", mock_systems_root=str(tmp_path))
    monkeypatch.setattr("backend.app.storage.factory.get_settings", lambda: settings)
    managed = create_binary_store()
    assert isinstance(managed, MockBinaryStore)
    assert hasattr(managed, "write_temporary") and hasattr(managed, "finalize")


def test_external_factory_returns_dedicated_read_only_runtime(monkeypatch):
    settings = SimpleNamespace(
        smb_external_server="synthetic.invalid",
        smb_external_port=445,
        smb_external_share="synthetic",
        smb_external_root="root",
        smb_external_username="synthetic-readonly",
        smb_external_password="synthetic-placeholder",
        smb_external_auth_mode="ntlm",
        smb_external_require_signing=True,
        smb_external_require_encryption=True,
        smb_operation_timeout_seconds=1,
    )
    monkeypatch.setattr("backend.app.storage.factory.get_settings", lambda: settings)
    source = create_external_source_store()
    assert isinstance(source, SMBSourceStore)
    assert not isinstance(source, MockBinaryStore)
    assert not hasattr(source, "write_temporary")


@pytest.mark.parametrize("field,value", [
    ("require_signing", False),
    ("require_encryption", False),
    ("anonymous", True),
    ("guest", True),
    ("auth_mode", "anonymous"),
    ("operation_timeout_seconds", 0),
])
def test_external_security_contract_rejects_unsafe_configuration(field, value):
    with pytest.raises(Exception):
        SMBSourceConfig(**{**secure_config().__dict__, field: value})


@pytest.mark.parametrize("bad_path", [
    "../escape.txt", "/absolute.txt", "\\\\server\\share\\x.txt", "C:/drive.txt", "a/../../escape.txt",
    "a\x00b.txt", "a\n b.txt", "CON", "folder/PRN.txt", "folder/AUX", "folder/NUL", "folder/COM1.txt",
    "folder/LPT1", "folder/..", "", ":alternate", "\\absolute", "/rooted",
])
def test_source_paths_are_rejected_before_provider_use(bad_path):
    with pytest.raises(Exception):
        normalize_relative_path(bad_path)


def test_source_root_confinement_prefixes_only_safe_relative_paths():
    source = SMBSourceStore(secure_config(root="AMEC/Projects"))
    unc = source._unc("PRJ-001/report.pdf")
    assert unc == r"\\synology.invalid\AMEC\AMEC\Projects\PRJ-001\report.pdf"
    with pytest.raises(Exception):
        source._unc("../outside")
