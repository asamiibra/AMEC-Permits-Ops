#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
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

REQUIRED_RETURN_FILES = {
    "00_AUTHORIZATION.json", "01_APPLICATION_IDENTITY.json", "02_HARNESS_IDENTITY.json", "03_STAGE1R_REFERENCE.json", "04_T2_SKIP_OWNER_DECISION.json",
    "10_DSM_PRE_STATE.json", "11_TEST_SHARE_IDENTITY.json", "12_TEST_ACCOUNT_POLICY.json", "13_FIXTURE_MANIFEST.json", "14_NETWORK_DESTINATION_POLICY.json", "15_CONTAINER_IDENTITY.json",
    "20_SMB_SESSION_SECURITY.json", "21_HEALTH.json", "22_CAPABILITIES.json", "23_STAT_RESULTS.json", "24_READ_HASH_RESULTS.json", "25_RANGE_STREAM_RESULTS.json", "26_LISTING_RESULTS.json", "27_UNICODE_PATH_RESULTS.json", "28_STABILITY_RESULTS.json", "29_MUTATION_RACE_RESULTS.json",
    "30_RO_ACL_NEGATIVES.json", "31_DENIED_IDENTITY_RESULTS.json", "32_MISSING_SHARE_OBJECT_RESULTS.json", "33_SESSION_ISOLATION.json", "34_RECONNECT_RESULTS.json",
    "40_ZERO_REAL_DATA.json", "41_ZERO_UNEXPECTED_NETWORK.json", "42_SECRET_HYGIENE.json", "43_ARTIFACT_HYGIENE.json", "44_DSM_POST_STATE.json", "45_DSM_STATE_DELTA.json",
    "48_ACCESS_LEDGER.json", "49_CHECKS.json", "50_TEST_RESULTS.junit.xml", "51_ACCEPTANCE_REGISTRY.json", "52_FINAL_HANDOFF.json", "SOURCE_MANIFEST.json", "HARNESS_MANIFEST.json", "MANIFEST.sha256",
}
PATTERNS = (
    ("GHP_TOKEN", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PRIVATE_KEY_MARKER", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("SMB_EXTERNAL_PASSWORD", re.compile(r"SMB_EXTERNAL_PASSWORD\s*=\s*(\S+)")),
)


def scan(root: Path) -> dict:
    return scan_text_tree(root, excluded_names={"43_ARTIFACT_HYGIENE.json"})


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
    try:
        pre = json.loads((root / "10_DSM_PRE_STATE.json").read_text(encoding="utf-8"))
        post = json.loads((root / "44_DSM_POST_STATE.json").read_text(encoding="utf-8"))
        errors.extend(validate_state(pre, "PRE"))
        errors.extend(validate_state(post, "POST"))
        comparison = compare_states(pre, post)
        errors.extend(comparison["schema_errors"])
        if comparison["UNAUTHORIZED_DSM_GLOBAL_DELTA_COUNT"] != 0 or comparison["UNAUTHORIZED_BUSINESS_SHARE_DELTA_COUNT"] != 0 or comparison["EXISTING_PROPOSALOPS_IDENTITY_MUTATION_COUNT"] != 0:
            errors.append("immutable DSM/business/identity field changed")
        if post.get("proposalops_t3_ro_enabled") is not False or post.get("proposalops_t3_denied_enabled") is not False or post.get("t3_secret_files_retained") != 0 or post.get("t3_recurring_tasks_enabled") != 0 or post.get("t3_task_removed") is not True:
            errors.append("cleanup proof is not exact")
    except (json.JSONDecodeError, KeyError) as exc:
        errors.append(f"state comparison failed:{type(exc).__name__}")
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
    if registry.get("status") not in {"OWNER_DSM_SYNTHETIC_RETURN_READY_FOR_INDEPENDENT_ACCEPTANCE", "PASS"}:
        errors.append("return registry is not candidate-ready")
    if registry.get("T3_RETURN_STATUS") not in {"PASS", "READY"}:
        errors.append("T3_RETURN_STATUS is not PASS/READY")
    distinct = registry.get("distinct_assertions")
    if not isinstance(distinct, int) or distinct < 120:
        errors.append("runtime assertion count is below 120")
    if registry.get("PASS") != distinct or registry.get("FAIL") != 0 or registry.get("WARN") != 0 or registry.get("ENV_BLOCKED") != 0 or registry.get("NOT_EXECUTED") != 0 or registry.get("UNRESOLVED_EVIDENCE_REF_COUNT") != 0 or registry.get("NORMALIZED_ASSERTION_DUPLICATE_COUNT") != 0 or registry.get("DUPLICATE_EVIDENCE_TUPLE_COUNT") != 0 or registry.get("SELF_REFERENCE_COUNT") != 0:
        errors.append("execution-derived registry contains failures or evidence defects")
    try:
        junit_root = ET.parse(root / "50_TEST_RESULTS.junit.xml").getroot()
        junit_values = {key: int(junit_root.attrib.get(key, "-1")) for key in ("tests", "failures", "errors")}
        if junit_values["tests"] != distinct or junit_values["failures"] != 0 or junit_values["errors"] != 0:
            errors.append("JUnit does not match execution-derived registry")
    except (ET.ParseError, ValueError):
        errors.append("JUnit is malformed")
    post = json.loads((root / "45_DSM_STATE_DELTA.json").read_text(encoding="utf-8"))
    for key in ("UNAUTHORIZED_DSM_GLOBAL_DELTA_COUNT", "UNAUTHORIZED_BUSINESS_SHARE_DELTA_COUNT", "EXISTING_PROPOSALOPS_IDENTITY_MUTATION_COUNT", "t3_secret_files_retained", "t3_recurring_tasks_enabled"):
        if post.get(key) != 0:
            errors.append(f"post-run state gate failed:{key}")
    scan_result = scan(root)
    if scan_result["match_count"]:
        errors.append("return artifact contains secret-shaped content")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "artifact_secret_shaped_match_count": scan_result["match_count"], "manifest_status": "PASS" if not root_manifest_ok(root) else "FAIL"}


def validate_handoff(root: Path) -> dict:
    errors = []
    required = {"00_AUTHORIZATION.json", "01_APPLICATION_IDENTITY.json", "02_STORAGE_BLOB_MANIFEST.json", "03_STAGE1R_REFERENCE.json", "04_T2_SKIP_OWNER_DECISION.json", "05_T3_TEST_SPEC.json", "06_IMAGE_BUILD_POLICY.json", "07_DOCKER_IMAGE_INSPECT.json", "08_PYTHON_VERSION.txt", "09_OPENSSL_VERSION.txt", "10_PIP_FREEZE.txt", "13_FIXTURE_MANIFEST.json", "SOURCE_MANIFEST.json", "HARNESS_MANIFEST.json", "proposalops-syn-t3-image.tar", "run_t3_owner_dsm.sh", "seed_t3_synthetic_share.sh", "verify_t3_dsm_state.sh", "finalize_t3_return.py", "validate_t3_return.py", "dsm_state_schema.py", "OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md", "OWNER_DSM_T3_ATTESTATION_TEMPLATE.json", "MANIFEST.sha256"}
    missing = sorted(name for name in required if not (root / name).exists())
    if missing:
        errors.append("missing:" + ",".join(missing))
    if not (root / "fixture_staging" / "cert" / "v1").is_dir():
        errors.append("fixture staging root is not cert/v1")
    if not (root / "harness_source").is_dir():
        errors.append("harness source missing")
    if (root / "06_IMAGE_BUILD_POLICY.json").is_file():
        policy = json.loads((root / "06_IMAGE_BUILD_POLICY.json").read_text(encoding="utf-8"))
        for key in ("image_ref", "image_id", "image_tar_sha256", "application_sha", "harness_sha"):
            if not policy.get(key):
                errors.append(f"image policy field missing:{key}")
        if (root / "07_DOCKER_IMAGE_INSPECT.json").is_file():
            image = json.loads((root / "07_DOCKER_IMAGE_INSPECT.json").read_text(encoding="utf-8"))
            labels = image.get("Config", {}).get("Labels", {}) or {}
            if image.get("Id") != policy.get("image_id"):
                errors.append("policy/image inspect ID mismatch")
            if labels.get("org.opencontainers.image.revision") != policy.get("harness_sha") or labels.get("org.opencontainers.image.proposalops-application-revision") != policy.get("application_sha") or labels.get("org.opencontainers.image.synthetic-only") != "true":
                errors.append("policy/image labels mismatch")
    if (root / "MANIFEST.sha256").is_file():
        errors.extend(root_manifest_ok(root))
    scan_result = scan(root)
    if scan_result["match_count"]:
        errors.append("handoff contains secret-shaped content")
    if (root / "T3_ASSERTION_CATALOG.json").is_file():
        catalog = json.loads((root / "T3_ASSERTION_CATALOG.json").read_text(encoding="utf-8"))
        if catalog.get("distinct_assertions", 0) < 120:
            errors.append("assertion catalog has fewer than 120 assertions")
        if any(str(row.get("assertion_id", "")).startswith("fixture_integrity::") for row in catalog.get("assertions", [])):
            errors.append("catalog uses stale fixture_integrity assertion semantics")
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
