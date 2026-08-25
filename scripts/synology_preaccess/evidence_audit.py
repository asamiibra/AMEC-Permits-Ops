#!/usr/bin/env python3
"""Referential, structural, and distinctness audit for the unified artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ALLOWED_RESULTS = {"PASS", "FAIL", "WARN", "ENV_BLOCKED", "NOT_EXECUTED"}
DEFERRED = {"REAL_SMB_SERVER_SIDE_PAGINATION", "REAL_SMB_HARD_OPERATION_ABORT", "REAL_DSM_REPARSE_REFERRAL"}
REQUIRED_CHECK_FIELDS = {"check_id", "requirement_id", "category", "assertion", "method", "expected", "observed", "result", "evidence_refs", "independence_basis"}


def normalize_assertion(value: str) -> str:
    value = re.sub(r"^round\s+\d+\s+", "", value.lower().strip())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", value)).strip()


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in value and value != ""


def _manifest_entries(root: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    manifest_path = root / "ROOT_MANIFEST.sha256"
    if not manifest_path.is_file():
        return {}, ["ROOT_MANIFEST.sha256 missing"]
    entries: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]) or not _safe_relative(parts[1]) or parts[1] in entries:
            errors.append(f"unsafe or duplicate root manifest line: {line}")
            continue
        entries[parts[1]] = parts[0]
    return entries, errors


def audit(root: Path, *, repo_root: Path | None = None, require_root_manifest: bool = True) -> dict:
    root = root.resolve()
    errors: list[str] = []
    registry_path = root / "evidence" / "50_ACCEPTANCE_REGISTRY.json"
    if not registry_path.is_file():
        return {"status": "FAIL", "errors": ["acceptance registry missing"]}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    hygiene_path = root / "evidence" / "52_ARTIFACT_HYGIENE.json"
    if not hygiene_path.is_file():
        errors.append("artifact hygiene evidence missing")
    else:
        try:
            hygiene = json.loads(hygiene_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            hygiene = None
            errors.append("artifact hygiene evidence malformed")
        if hygiene is not None:
            if hygiene.get("scanner_executed") is not True:
                errors.append("artifact hygiene scanner was not executed")
            if hygiene.get("match_count") != 0:
                errors.append("artifact hygiene secret-shaped matches are nonzero")
            if hygiene.get("errors") != []:
                errors.append("artifact hygiene scanner errors are nonempty")
            if hygiene.get("status") != "PASS":
                errors.append("artifact hygiene scanner did not PASS")
            if hygiene.get("matches") != []:
                errors.append("artifact hygiene match list is nonempty")
    checks = registry.get("checks", [])
    if len(checks) < 90:
        errors.append("distinct assertion minimum is not met")
    if any(set(item) != REQUIRED_CHECK_FIELDS for item in checks):
        errors.append("check schema mismatch")
    ids = [item.get("check_id") for item in checks]
    if len(ids) != len(set(ids)):
        errors.append("duplicate check ids")
    normalized = [normalize_assertion(item.get("assertion", "")) for item in checks]
    normalized_duplicates = len(normalized) - len(set(normalized))
    if normalized_duplicates:
        errors.append("normalized assertion duplicates")
    tuples = [(item.get("assertion"), json.dumps(item.get("expected"), sort_keys=True), json.dumps(item.get("observed"), sort_keys=True), tuple(sorted(item.get("evidence_refs", [])))) for item in checks]
    tuple_duplicates = len(tuples) - len(set(tuples))
    if tuple_duplicates:
        errors.append("duplicate evidence tuples")
    if any(item.get("result") not in ALLOWED_RESULTS for item in checks):
        errors.append("invalid result status")
    warnings = {item.get("assertion") for item in checks if item.get("result") == "WARN"}
    if warnings != DEFERRED:
        errors.append("WARN set is not exactly the three deferred capabilities")
    source_manifest_path = root / "source_manifest.json"
    if not source_manifest_path.is_file():
        errors.append("source manifest missing")
        source_rows = {}
    else:
        source_payload = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_rows = {row.get("path"): row for row in source_payload.get("rows", [])}
        if len(source_rows) != len(source_payload.get("rows", [])):
            errors.append("duplicate source manifest path")
    root_entries, manifest_errors = _manifest_entries(root)
    if require_root_manifest:
        errors.extend(manifest_errors)
    elif manifest_errors == ["ROOT_MANIFEST.sha256 missing"]:
        root_entries = {}
    else:
        errors.extend(manifest_errors)
    actual_files = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if relative == "ROOT_MANIFEST.sha256" or any(part in {".git", "__pycache__"} for part in Path(relative).parts):
            continue
        if path.is_symlink() or (path.is_file() and os.stat(path).st_nlink > 1):
            errors.append(f"symlink/hardlink artifact member: {relative}")
        if path.is_file():
            actual_files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if root_entries and set(actual_files) != set(root_entries):
        errors.append("unlisted artifact file")
    for relative, digest in root_entries.items():
        if actual_files.get(relative) != digest:
            errors.append(f"manifest digest mismatch: {relative}")
    cited_raw = set()
    cited_source = set()
    for item in checks:
        for ref in item.get("evidence_refs", []):
            if ref.startswith("raw:"):
                name = ref[4:]
                if not _safe_relative(name) or Path(name).name != name or not (root / "raw" / name).is_file():
                    errors.append(f"unresolved raw evidence ref: {ref}")
                cited_raw.add(name)
            elif ref.startswith("source:"):
                path = ref[7:]
                row = source_rows.get(path)
                if not _safe_relative(path) or row is None:
                    errors.append(f"unresolved source evidence ref: {ref}")
                elif repo_root is not None:
                    try:
                        blob = subprocess.check_output(["git", "cat-file", "blob", row["blob_sha"]], cwd=repo_root)
                        if hashlib.sha256(blob).hexdigest() != row.get("sha256"):
                            errors.append(f"source manifest digest mismatch: {path}")
                    except (OSError, subprocess.CalledProcessError, KeyError):
                        errors.append(f"source blob cannot be resolved: {path}")
            elif "50_ACCEPTANCE_REGISTRY" in ref:
                errors.append("self-referential evidence ref")
            else:
                errors.append(f"unknown evidence ref: {ref}")
    if not all((root / "raw" / name).is_file() for name in cited_raw):
        errors.append("raw evidence resolution failed")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "distinct_assertions": len(checks), "normalized_assertion_duplicate_count": normalized_duplicates, "duplicate_evidence_tuple_count": tuple_duplicates, "unresolved_evidence_ref_count": sum("unresolved" in error for error in errors), "self_reference_count": sum("self-referential" in error for error in errors), "raw_evidence_file_count": len(list((root / "raw").glob("*")))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", "--evidence", dest="artifact_root", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--allow-missing-root-manifest", action="store_true")
    args = parser.parse_args()
    result = audit(args.artifact_root, repo_root=args.repo_root, require_root_manifest=not args.allow_missing_root_manifest)
    print(json.dumps(result, sort_keys=True))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
