from pathlib import Path
from typing import Protocol


class SynologyAdapter(Protocol):
    def list_project_roots(self) -> list[str]: ...
    def list_project_files(self, project_ref: str) -> list[dict]: ...
    def get_file_metadata(self, path: str) -> dict: ...
    def health_check(self) -> dict: ...


class MockSynologyAdapter:
    def __init__(self, root: str):
        self.root = Path(root)

    def list_project_roots(self) -> list[str]:
        return [str(p.relative_to(self.root)) for p in self.root.glob("2026/PRJ-*") if p.is_dir()]

    def list_project_files(self, project_ref: str) -> list[dict]:
        folder = self.root / project_ref
        if not folder.exists(): return []
        return [self.get_file_metadata(str(path.relative_to(self.root))) for path in folder.rglob("*") if path.is_file()]

    def get_file_metadata(self, path: str) -> dict:
        file_path = self.root / path
        stat = file_path.stat()
        return {"path": path, "name": file_path.name, "size": stat.st_size, "suffix": file_path.suffix, "synthetic": True}

    def health_check(self) -> dict:
        return {"adapter": "SYNOLOGY", "status": "OK" if self.root.exists() else "UNAVAILABLE", "root": str(self.root), "synthetic": True}
