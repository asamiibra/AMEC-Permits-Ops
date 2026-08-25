#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ACCEPTED_V23 = "4925518b35b58956aaa5870f226af5e57d14b610"
V23_TREE = "9dafcf25ac59d4dc2940c03bb081206d7f2820fa"
STORAGE_BLOBS = {
    "backend/app/storage/smb.py": "ad3720c23a9b2d9f65145b32896f8fec60372911",
    "backend/app/storage/external.py": "2e4c8ee0bf4b91ecf5b66894751f750a9179af19",
    "backend/app/storage/port.py": "2a280b4c06f85fc75812c69b7509fc15f2945507",
    "backend/app/storage/factory.py": "fa5836adc7abf040acf7354c0377cb88f0034c8b",
}
BASE_IMAGE = "python:3.12-slim-trixie@sha256:876416ecde9aca2bcc90e1fb0c7a9500bbf749f5788b70f82d4c5a5c2357f8b4"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def source_manifest(repo: Path) -> dict:
    rows = []
    for path in sorted(git(repo, "ls-tree", "-r", "--name-only", ACCEPTED_V23).splitlines()):
        if not path.startswith(("backend/app/storage/", "scripts/synology_t3/", "contracts/amec/synology_t3/")):
            continue
        blob = git(repo, "rev-parse", f"{ACCEPTED_V23}:{path}")
        content = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=repo)
        rows.append({"path": path, "blob_sha": blob, "sha256": hashlib.sha256(content).hexdigest()})
    return {"repo": "asamiibra/AMEC-Permits-Ops", "candidate_sha": ACCEPTED_V23, "candidate_tree": V23_TREE, "rows": rows}


def create_bundle(repo: Path, output: Path, run_id: str) -> Path:
    bundle = output / f"ProposalOps_SYN_T3_Handoff_{run_id}"
    bundle.mkdir(parents=True, exist_ok=True)
    write_json(bundle / "00_AUTHORIZATION.json", {"workstream": "SYN-T3-COMBINED", "synthetic_only": True, "real_amec_data_authorized": False, "accepted_v23_sha": ACCEPTED_V23, "owner_dsm_mutations": ["dedicated synthetic share", "two non-admin test identities", "synthetic fixtures", "disable test identities after run"]})
    write_json(bundle / "01_APPLICATION_IDENTITY.json", {"repository": "asamiibra/AMEC-Permits-Ops", "accepted_v23_sha": ACCEPTED_V23, "accepted_v23_tree": V23_TREE, "smbprotocol": "1.15.0", "storage_blobs": STORAGE_BLOBS})
    write_json(bundle / "02_STORAGE_BLOB_MANIFEST.json", {"storage_blobs": STORAGE_BLOBS, "storage_blob_delta": 0, "implementation_change_authorized": False})
    write_json(bundle / "03_STAGE1R_REFERENCE.json", {"run_id": "20260821T225757Z-24888", "owner_attested_handoff_sha256": "203153beead97910785a4539924bb6b715373466dadec66414a03f68fa7e0172", "base_return_sha256": "cb128fc21353dc72a6a45b91e7e5f04ad71e3fa69b105c6a9fea68c1624ecd40", "completion_archive_sha256": "6f810f0ce050241614d1c7e2cb0796a2715d55728c376f1e6905bfd7fc71da1a", "complete": True, "rerun_authority": False})
    write_json(bundle / "04_T2_SKIP_OWNER_DECISION.json", {"separate_syn_t2_executed": False, "decision": "T2-equivalent protocol criteria are absorbed into T3 against the isolated synthetic DSM share"})
    write_json(bundle / "05_T3_TEST_SPEC.json", {"target_share": "ProposalOps-T3-Synthetic", "target_root": "cert/v1", "positive_identity": "proposalops_t3_ro", "negative_identity": "proposalops_t3_denied", "port": 445, "require_signing": True, "require_encryption": True, "real_amec_access": False, "parser_classifier_llm": False, "managed_write_lane": False, "allowed_warnings": ["REAL_SMB_SERVER_SIDE_PAGINATION", "REAL_SMB_HARD_OPERATION_ABORT", "REAL_NAS_RESTART_RECOVERY", "T3_DSM_MUTATION_RACE", "REAL_DSM_REPARSE_REFERRAL", "PRODUCTION_PRIVATE_PATH"]})
    write_json(bundle / "03_FIXTURE_MANIFEST_PLACEHOLDER.json", {"generated_by": "fixture_manifest.py", "root": "cert/v1", "entry_count": 270})
    write_json(bundle / "06_IMAGE_BUILD_POLICY.json", {"platform": "linux/amd64", "base_image": BASE_IMAGE, "credentials_in_image": False, "business_content_in_image": False, "source_commit": ACCEPTED_V23})
    write_json(bundle / "SOURCE_MANIFEST.json", source_manifest(repo))
    for name in ("run_t3_owner_dsm.sh", "seed_t3_synthetic_share.sh", "verify_t3_dsm_state.sh", "validate_t3_return.py", "fixture_manifest.py", "OWNER_DSM_T3_OPERATOR_INSTRUCTIONS.md", "OWNER_DSM_T3_ATTESTATION_TEMPLATE.json"):
        shutil.copy2(repo / "scripts/synology_t3" / name, bundle / name)
    shutil.copytree(repo / "scripts/synology_t3", bundle / "harness_source", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    staging = bundle / "fixture_staging"
    try:
        from scripts.synology_t3.fixture_manifest import write_manifest
    except ModuleNotFoundError:
        from fixture_manifest import write_manifest
    write_manifest(staging, bundle / "13_FIXTURE_MANIFEST.json")
    (bundle / "03_FIXTURE_MANIFEST_PLACEHOLDER.json").unlink()
    return bundle


def finalize(bundle: Path) -> None:
    image = bundle / "proposalops-syn-t3-image.tar"
    if not image.is_file():
        raise SystemExit("image tar missing")
    metadata = json.loads((bundle / "06_IMAGE_BUILD_POLICY.json").read_text(encoding="utf-8"))
    metadata.update({"image_tar_sha256": hashlib.sha256(image.read_bytes()).hexdigest()})
    write_json(bundle / "06_IMAGE_BUILD_POLICY.json", metadata)
    manifest = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.name not in {"MANIFEST.sha256"}:
            manifest.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle).as_posix()}")
    (bundle / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    archive = bundle.with_suffix(".tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(bundle, arcname=bundle.name, recursive=True)
    print(json.dumps({"bundle": str(bundle), "archive": str(archive), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "status": "PASS"}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--finalize", type=Path)
    args = parser.parse_args()
    if args.finalize:
        finalize(args.finalize.resolve())
    else:
        print(json.dumps({"bundle": str(create_bundle(args.repo_root.resolve(), args.output.resolve(), args.run_id)), "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
