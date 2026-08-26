#!/usr/bin/env python3
"""Create and verify the unified downloadable artifact root manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


def safe_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in {".git", "__pycache__"} for part in relative.parts):
            continue
        if path.is_symlink() or path.is_file():
            files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "ROOT_MANIFEST.sha256"
    entries = []
    for path in safe_files(root):
        if path == manifest_path:
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.is_file() or ".." in Path(relative).parts or relative.startswith("/"):
            raise SystemExit(f"unsafe artifact member: {relative}")
        entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    manifest_path.write_text("\n".join(entries) + "\n", encoding="utf-8")
    with tarfile.open(args.archive, "w:gz") as tar:
        tar.add(root, arcname=root.name, recursive=True)
    with tarfile.open(args.archive, "r:gz") as tar:
        for member in tar.getmembers():
            name = Path(member.name)
            if name.is_absolute() or ".." in name.parts or member.issym() or member.islnk():
                raise SystemExit(f"unsafe archive member: {member.name}")
    print(json.dumps({"root": str(root), "file_count": len(entries), "archive": str(args.archive), "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(), "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
