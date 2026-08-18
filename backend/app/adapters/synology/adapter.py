import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from ...storage.fixture_exclusion import ensure_fixture_path_allowed


@dataclass(frozen=True)
class StorageFaultPlan:
    """Deterministic synthetic faults for the storage seam test harness."""

    fail_before_write: bool = False
    fail_during_readback: bool = False
    force_hash_mismatch: bool = False


class SynologyAdapter(Protocol):
    def list_project_roots(self) -> list[str]: ...
    def list_project_files(self, project_ref: str) -> list[dict]: ...
    def get_file_metadata(self, path: str) -> dict: ...
    def resolve_project_root(self, root_path: str) -> Path: ...
    def ensure_configured_project_structure(self, root_path: str, expected_folders: list[str]) -> dict: ...
    def put_artifact(self, root_path: str, semantic_folder: str, filename: str, content: bytes) -> dict: ...
    def read_artifact_metadata(self, path: str) -> dict: ...
    def verify_artifact(self, path: str, expected_hash: str, expected_size: int) -> dict: ...
    def health_check(self) -> dict: ...
    def write_readback_hash(self, destination: str, filename: str, content: bytes, *, fault_plan: StorageFaultPlan | None = None) -> dict: ...


class MockSynologyAdapter:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def list_project_roots(self) -> list[str]:
        return [str(p.relative_to(self.root)) for p in self.root.glob("2026/PRJ-*") if p.is_dir()]

    def list_project_files(self, project_ref: str) -> list[dict]:
        ensure_fixture_path_allowed(project_ref)
        folder = self.root / project_ref
        if not folder.exists(): return []
        return [self.get_file_metadata(str(path.relative_to(self.root))) for path in folder.rglob("*") if path.is_file()]

    def get_file_metadata(self, path: str) -> dict:
        ensure_fixture_path_allowed(path)
        file_path = self.root / path
        stat = file_path.stat()
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        return {"path": path, "name": file_path.name, "size": stat.st_size, "suffix": file_path.suffix, "sha256": digest, "synthetic": True}

    def resolve_project_root(self, root_path: str) -> Path:
        """Resolve only a configured relative root below the adapter root."""
        ensure_fixture_path_allowed(root_path)
        if not root_path or Path(root_path).is_absolute() or ".." in Path(root_path).parts:
            raise ValueError("INVALID_CONFIGURED_PROJECT_ROOT")
        resolved = (self.root / root_path).resolve()
        adapter_root = self.root.resolve()
        if adapter_root not in resolved.parents and resolved != adapter_root:
            raise ValueError("PROJECT_ROOT_ESCAPES_SOR")
        return resolved

    def ensure_configured_project_structure(self, root_path: str, expected_folders: list[str]) -> dict:
        resolved = self.resolve_project_root(root_path)
        if not resolved.exists():
            raise FileNotFoundError("SOR_PROJECT_ROOT_UNAVAILABLE")
        observed = sorted(path.name for path in resolved.iterdir() if path.is_dir())
        expected = sorted(expected_folders)
        if observed != expected:
            raise RuntimeError("SOR_FOLDER_TEMPLATE_DRIFT")
        return {"root": str(resolved), "observed_folders": observed, "template_match": True}

    def put_artifact(self, root_path: str, semantic_folder: str, filename: str, content: bytes) -> dict:
        resolved = self.resolve_project_root(root_path)
        destination_folder = (resolved / semantic_folder).resolve()
        if destination_folder.parent != resolved or not destination_folder.is_dir():
            raise RuntimeError("SOR_DESTINATION_NOT_CONFIGURED")
        return self.write_readback_hash(str(destination_folder.relative_to(self.root)), filename, content)

    def read_artifact_metadata(self, path: str) -> dict:
        safe = Path(path)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError("INVALID_SOR_PATH")
        return self.get_file_metadata(str(safe))

    def verify_artifact(self, path: str, expected_hash: str, expected_size: int) -> dict:
        metadata = self.read_artifact_metadata(path)
        return {**metadata, "verified": metadata["sha256"] == expected_hash and metadata["size"] == expected_size}

    def health_check(self) -> dict:
        return {
            "adapter": "SYNOLOGY",
            "status": "OK" if self.root.exists() else "UNAVAILABLE",
            "configured": self.root.exists(),
            "storage_scope": "SYNTHETIC_LOCAL_ROOT",
            "synthetic": True,
        }

    def resolve_configured_path(self, configured_path: str) -> Path:
        """Resolve a server-side configured path below the adapter root only."""
        ensure_fixture_path_allowed(configured_path)
        if not configured_path:
            raise ValueError("SOR_DESTINATION_UNRESOLVED")
        candidate = Path(configured_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("SOR_DESTINATION_UNRESOLVED")
        resolved = (self.root / candidate).resolve()
        if self.root.resolve() not in resolved.parents and resolved != self.root.resolve():
            raise ValueError("SOR_DESTINATION_UNRESOLVED")
        if not resolved.is_dir():
            raise FileNotFoundError("SOR_DESTINATION_UNAVAILABLE")
        return resolved

    def put_configured_artifact(self, configured_path: str, filename: str, content: bytes) -> dict:
        folder = self.resolve_configured_path(configured_path)
        return self.write_readback_hash(str(folder.relative_to(self.root)), filename, content)

    def write_readback_hash(
        self,
        destination: str,
        filename: str,
        content: bytes,
        *,
        fault_plan: StorageFaultPlan | None = None,
    ) -> dict:
        """Atomically write a version, read it back, and verify its identity.

        The current pointer is never promoted before the temporary file has
        passed read-back and SHA-256 validation. An existing identical file is
        an idempotent reuse; an existing different file is immutable-version
        drift and fails closed.
        """
        if not re.fullmatch(r"[A-Za-z0-9._ -]+", filename) or filename in {".", ".."}:
            raise ValueError("INVALID_STORED_FILENAME")
        if not isinstance(content, bytes) or not content:
            raise ValueError("EMPTY_ARTIFACT")
        plan = fault_plan or StorageFaultPlan()
        folder = self.resolve_configured_path(destination)
        target = folder / filename
        expected_hash = hashlib.sha256(content).hexdigest()
        if target.exists():
            existing = self.get_file_metadata(str(target.relative_to(self.root)))
            if existing["sha256"] == expected_hash and existing["size"] == len(content):
                return {**existing, "verified": True, "read_back": True, "hash_match": True, "reused": True}
            raise RuntimeError("SOR_VERSION_IMMUTABLE")
        if plan.fail_before_write:
            raise OSError("SOR_WRITE_FAILED_BEFORE_COMMIT")

        temporary = folder / f".{filename}.pending-{uuid4().hex}"
        try:
            temporary.write_bytes(content)
            if plan.fail_during_readback:
                raise OSError("SOR_READBACK_UNAVAILABLE")
            read_back = temporary.read_bytes()
            observed_hash = hashlib.sha256(read_back).hexdigest()
            if plan.force_hash_mismatch:
                observed_hash = "0" * 64
            if observed_hash != expected_hash or len(read_back) != len(content):
                raise RuntimeError("SOR_HASH_MISMATCH")
            temporary.replace(target)
            metadata = self.get_file_metadata(str(target.relative_to(self.root)))
            return {**metadata, "verified": True, "read_back": True, "hash_match": True, "reused": False}
        finally:
            if temporary.exists():
                temporary.unlink()

    def read_configured_artifact(self, path: str) -> bytes:
        ensure_fixture_path_allowed(path)
        safe = Path(path)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError("INVALID_SOR_PATH")
        file_path = (self.root / safe).resolve()
        if self.root.resolve() not in file_path.parents or not file_path.is_file():
            raise FileNotFoundError("SOR_FILE_NOT_FOUND")
        return file_path.read_bytes()
