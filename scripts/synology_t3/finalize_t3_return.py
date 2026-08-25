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
    from scripts.synology_t3.t3_common import scan_text_tree
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[2]
    handoff_harness = Path(__file__).resolve().parent / "harness_source"
    sys.path.insert(0, str(handoff_harness if (handoff_harness / "t3_common.py").is_file() else repo_root))
    try:
        from scripts.synology_t3.t3_common import scan_text_tree
    except ModuleNotFoundError:
        from t3_common import scan_text_tree


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def state_delta(pre: dict, post: dict) -> dict:
    global_keys = ("smb", "firewall", "auto_block", "tun1000", "network", "global_smb")
    business_keys = ("business_shares", "shares")
    identity_keys = ("existing_proposalops_identities", "existing_identities")
    global_delta = sum(pre.get(key) != post.get(key) for key in global_keys if key in pre or key in post)
    business_delta = sum(pre.get(key) != post.get(key) for key in business_keys if key in pre or key in post)
    identity_delta = sum(pre.get(key) != post.get(key) for key in identity_keys if key in pre or key in post)
    retained = post.get("t3_secret_files_retained", post.get("secret_files_retained", 0))
    if isinstance(retained, list):
        retained = len(retained)
    tasks = post.get("t3_recurring_tasks_enabled", post.get("recurring_tasks_enabled", 0))
    if isinstance(tasks, list):
        tasks = sum(bool(item.get("enabled")) for item in tasks if isinstance(item, dict))
    return {
        "unauthorized_global_delta_count": int(global_delta),
        "unauthorized_business_share_delta_count": int(business_delta),
        "existing_proposalops_identity_mutation_count": int(identity_delta),
        "t3_secret_files_retained": int(retained),
        "t3_recurring_tasks_enabled": int(tasks),
        "comparison_keys": {"global": global_keys, "business": business_keys, "identities": identity_keys},
    }


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


def finalize(root: Path, handoff_root: Path | None) -> int:
    pre_path = root / "10_DSM_PRE_STATE.json"
    post_path = root / "44_DSM_POST_STATE.json"
    delta_path = root / "45_DSM_STATE_DELTA.json"
    if not pre_path.is_file() or not post_path.is_file():
        write_json(delta_path, {"T3_RETURN_STATUS": "FAIL", "reason": "missing 10_DSM_PRE_STATE.json or 44_DSM_POST_STATE.json"})
        return 2
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    post = json.loads(post_path.read_text(encoding="utf-8"))
    if post.get("status") == "OWNER_POST_STATE_REQUIRED":
        write_json(delta_path, {"T3_RETURN_STATUS": "FAIL", "reason": "44_DSM_POST_STATE.json is still the runner placeholder"})
        return 2
    delta = state_delta(pre, post)
    delta["T3_RETURN_STATUS"] = "PASS" if all(value == 0 for key, value in delta.items() if key.endswith("count") or key.endswith("retained") or key.endswith("enabled")) else "FAIL"
    write_json(delta_path, delta)
    if handoff_root:
        for name in ("SOURCE_MANIFEST.json", "HARNESS_MANIFEST.json"):
            source = handoff_root / name
            if source.is_file():
                shutil.copy2(source, root / name)
    hygiene = scan_text_tree(root, excluded_names={"42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json"})
    write_json(root / "43_ARTIFACT_HYGIENE.json", hygiene)
    registry = json.loads((root / "51_ACCEPTANCE_REGISTRY.json").read_text(encoding="utf-8")) if (root / "51_ACCEPTANCE_REGISTRY.json").is_file() else {}
    registry.update({"status": "OWNER_DSM_SYNTHETIC_RETURN_READY_FOR_INDEPENDENT_ACCEPTANCE" if delta["T3_RETURN_STATUS"] == "PASS" and hygiene["status"] == "PASS" and hygiene["match_count"] == 0 else "FAIL", "T3_RETURN_STATUS": delta["T3_RETURN_STATUS"], **delta, "artifact_secret_shaped_match_count": hygiene["match_count"], "T3_OWNER_EXECUTION_READY": False})
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
