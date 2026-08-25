#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

REQUIRED_RETURN_FILES = {
    "00_AUTHORIZATION.json", "01_APPLICATION_IDENTITY.json", "02_HARNESS_IDENTITY.json", "03_STAGE1R_REFERENCE.json", "04_T2_SKIP_OWNER_DECISION.json",
    "10_DSM_PRE_STATE.json", "11_TEST_SHARE_IDENTITY.json", "12_TEST_ACCOUNT_POLICY.json", "13_FIXTURE_MANIFEST.json", "14_NETWORK_DESTINATION_POLICY.json", "15_CONTAINER_IDENTITY.json",
    "20_SMB_SESSION_SECURITY.json", "21_HEALTH.json", "22_CAPABILITIES.json", "23_STAT_RESULTS.json", "24_READ_HASH_RESULTS.json", "25_RANGE_STREAM_RESULTS.json", "26_LISTING_RESULTS.json", "27_UNICODE_PATH_RESULTS.json", "28_STABILITY_RESULTS.json", "29_MUTATION_RACE_RESULTS.json",
    "30_RO_ACL_NEGATIVES.json", "31_DENIED_IDENTITY_RESULTS.json", "32_MISSING_SHARE_OBJECT_RESULTS.json", "33_SESSION_ISOLATION.json", "34_RECONNECT_RESULTS.json",
    "40_ZERO_REAL_DATA.json", "41_ZERO_UNEXPECTED_NETWORK.json", "42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json", "44_DSM_POST_STATE.json", "45_DSM_STATE_DELTA.json",
    "50_TEST_RESULTS.junit.xml", "51_ACCEPTANCE_REGISTRY.json", "52_FINAL_HANDOFF.json", "SOURCE_MANIFEST.json", "MANIFEST.sha256",
}
PATTERNS = (
    ("GHP_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PRIVATE_KEY_MARKER", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("SMB_EXTERNAL_PASSWORD", re.compile(r"SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)")),
)


def scan(root: Path) -> dict:
    matches = []
    files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "43_ARTIFACT_HYGIENE.json":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        files += 1
        for line_number, line in enumerate(text.splitlines(), 1):
            for pattern_id, pattern in PATTERNS:
                if pattern.search(line):
                    matches.append({"path": path.relative_to(root).as_posix(), "line": line_number, "pattern_id": pattern_id})
    return {"files_scanned": files, "matches": matches, "match_count": len(matches)}


def root_manifest_ok(root: Path) -> list[str]:
    errors = []
    listed = {}
    for line in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2:
            errors.append("malformed manifest entry")
            continue
        digest, relative = parts
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or Path(relative).is_absolute() or ".." in Path(relative).parts or relative in listed:
            errors.append("unsafe or duplicate manifest entry")
        listed[relative] = digest
    actual = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file() and path.name != "MANIFEST.sha256"}
    if set(listed) != set(actual):
        errors.append("manifest file set mismatch")
    for relative, digest in listed.items():
        if actual.get(relative) != digest:
            errors.append(f"manifest digest mismatch:{relative}")
    return errors


def validate_return(root: Path) -> dict:
    errors = []
    missing = sorted(name for name in REQUIRED_RETURN_FILES if not (root / name).is_file())
    if missing:
        errors.append("missing:" + ",".join(missing))
        return {"status": "FAIL", "errors": errors}
    for name in REQUIRED_RETURN_FILES - {"50_TEST_RESULTS.junit.xml", "MANIFEST.sha256"}:
        try:
            json.loads((root / name).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"malformed:{name}")
    errors.extend(root_manifest_ok(root))
    hygiene = json.loads((root / "43_ARTIFACT_HYGIENE.json").read_text(encoding="utf-8"))
    if hygiene.get("status") != "PASS" or hygiene.get("match_count") != 0 or hygiene.get("errors") != [] or hygiene.get("scanner_executed") is not True:
        errors.append("artifact hygiene failed")
    zero = json.loads((root / "40_ZERO_REAL_DATA.json").read_text(encoding="utf-8"))
    if any(value != 0 for key, value in zero.items() if key.endswith(("attempts", "lists", "stats", "opens", "bytes", "writes", "executions", "calls"))):
        errors.append("real-data or parser counters are nonzero")
    network = json.loads((root / "41_ZERO_UNEXPECTED_NETWORK.json").read_text(encoding="utf-8"))
    if network.get("unexpected_network_destination_count") != 0 or len(network.get("unique_destinations", [])) != 1:
        errors.append("network destination guard failed")
    registry = json.loads((root / "51_ACCEPTANCE_REGISTRY.json").read_text(encoding="utf-8"))
    if registry.get("status") != "PASS":
        errors.append("acceptance registry is not PASS")
    post = json.loads((root / "45_DSM_STATE_DELTA.json").read_text(encoding="utf-8"))
    for key in ("unauthorized_global_delta_count", "unauthorized_business_share_delta_count", "existing_proposalops_identity_mutation_count", "t3_secret_files_retained", "t3_recurring_tasks_enabled"):
        if post.get(key) != 0:
            errors.append(f"post-run state gate failed:{key}")
    scan_result = scan(root)
    if scan_result["match_count"]:
        errors.append("return artifact contains secret-shaped content")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "artifact_secret_shaped_match_count": scan_result["match_count"], "manifest_status": "PASS" if not root_manifest_ok(root) else "FAIL"}


def validate_handoff(root: Path) -> dict:
    errors = []
    if not (root / "MANIFEST.sha256").is_file():
        errors.append("handoff manifest missing")
    if not (root / "proposalops-syn-t3-image.tar").is_file():
        errors.append("handoff image missing")
    if (root / "MANIFEST.sha256").is_file():
        errors.extend(root_manifest_ok(root))
    scan_result = scan(root)
    if scan_result["match_count"]:
        errors.append("handoff contains secret-shaped content")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "artifact_secret_shaped_match_count": scan_result["match_count"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--return-root", type=Path)
    parser.add_argument("--handoff-root", type=Path)
    args = parser.parse_args()
    if bool(args.return_root) == bool(args.handoff_root):
        parser.error("choose exactly one root")
    result = validate_return(args.return_root.resolve()) if args.return_root else validate_handoff(args.handoff_root.resolve())
    print(json.dumps(result, sort_keys=True))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
