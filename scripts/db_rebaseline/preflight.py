"""Exact-source stale-head classification used before each migration stage."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


OLD_HEAD = "0059_entra_user_identity"
ACTIVE_ALLOWLIST = {
    "backend/app/main.py",
    "backend/tests/test_database_startup_contract.py",
    "release/a1-release-manifest.schema.json",
    "scripts/release/verify_a1_release_manifest.py",
}
HISTORICAL_WORKFLOW = ".github/workflows/azure-a1-f1-batch3a-step4c-hardening-validation.yml"
HISTORICAL_TESTS = {
    "backend/scripts/batch3a_postgres16_proof.py",
    "backend/tests/test_migration_runner.py",
    "backend/tests/test_azure_readiness.py",
    "backend/tests/test_preprod_bootstrap.py",
    "backend/tests/test_user_provisioning.py",
    "backend/tests/test_azure_database_tls.py",
    "backend/tests/test_worker.py",
}


def classify(path: str) -> tuple[str, str]:
    if path in ACTIVE_ALLOWLIST:
        return (
            "ACTIVE_RELEASE_CONTRACT" if path.startswith(("release/", "scripts/release/")) else "ACTIVE_REBASELINE_DEPENDENCY",
            "ALLOWLIST",
        )
    if path == HISTORICAL_WORKFLOW or path in HISTORICAL_TESTS or path.startswith(".github/workflows/azure-a1-batch3a-"):
        return "HISTORICAL_STEP3A4C_EVIDENCE", "FROZEN"
    if path.startswith("backend/migrations/versions/"):
        return "HISTORICAL_MIGRATION_PROVENANCE", "ARCHIVE_REQUIRED"
    if path.startswith("backend/migrations/history/"):
        return "HISTORICAL_MIGRATION_PROVENANCE", "ARCHIVE_REQUIRED"
    if path.startswith("docs/") or path.endswith((".md", ".txt")):
        return "DOCUMENTATION_PROVENANCE", "PRESERVE_OR_UPDATE"
    return "UNCLASSIFIED", "STOP"


def tracked_paths(source_dir: Path) -> list[str]:
    output = subprocess.check_output(["git", "-C", str(source_dir), "ls-tree", "-r", "--name-only", "HEAD"], text=True)
    return [line for line in output.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source_dir = Path(args.source_dir).resolve()
    occurrences = []
    for path in tracked_paths(source_dir):
        full_path = source_dir / path
        try:
            content = full_path.read_bytes()
        except OSError:
            continue
        if b"0059_entra_user_identity" not in content and b"0059_" not in content:
            continue
        for line_number, line in enumerate(content.decode("utf-8", errors="replace").splitlines(), start=1):
            if OLD_HEAD not in line and "0059_" not in line:
                continue
            classification, scope = classify(path)
            occurrences.append(
                {
                    "path": path,
                    "line": line_number,
                    "text_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                    "classification": classification,
                    "scope_result": scope,
                }
            )
    unclassified = [item for item in occurrences if item["classification"] == "UNCLASSIFIED"]
    active_outside = [
        item
        for item in occurrences
        if item["classification"] in {"ACTIVE_REBASELINE_DEPENDENCY", "ACTIVE_RELEASE_CONTRACT"}
        and item["scope_result"] != "ALLOWLIST"
    ]
    result = {
        "source_sha": subprocess.check_output(["git", "-C", str(source_dir), "rev-parse", "HEAD"], text=True).strip(),
        "source_method": "FULL_GIT_TREE",
        "occurrences": occurrences,
        "unclassified_count": len(unclassified),
        "active_stale_head_outside_allowlist_count": len(active_outside),
        "active_stale_head_outside_allowlist": active_outside,
        "stale_head_sweep_executed": True,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PREFLIGHT_STALE_HEAD_UNCLASSIFIED_COUNT={len(unclassified)}")
    print(f"PREFLIGHT_ACTIVE_STALE_HEAD_OUTSIDE_ALLOWLIST_COUNT={len(active_outside)}")
    return 1 if unclassified or active_outside else 0


if __name__ == "__main__":
    raise SystemExit(main())
