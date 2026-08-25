#!/usr/bin/env python3
"""Finalize owner-return evidence without self-accepting T3."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import sys

try:
    from scripts.synology_t3.dsm_state_schema import compare_states, validate_state
    from scripts.synology_t3.t3_common import scan_text_tree
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    handoff_harness = Path(__file__).resolve().parent / "harness_source"
    sys.path.insert(0, str(handoff_harness if (handoff_harness / "t3_common.py").is_file() else repo_root))
    try:
        from scripts.synology_t3.dsm_state_schema import compare_states, validate_state
        from scripts.synology_t3.t3_common import scan_text_tree
    except ModuleNotFoundError:
        from dsm_state_schema import compare_states, validate_state
        from t3_common import scan_text_tree


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def fail_return(root: Path, reason: str, errors: list[str]) -> int:
    write_json(root / "45_DSM_STATE_DELTA.json", {"T3_RETURN_STATUS": "FAIL", "reason": reason, "schema_errors": errors})
    write_json(root / "51_ACCEPTANCE_REGISTRY.json", {"status": "FAIL", "T3_RETURN_STATUS": "FAIL", "FAIL": 1, "errors": errors, "T3_OWNER_EXECUTION_READY": False})
    return 2


def finalize(root: Path, handoff_root: Path | None) -> int:
    pre_path = root / "10_DSM_PRE_STATE.json"
    post_path = root / "44_DSM_POST_STATE.json"
    if not pre_path.is_file() or not post_path.is_file():
        return fail_return(root, "missing exact PRE or POST state file", ["10_DSM_PRE_STATE.json and 44_DSM_POST_STATE.json are required"])
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    post = json.loads(post_path.read_text(encoding="utf-8"))
    schema_errors = validate_state(pre, "PRE") + validate_state(post, "POST")
    comparison = compare_states(pre, post)
    schema_errors.extend(comparison["schema_errors"])
    if comparison["UNAUTHORIZED_DSM_GLOBAL_DELTA_COUNT"] != 0 or comparison["UNAUTHORIZED_BUSINESS_SHARE_DELTA_COUNT"] != 0 or comparison["EXISTING_PROPOSALOPS_IDENTITY_MUTATION_COUNT"] != 0:
        schema_errors.append("immutable DSM/business/identity field changed")
    if post.get("proposalops_t3_ro_enabled") is not False:
        schema_errors.append("proposalops_t3_ro_enabled must be false")
    if post.get("proposalops_t3_denied_enabled") is not False:
        schema_errors.append("proposalops_t3_denied_enabled must be false")
    if post.get("t3_secret_files_retained") != 0:
        schema_errors.append("t3_secret_files_retained must be zero")
    if post.get("t3_recurring_tasks_enabled") != 0:
        schema_errors.append("t3_recurring_tasks_enabled must be zero")
    if post.get("t3_task_removed") is not True:
        schema_errors.append("t3_task_removed must be true")
    schema_errors = sorted(set(schema_errors))
    if schema_errors:
        return fail_return(root, "PRE/POST schema or cleanup proof failed", schema_errors)
    write_json(root / "45_DSM_STATE_DELTA.json", {"T3_RETURN_STATUS": "PASS", **comparison})
    if handoff_root:
        for name in ("SOURCE_MANIFEST.json", "HARNESS_MANIFEST.json"):
            source = handoff_root / name
            if source.is_file():
                shutil.copy2(source, root / name)
    hygiene = scan_text_tree(root, excluded_names={"42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json"})
    write_json(root / "43_ARTIFACT_HYGIENE.json", hygiene)
    registry = json.loads((root / "51_ACCEPTANCE_REGISTRY.json").read_text(encoding="utf-8")) if (root / "51_ACCEPTANCE_REGISTRY.json").is_file() else {}
    registry.update({"status": "OWNER_DSM_SYNTHETIC_RETURN_READY_FOR_INDEPENDENT_ACCEPTANCE" if hygiene["status"] == "PASS" and hygiene["match_count"] == 0 else "FAIL", "T3_RETURN_STATUS": "PASS" if hygiene["status"] == "PASS" and hygiene["match_count"] == 0 else "FAIL", **comparison, "artifact_secret_shaped_match_count": hygiene["match_count"], "T3_OWNER_EXECUTION_READY": False})
    write_json(root / "51_ACCEPTANCE_REGISTRY.json", registry)
    write_json(root / "52_FINAL_HANDOFF.json", {"status": registry["status"], "T3_OWNER_EXECUTION_READY": False, "next": "INDEPENDENT_SYN_T3_ACCEPTANCE"})
    write_manifest(root)
    archive = root.with_suffix(".tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(root, arcname=root.name, recursive=True)
    print(json.dumps({"status": registry["status"], "archive": str(archive), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}, sort_keys=True))
    return 0 if registry["status"] != "FAIL" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--return-root", type=Path, required=True)
    parser.add_argument("--handoff-root", type=Path)
    args = parser.parse_args()
    return finalize(args.return_root.resolve(), args.handoff_root.resolve() if args.handoff_root else None)


if __name__ == "__main__":
    raise SystemExit(main())
