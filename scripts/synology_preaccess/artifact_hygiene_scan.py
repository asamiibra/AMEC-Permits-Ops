#!/usr/bin/env python3
"""Scan replayable evidence members for secret-shaped leakage."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PATTERNS = (
    ("GHP_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PRIVATE_KEY_MARKER", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("SMB_EXTERNAL_PASSWORD", re.compile(r"SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)")),
)
SYNTHETIC_SENTINELS = {"synthetic", "synthetic-placeholder", "synthetic-only-placeholder", "placeholder", "none", "false"}
SCAN_DIRS = ("raw", "evidence")


def _files_to_scan(root: Path) -> tuple[list[Path], list[str]]:
    errors: list[str] = []
    paths: list[Path] = []
    for name in SCAN_DIRS:
        directory = root / name
        if not directory.is_dir():
            errors.append(f"missing scan directory:{name}")
            continue
        for path in directory.rglob("*"):
            if path.is_symlink():
                errors.append(f"symlink in scan scope:{path.relative_to(root).as_posix()}")
            elif path.is_file():
                paths.append(path)
    source_manifest = root / "source_manifest.json"
    if not source_manifest.is_file():
        errors.append("missing scan file:source_manifest.json")
    else:
        paths.append(source_manifest)
    return sorted(set(paths)), errors


def scan_artifact(root: Path) -> dict:
    root = root.resolve()
    matches: list[dict[str, object]] = []
    paths, errors = _files_to_scan(root)
    files_scanned = 0
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"read failed:{relative}:{type(exc).__name__}")
            continue
        files_scanned += 1
        for line_number, line in enumerate(text.splitlines(), 1):
            for pattern_id, pattern in PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if pattern_id == "SMB_EXTERNAL_PASSWORD" and match.group(1).strip("\"'").lower() in SYNTHETIC_SENTINELS:
                    continue
                matches.append({"path": relative, "line": line_number, "pattern_id": pattern_id})
    return {
        "scanner_executed": True,
        "files_scanned": files_scanned,
        "patterns_checked": [pattern_id for pattern_id, _ in PATTERNS],
        "match_count": len(matches),
        "matches": matches,
        "errors": errors,
        "status": "PASS" if not matches and not errors else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = scan_artifact(args.artifact_root)
    except Exception as exc:  # the JSON result remains machine-readable on scanner failure
        result = {"scanner_executed": False, "files_scanned": 0, "patterns_checked": [], "match_count": 0, "matches": [], "errors": [type(exc).__name__], "status": "FAIL"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
