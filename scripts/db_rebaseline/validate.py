"""Fail-closed static validation for the two rebaseline stages."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


SOURCE_SHA = "96c4b90968754efd8e5998cd1b1793b67c23d2bc"
AUTHORIZED_PREFIXES = (
    "backend/migrations/versions/",
    "backend/migrations/history/postgresql_r13_0001_0059/",
    "scripts/db_rebaseline/",
    "backend/app/main.py",
    "backend/tests/test_database_startup_contract.py",
    "backend/tests/test_db_rebaseline.py",
    "release/a1-release-manifest.schema.json",
    "scripts/release/verify_a1_release_manifest.py",
    ".github/workflows/db-rebaseline-validation.yml",
    "docs/database/DB_REBASELINE_R13_0059.md",
)
FORBIDDEN_BASELINE_PATTERNS = (
    r"backend\.app\.models",
    r"\bBase\s*\.\s*metadata\s*\.\s*(create_all|drop_all)",
    r"\b(create_all|drop_all)\s*\(",
    r"sqlalchemy\.dialects\.postgresql",
    r"\bCREATE\s+TABLE\b",
    r"\bDROP\s+TABLE\b",
    r"\bpsql\b",
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def stage_a(root: Path) -> None:
    paths = git("diff", "--name-only", SOURCE_SHA, "HEAD").splitlines()
    forbidden = [path for path in paths if not (path.startswith("scripts/db_rebaseline/") or path == ".github/workflows/db-rebaseline-validation.yml")]
    if forbidden:
        raise SystemExit(f"STAGE_A_FORBIDDEN_CHANGED_PATHS={forbidden}")
    if list((root / "backend/migrations/versions").glob("baseline_r13_0059.py")):
        raise SystemExit("STAGE_A_BASELINE_PRESENT")
    if len(list((root / "backend/migrations/versions").glob("*.py"))) != 59:
        raise SystemExit("STAGE_A_LEGACY_MIGRATION_COUNT_DRIFT")
    print("STAGE_A_MIGRATIONS_CHANGED=false")
    print("STAGE_A_RELEASE_CONTRACT_CHANGED=false")
    print("STAGE_A_RUNTIME_CHANGED=false")


def candidate(root: Path) -> None:
    active = sorted((root / "backend/migrations/versions").glob("*.py"))
    if len(active) != 1 or active[0].name != "baseline_r13_0059.py":
        raise SystemExit("ACTIVE_MIGRATION_GRAPH_INVALID")
    baseline = active[0].read_text(encoding="utf-8")
    for pattern in FORBIDDEN_BASELINE_PATTERNS:
        if re.search(pattern, baseline, flags=re.IGNORECASE):
            raise SystemExit(f"BASELINE_FORBIDDEN_PATTERN={pattern}")
    required = [
        'revision = "baseline_r13_0059"',
        "down_revision = None",
        'raise RuntimeError("Canonical root baseline downgrade is intentionally unsupported")',
        "op.create_table(",
    ]
    for marker in required:
        if marker not in baseline:
            raise SystemExit(f"BASELINE_REQUIRED_MARKER_MISSING={marker}")
    old_files = sorted((root / "backend/migrations/history/postgresql_r13_0001_0059").glob("*.py"))
    if len(old_files) != 59:
        raise SystemExit(f"LEGACY_ARCHIVE_ENTRY_COUNT={len(old_files)}")
    for path in old_files:
        relative = str(path.relative_to(root))
        source_path = relative.replace("backend/migrations/history/postgresql_r13_0001_0059/", "backend/migrations/versions/")
        expected = git("rev-parse", f"{SOURCE_SHA}:{source_path}")
        actual = git("hash-object", str(path))
        if expected != actual:
            raise SystemExit(f"LEGACY_ARCHIVE_GIT_BLOB_MISMATCH={path.name}")
    print(f"ACTIVE_MIGRATION_COUNT={len(active)}")
    print("ACTIVE_ROOT_COUNT=1")
    print("ACTIVE_HEAD=baseline_r13_0059")
    print("LEGACY_ARCHIVE_ENTRY_COUNT=59")
    print("LEGACY_ARCHIVE_BYTE_PARITY=PASS")
    print("LEGACY_ARCHIVE_GIT_BLOB_PARITY=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("stage-a", "candidate"), required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    stage_a(root) if args.mode == "stage-a" else candidate(root)


if __name__ == "__main__":
    main()
