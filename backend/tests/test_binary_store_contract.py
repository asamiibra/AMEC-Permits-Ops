"""Reusable BinaryStorePort contract suite.

Run this file with ``STORAGE_CONTRACT_PROVIDER=smb`` in the Samba lab/CI to
execute the identical checks against the real network provider. The default
is the isolated mock so the normal unit suite remains fast.
"""

import hashlib
import io
import os
from pathlib import Path

import pytest

from backend.app.storage import MockBinaryStore, StorageTarget
from backend.app.storage.smb import SMBConfig, SMBBinaryStore


@pytest.fixture
def store(tmp_path: Path):
    if os.getenv("STORAGE_CONTRACT_PROVIDER", "mock").lower() == "smb":
        return SMBBinaryStore(SMBConfig(
            server=os.getenv("SMB_SERVER", "samba"),
            port=int(os.getenv("SMB_PORT", "445")),
            share=os.getenv("SMB_SHARE", "ProposalOpsLab"),
            root=os.getenv("SMB_ROOT", "proposalops"),
            username=os.getenv("SMB_USERNAME", "proposalops_rw"),
            password=os.getenv("SMB_PASSWORD", "proposalops_rw_dev"),
            auth_mode=os.getenv("SMB_AUTH_MODE", "ntlm"),
            require_signing=os.getenv("SMB_REQUIRE_SIGNING", "true").lower() == "true",
        ))
    return MockBinaryStore(tmp_path / "contract")


def target_for(store, path: str = "contract"):
    if isinstance(store, SMBBinaryStore):
        return StorageTarget(store.config.provider_id, store.config.share, path)
    return StorageTarget("mock-test", "test", path)


def test_contract_health_capabilities_and_round_trip(store):
    assert store.health().state == "HEALTHY"
    assert store.capabilities().safe_finalize is True
    target = target_for(store)
    content = "ملف عربي / Unicode".encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    temporary = store.write_temporary(target, io.BytesIO(content), operation_id="contract-1", expected_size=len(content), expected_sha256=digest)
    locator = store.finalize(temporary, target_for(store, "contract/documents/v1/ملف عربي.txt"))
    with store.open_read(locator) as stream:
        assert stream.read() == content
    assert store.stat(locator).size == len(content)


def test_contract_immutable_target_conflict(store):
    target = target_for(store)
    first = b"one"
    second = b"two"
    a = store.write_temporary(target, io.BytesIO(first), operation_id="contract-a", expected_size=3, expected_sha256=hashlib.sha256(first).hexdigest())
    store.finalize(a, target_for(store, "contract/immutable.bin"))
    b = store.write_temporary(target, io.BytesIO(second), operation_id="contract-b", expected_size=3, expected_sha256=hashlib.sha256(second).hexdigest())
    with pytest.raises(Exception):
        store.finalize(b, target_for(store, "contract/immutable.bin"))
