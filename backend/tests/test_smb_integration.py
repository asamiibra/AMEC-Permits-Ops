"""Live Samba integration checks.

These checks are intentionally opt-in. They use the same provider and lab
credentials as the CI workflow and are never satisfied by the mock store.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import os
from uuid import uuid4

import pytest

from backend.app.storage import SMBConfig, SMBBinaryStore, StorageError, StorageErrorCode, StorageTarget


pytestmark = pytest.mark.skipif(
    os.getenv("STORAGE_CONTRACT_PROVIDER", "mock").lower() != "smb",
    reason="live Samba integration suite requires STORAGE_CONTRACT_PROVIDER=smb",
)


def make_store(*, username: str | None = None, password: str | None = None, share: str | None = None) -> SMBBinaryStore:
    return SMBBinaryStore(SMBConfig(
        server=os.getenv("SMB_SERVER", "127.0.0.1"),
        port=int(os.getenv("SMB_PORT", "1445")),
        share=share or os.getenv("SMB_SHARE", "ProposalOpsLab"),
        root=os.getenv("SMB_ROOT", "proposalops"),
        username=username or os.getenv("SMB_USERNAME", "proposalops_rw"),
        password=password or os.getenv("SMB_PASSWORD", "proposalops_rw_dev"),
        auth_mode=os.getenv("SMB_AUTH_MODE", "ntlm"),
        require_signing=os.getenv("SMB_REQUIRE_SIGNING", "true").lower() == "true",
    ))


def target(path: str) -> StorageTarget:
    return StorageTarget("smb", os.getenv("SMB_SHARE", "ProposalOpsLab"), path)


def test_temporary_retry_cleanup_and_range_read():
    store = make_store()
    path = f"integration/retry-{uuid4()}"
    content = ("retry / تقرير عربي / Unicode" * 64).encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    temporary = store.write_temporary(target(path), io.BytesIO(content), operation_id=str(uuid4()), expected_size=len(content), expected_sha256=digest)
    retried = store.write_temporary(target(path), io.BytesIO(content), operation_id=temporary.operation_id, expected_size=len(content), expected_sha256=digest)
    assert retried.locator == temporary.locator
    final = store.finalize(retried, target(f"{path}/documents/v1/report.txt"))
    with store.open_read(final, offset=7, length=12) as stream:
        assert stream.read() == content[7:19]
    store.cleanup_temporary(retried)
    with pytest.raises(StorageError) as error:
        store.stat(retried.locator)
    assert error.value.code == StorageErrorCode.OBJECT_NOT_FOUND


def test_delete_is_detected_as_missing_object():
    store = make_store()
    path = f"integration/delete-{uuid4()}"
    content = b"delete me"
    temporary = store.write_temporary(target(path), io.BytesIO(content), operation_id=str(uuid4()), expected_size=len(content), expected_sha256=hashlib.sha256(content).hexdigest())
    final = store.finalize(temporary, target(f"{path}/documents/v1/delete.bin"))
    store._client().remove(store._unc(final.relative_path), **store._session_kwargs())
    with pytest.raises(StorageError) as error:
        store.open_read(final)
    assert error.value.code == StorageErrorCode.OBJECT_NOT_FOUND


def test_read_only_and_denied_credentials_are_not_write_capable():
    read_only = make_store(username="proposalops_ro", password=os.getenv("SMB_PASSWORD_RO", "proposalops_ro_dev"))
    assert read_only.health().state == "HEALTHY"
    content = b"must not write"
    with pytest.raises(StorageError) as error:
        read_only.write_temporary(target(f"integration/readonly-{uuid4()}"), io.BytesIO(content), operation_id=str(uuid4()), expected_size=len(content), expected_sha256=hashlib.sha256(content).hexdigest())
    assert error.value.code in {StorageErrorCode.ACCESS_DENIED, StorageErrorCode.AUTH_FAILED, StorageErrorCode.UNAVAILABLE}

    denied = make_store(username="proposalops_denied", password=os.getenv("SMB_PASSWORD_DENIED", "proposalops_denied_dev"))
    assert denied.health().state in {"AUTH_FAILED", "UNAVAILABLE"}


def test_missing_share_is_not_reported_healthy():
    missing = make_store(share="ProposalOpsMissing")
    assert missing.health().state in {"AUTH_FAILED", "UNAVAILABLE"}


def test_independent_provider_instances_can_write_concurrently():
    namespace = f"integration/concurrency-{uuid4()}"

    def write_one(index: int) -> str:
        store = make_store()
        content = f"worker-{index}-تقرير".encode("utf-8")
        temporary = store.write_temporary(target(f"{namespace}/{index}"), io.BytesIO(content), operation_id=str(uuid4()), expected_size=len(content), expected_sha256=hashlib.sha256(content).hexdigest())
        final = store.finalize(temporary, target(f"{namespace}/{index}/documents/v1/file.txt"))
        with store.open_read(final) as stream:
            assert stream.read() == content
        return final.serialized()

    with ThreadPoolExecutor(max_workers=6) as pool:
        locators = list(pool.map(write_one, range(6)))
    assert len(set(locators)) == 6
