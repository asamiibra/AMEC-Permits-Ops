from pathlib import Path

import pytest

from backend.app.adapters.synology.adapter import MockSynologyAdapter, StorageFaultPlan


def adapter_with_folder(tmp_path: Path) -> MockSynologyAdapter:
    root = tmp_path / "synology"
    (root / "2026" / "PRJ-001" / "01_Client").mkdir(parents=True)
    return MockSynologyAdapter(str(root))


def test_health_does_not_expose_raw_filesystem_path(tmp_path):
    health = adapter_with_folder(tmp_path).health_check()
    assert health["status"] == "OK"
    assert health["synthetic"] is True
    assert health["storage_scope"] == "SYNTHETIC_LOCAL_ROOT"
    assert "root" not in health


def test_write_readback_hash_is_atomic_and_idempotent(tmp_path):
    adapter = adapter_with_folder(tmp_path)
    first = adapter.write_readback_hash("2026/PRJ-001/01_Client", "source.txt", b"controlled source")
    second = adapter.write_readback_hash("2026/PRJ-001/01_Client", "source.txt", b"controlled source")

    assert first["verified"] is True
    assert first["read_back"] is True
    assert first["hash_match"] is True
    assert first["reused"] is False
    assert second["reused"] is True
    assert sorted(path.name for path in (tmp_path / "synology" / "2026" / "PRJ-001" / "01_Client").iterdir()) == ["source.txt"]


def test_existing_different_version_fails_closed_without_overwrite(tmp_path):
    adapter = adapter_with_folder(tmp_path)
    adapter.write_readback_hash("2026/PRJ-001/01_Client", "source.txt", b"original")

    with pytest.raises(RuntimeError, match="SOR_VERSION_IMMUTABLE"):
        adapter.write_readback_hash("2026/PRJ-001/01_Client", "source.txt", b"replacement")

    assert (tmp_path / "synology" / "2026" / "PRJ-001" / "01_Client" / "source.txt").read_bytes() == b"original"


@pytest.mark.parametrize(
    "fault, expected",
    [
        (StorageFaultPlan(fail_before_write=True), "SOR_WRITE_FAILED_BEFORE_COMMIT"),
        (StorageFaultPlan(fail_during_readback=True), "SOR_READBACK_UNAVAILABLE"),
        (StorageFaultPlan(force_hash_mismatch=True), "SOR_HASH_MISMATCH"),
    ],
)
def test_failure_modes_never_promote_a_pointer(tmp_path, fault, expected):
    adapter = adapter_with_folder(tmp_path)
    folder = tmp_path / "synology" / "2026" / "PRJ-001" / "01_Client"

    with pytest.raises((OSError, RuntimeError), match=expected):
        adapter.write_readback_hash("2026/PRJ-001/01_Client", "failure.txt", b"controlled source", fault_plan=fault)

    assert not (folder / "failure.txt").exists()
    assert not list(folder.glob(".failure.txt.pending-*"))


def test_path_and_filename_validation_are_fail_closed(tmp_path):
    adapter = adapter_with_folder(tmp_path)

    with pytest.raises(ValueError, match="INVALID_CONFIGURED_PROJECT_ROOT"):
        adapter.resolve_project_root("../escape")
    with pytest.raises(ValueError, match="INVALID_STORED_FILENAME"):
        adapter.write_readback_hash("2026/PRJ-001/01_Client", "../escape", b"data")
