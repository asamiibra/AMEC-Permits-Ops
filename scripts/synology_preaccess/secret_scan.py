#!/usr/bin/env python3
"""Deterministic, non-disclosing secret scanner for SYN-PRE evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PATTERNS = (
    ("GHP_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PRIVATE_KEY_MARKER", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("SMB_EXTERNAL_PASSWORD", re.compile(r"SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)")),
)
SYNTHETIC_SENTINELS = {"synthetic", "synthetic-placeholder", "synthetic-only-placeholder", "placeholder", "none", "false"}
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", "evidence", "raw", "remote-artifact"}


def _candidate_paths(repo_root: Path, base_sha: str, candidate_sha: str, source_roots: tuple[str, ...]) -> tuple[list[Path], list[str]]:
    errors: list[str] = []
    try:
        output = subprocess.check_output(["git", "diff", "--name-only", base_sha, candidate_sha, "--"], cwd=repo_root, text=True)
        names = [line.strip() for line in output.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError) as exc:
        return [], [f"git diff failed: {type(exc).__name__}"]
    paths = {repo_root / name for name in names}
    for root_name in source_roots:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                paths.add(path)
    return sorted(paths), errors


def scan(repo_root: Path, *, base_sha: str, candidate_sha: str, source_roots: tuple[str, ...]) -> dict:
    paths, errors = _candidate_paths(repo_root, base_sha, candidate_sha, source_roots)
    matches: list[dict] = []
    files_scanned = 0
    for path in paths:
        try:
            relative = path.relative_to(repo_root)
        except ValueError:
            errors.append("path escaped repository root")
            continue
        if any(part in EXCLUDED_PARTS for part in relative.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            errors.append(f"read failed:{relative}:{type(exc).__name__}")
            continue
        files_scanned += 1
        for line_number, line in enumerate(text.splitlines(), 1):
            for pattern_id, pattern in PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if pattern_id == "SMB_EXTERNAL_PASSWORD" and match.group(1).strip('"\'').lower() in SYNTHETIC_SENTINELS:
                    continue
                matches.append({"path": relative.as_posix(), "line": line_number, "pattern_id": pattern_id})
    return {
        "scanner_executed": True,
        "files_scanned": files_scanned,
        "patterns_checked": [pattern_id for pattern_id, _ in PATTERNS],
        "match_count": len(matches),
        "matches": matches,
        "errors": errors,
        "status": "PASS" if not errors and not matches else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", action="append", default=[])
    args = parser.parse_args()
    try:
        result = scan(args.repo_root.resolve(), base_sha=args.base_sha, candidate_sha=args.candidate_sha, source_roots=tuple(args.source_root))
    except Exception as exc:
        result = {"scanner_executed": False, "files_scanned": 0, "patterns_checked": [], "match_count": 0, "matches": [], "errors": [type(exc).__name__], "status": "NOT_EXECUTED"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
