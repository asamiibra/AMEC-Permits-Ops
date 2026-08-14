import hashlib
import re
from pathlib import Path
from typing import Protocol


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


class MockSynologyAdapter:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def list_project_roots(self) -> list[str]:
        return [str(p.relative_to(self.root)) for p in self.root.glob("2026/PRJ-*") if p.is_dir()]

    def list_project_files(self, project_ref: str) -> list[dict]:
        folder = self.root / project_ref
        if not folder.exists(): return []
        return [self.get_file_metadata(str(path.relative_to(self.root))) for path in folder.rglob("*") if path.is_file()]

    def get_file_metadata(self, path: str) -> dict:
        file_path = self.root / path
        stat = file_path.stat()
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        return {"path": path, "name": file_path.name, "size": stat.st_size, "suffix": file_path.suffix, "sha256": digest, "synthetic": True}

    def resolve_project_root(self, root_path: str) -> Path:
        """Resolve only a configured relative root below the adapter root."""
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
        if not re.fullmatch(r"[A-Za-z0-9._ -]+", filename) or filename in {".", ".."}:
            raise ValueError("INVALID_STORED_FILENAME")
        resolved = self.resolve_project_root(root_path)
        destination_folder = (resolved / semantic_folder).resolve()
        if destination_folder.parent != resolved or not destination_folder.is_dir():
            raise RuntimeError("SOR_DESTINATION_NOT_CONFIGURED")
        destination = destination_folder / filename
        destination.write_bytes(content)
        relative = str(destination.relative_to(self.root))
        return self.get_file_metadata(relative)

    def read_artifact_metadata(self, path: str) -> dict:
        safe = Path(path)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError("INVALID_SOR_PATH")
        return self.get_file_metadata(str(safe))

    def verify_artifact(self, path: str, expected_hash: str, expected_size: int) -> dict:
        metadata = self.read_artifact_metadata(path)
        return {**metadata, "verified": metadata["sha256"] == expected_hash and metadata["size"] == expected_size}

    def health_check(self) -> dict:
        return {"adapter": "SYNOLOGY", "status": "OK" if self.root.exists() else "UNAVAILABLE", "root": str(self.root), "synthetic": True}

    def resolve_configured_path(self, configured_path: str) -> Path:
        """Resolve a server-side configured path below the adapter root only."""
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
        if not re.fullmatch(r"[A-Za-z0-9._ -]+", filename) or filename in {".", ".."}:
            raise ValueError("INVALID_STORED_FILENAME")
        folder = self.resolve_configured_path(configured_path)
        destination = folder / filename
        destination.write_bytes(content)
        return self.get_file_metadata(str(destination.relative_to(self.root)))

    def read_configured_artifact(self, path: str) -> bytes:
        safe = Path(path)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError("INVALID_SOR_PATH")
        file_path = (self.root / safe).resolve()
        if self.root.resolve() not in file_path.parents or not file_path.is_file():
            raise FileNotFoundError("SOR_FILE_NOT_FOUND")
        return file_path.read_bytes()
