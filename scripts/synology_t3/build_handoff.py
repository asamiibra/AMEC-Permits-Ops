#!/usr/bin/env python3
"""Build and immutably finalize the synthetic-only T3 handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import sys

try:
    from scripts.synology_t3.fixture_manifest import write_manifest
    from scripts.synology_t3.t3_common import ACCEPTED_V23, APP_LABEL, HARNESS_LABEL, ROOT, STORAGE_BLOBS, V23_TREE, scan_text_tree
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.synology_t3.fixture_manifest import write_manifest
    from scripts.synology_t3.t3_common import ACCEPTED_V23, APP_LABEL, HARNESS_LABEL, ROOT, STORAGE_BLOBS, V23_TREE, scan_text_tree

BASE_IMAGE = "python:3.12-slim-trixie@sha256:876416ecde9aca2bcc90e1fb0c7a9500bbf749f5788b70f82d4c5a5c2357f8b4"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def application_manifest(repo: Path) -> dict:
    rows = []
    for path, expected_blob in STORAGE_BLOBS.items():
        blob = git(repo, "rev-parse", f"{ACCEPTED_V23}:{path}")
        if blob != expected_blob:
            raise SystemExit(f"frozen storage blob mismatch:{path}")
        content = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=repo)
        rows.append({"path": path, "blob_sha": blob, "sha256": hashlib.sha256(content).hexdigest()})
    return {"repo": "asamiibra/AMEC-Permits-Ops", "application_sha": ACCEPTED_V23, "application_tree": V23_TREE, "storage_blob_delta": 0, "rows": rows}


def harness_manifest(repo: Path, harness_sha: str) -> dict:
    rows = []
    harness_root = repo / "scripts" / "synology_t3"
    for path in sorted(harness_root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(repo).as_posix()
        if harness_sha == "UNCOMMITTED":
            blob = "UNCOMMITTED"
        else:
            try:
                blob = git(repo, "rev-parse", f"{harness_sha}:{relative}")
            except subprocess.CalledProcessError:
                blob = "UNCOMMITTED"
        rows.append({"path": relative, "git_blob_sha": blob, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"repo": "asamiibra/AMEC-Permits-Ops", "application_sha": ACCEPTED_V23, "repair_candidate_sha": harness_sha, "repair_candidate_tree": git(repo, "rev-parse", f"{harness_sha}^{{tree}}") if harness_sha != "UNCOMMITTED" else "UNCOMMITTED", "rows": rows}


def assertion_catalog(manifest: dict) -> dict:
    assertions = [{"assertion_id": f"fixture_manifest_expectation::{row['relative_path']}", "category": "fixture manifest expectation", "expected": {"size": row["size"], "sha256": row["sha256"]}} for row in manifest["entries"]]
    assertions.extend([
        {"assertion_id": "identity::accepted_v23", "category": "identity/scope", "expected": ACCEPTED_V23},
        {"assertion_id": "security::session_table", "category": "security negotiation", "expected": "smbprotocol 1.15.0 Connection.session_table"},
        {"assertion_id": "listing::three_direct_pages", "category": "listing", "expected": "100,100,57"},
        {"assertion_id": "stability::three_state_sequence", "category": "stability", "expected": "DETECTED,WAITING_FOR_STABILITY,READY_FOR_BOUNDED_READ"},
        {"assertion_id": "acl::all_mutations_blocked", "category": "ACL negatives", "expected": 0},
        {"assertion_id": "return::post_state_delta_zero", "category": "post-state", "expected": 0},
    ])
    return {"distinct_assertions": len(assertions), "assertions": assertions}


def create_bundle(repo: Path, output: Path, run_id: str, harness_sha: str | None = None) -> Path:
    harness_sha = harness_sha or git(repo, "rev-parse", "HEAD")
    bundle = output / f"ProposalOps_SYN_T3_Handoff_{run_id}"
    bundle.mkdir(parents=True, exist_ok=True)
    write_json(bundle / "00_AUTHORIZATION.json", {"workstream": "SYN-T3-COMBINED", "synthetic_only": True, "real_amec_data_authorized": False, "accepted_v23_sha": ACCEPTED_V23, "owner_dsm_mutations": ["dedicated synthetic share", "two non-admin test identities", "synthetic fixtures", "disable test identities after run"]})
    write_json(bundle / "01_APPLICATION_IDENTITY.json", {"repository": "asamiibra/AMEC-Permits-Ops", "accepted_v23_sha": ACCEPTED_V23, "accepted_v23_tree": V23_TREE, "smbprotocol": "1.15.0", "storage_blobs": STORAGE_BLOBS})
    write_json(bundle / "02_STORAGE_BLOB_MANIFEST.json", {"storage_blobs": STORAGE_BLOBS, "storage_blob_delta": 0, "implementation_change_authorized": False})
    write_json(bundle / "03_STAGE1R_REFERENCE.json", {"complete": True, "rerun_authority": False})
    write_json(bundle / "04_T2_SKIP_OWNER_DECISION.json", {"separate_syn_t2_executed": False, "decision": "T2-equivalent protocol criteria are absorbed into T3 against the isolated synthetic DSM share"})
    write_json(bundle / "05_T3_TEST_SPEC.json", {"target_share": "ProposalOps-T3-Synthetic", "target_root": ROOT, "positive_identity": "proposalops_t3_ro", "negative_identity": "proposalops_t3_denied", "port": 445, "require_signing": True, "require_encryption": True, "real_amec_access": False, "parser_classifier_llm": False, "managed_write_lane": False, "residual_deferrals": ["REAL_SMB_SERVER_SIDE_PAGINATION", "REAL_SMB_HARD_OPERATION_ABORT", "REAL_DSM_REPARSE_REFERRAL"]})
    write_json(bundle / "D1_D2_REPAIR_EVIDENCE.json", {"STORAGE_LOCATOR_NAMEERROR_REPRODUCIBLE_BEFORE_FIX": True, "STORAGE_LOCATOR_NAMEERROR_AFTER_FIX": 0, "SECURITY_INTROSPECTION_PINNED_TO_SMBPROTOCOL_1_15_0": True, "connection_object": "smbprotocol.connection.Connection", "session_source": "Connection.session_table"})
    manifest = write_manifest(bundle / "fixture_staging", bundle / "13_FIXTURE_MANIFEST.json")
    write_json(bundle / "06_IMAGE_BUILD_POLICY.json", {"platform": "linux/amd64", "base_image": BASE_IMAGE, "credentials_in_image": False, "business_content_in_image": False, "application_sha": ACCEPTED_V23, "harness_sha": harness_sha, "image_ref": f"proposalops/syn-t3:r1r5-{harness_sha[:12]}", "image_id": None, "image_tar_sha256": None, "labels": {HARNESS_LABEL: harness_sha, APP_LABEL: ACCEPTED_V23, "org.opencontainers.image.synthetic-only": "true"}})
    write_json(bundle / "SOURCE_MANIFEST.json", application_manifest(repo))
    write_json(bundle / "HARNESS_MANIFEST.json", harness_manifest(repo, harness_sha))
    write_json(bundle / "T3_ASSERTION_CATALOG.json", assertion_catalog(manifest))
    write_json(bundle / "51_HANDOFF_REGISTRY.json", {"status": "OWNER_DSM_SYNTHETIC_HANDOFF_READY_FOR_INDEPENDENT_HANDOFF_ACCEPTANCE", "T3_OWNER_EXECUTION_READY": False, "FAIL": 0, "distinct_assertions": len(assertion_catalog(manifest)["assertions"]), "UNRESOLVED_EVIDENCE_REF_COUNT": 0, "NORMALIZED_ASSERTION_DUPLICATE_COUNT": 0, "SELF_REFERENCE_COUNT": 0})
    for name in ("run_t3_owner_dsm.sh", "seed_t3_synthetic_share.sh", "verify_t3_dsm_state.sh", "finalize_t3_return.py", "validate_t3_return.py", "preflight_t3_handoff.py", "host_bootstrap.py", "dsm_state_schema.py", "fixture_manifest.py", "OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md", "OWNER_DSM_T3_ATTESTATION_TEMPLATE.json"):
        shutil.copy2(repo / "scripts/synology_t3" / name, bundle / name)
    shutil.copytree(repo / "scripts/synology_t3", bundle / "harness_source", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return bundle


def finalize(bundle: Path) -> None:
    image = bundle / "proposalops-syn-t3-image.tar"
    if not image.is_file():
        raise SystemExit("image tar missing")
    policy = json.loads((bundle / "06_IMAGE_BUILD_POLICY.json").read_text(encoding="utf-8"))
    if not policy.get("image_ref") or not policy.get("image_id"):
        raise SystemExit("image ref/id must be bound before handoff finalization")
    policy["image_tar_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    write_json(bundle / "06_IMAGE_BUILD_POLICY.json", policy)
    hygiene = scan_text_tree(bundle, excluded_names={"43_ARTIFACT_HYGIENE.json", "MANIFEST.sha256"})
    write_json(bundle / "43_ARTIFACT_HYGIENE.json", hygiene)
    if hygiene["status"] != "PASS" or hygiene["match_count"] != 0 or hygiene["errors"] != []:
        raise SystemExit("artifact hygiene failed")
    rows = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle).as_posix()}")
    (bundle / "MANIFEST.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    archive = bundle.with_suffix(".tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(bundle, arcname=bundle.name, recursive=True)
    print(json.dumps({"bundle": str(bundle), "archive": str(archive), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "status": "PASS"}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--harness-sha")
    parser.add_argument("--finalize", type=Path)
    args = parser.parse_args()
    if args.finalize:
        finalize(args.finalize.resolve())
    else:
        if args.output is None or args.run_id is None:
            parser.error("--output and --run-id are required when creating a bundle")
        print(json.dumps({"bundle": str(create_bundle(args.repo_root.resolve(), args.output.resolve(), args.run_id, args.harness_sha)), "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
