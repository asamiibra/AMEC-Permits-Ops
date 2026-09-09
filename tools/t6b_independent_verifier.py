#!/usr/bin/env python3
"""Independent, read-only verifier for the immutable T6-B producer evidence."""

from __future__ import annotations

import hashlib
import json
import sys
import tarfile
from pathlib import Path


EXPECTED_RUN = "34295201328"
EXPECTED_HEAD = "7c3340001ad69e6681c65416d8492998b6a89661"
EXPECTED_CANDIDATE_SHA = "cb88dd82c8bd0541d736ec9f75bb16ef759faf466a8ddd26f1c495035acc4035"
EXPECTED_CANDIDATE_BYTES = 17444


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(root: Path, name: str) -> dict:
    return json.loads((root / name).read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verifier.py EVIDENCE_TAR PRODUCER_CHECKOUT")
    evidence_tar = Path(sys.argv[1]).resolve(strict=True)
    producer_checkout = Path(sys.argv[2]).resolve(strict=True)
    with tarfile.open(evidence_tar, "r:gz") as archive:
        members = archive.getmembers()
        if any(member.name.startswith("/") or ".." in Path(member.name).parts for member in members):
            raise AssertionError("UNSAFE_EVIDENCE_MEMBER")
        names = {member.name for member in members}
        required = {
            "T6B_FINAL_PRODUCER_SUMMARY.json",
            "T6B_FINAL_RELEASE_LEDGER.json",
            "T6B_SQLSERVER_PRE_DB_PROPERTIES.json",
            "T6B_SCHEMA_COMPARISON.json",
            "T6B_TABLE_DELTA_REPORT.json",
            "T6B_PROTECTED_SIDE_EFFECT_REPORT.json",
            "T6B_CLEANUP.json",
            "T6B_EXTERNAL_POSTRUN_CHECK.json",
            "T6B_HARNESS_ADAPTER.json",
        }
        if not required <= names:
            raise AssertionError(f"MISSING_EVIDENCE:{sorted(required - names)}")
        extract = evidence_tar.parent / "independent-extract"
        extract.mkdir(exist_ok=True)
        archive.extractall(extract)

    summary = read_json(extract, "T6B_FINAL_PRODUCER_SUMMARY.json")
    assert summary["T6B_NATIVE_LINUX_X86_64"] == "PASS"
    assert summary["SQLSERVER_2022_T6B_QUALIFICATION"] == "PASS"
    assert summary["T6B_APPLICATION_PERSISTENCE_CLOSED"] is True
    assert summary["T6B_READY_FOR_INDEPENDENT_ACCEPTANCE"] is True
    assert summary["T6B_INDEPENDENT_ACCEPTANCE"] == "NOT_PERFORMED_BY_PRODUCER"
    assert summary["T6B_REQUIRED_TEST_SKIPS"] == 0
    assert all(summary[key] == 0 for key in ("DSM_CONTACTS", "SMB_SOURCE_READS", "REAL_AMEC_SOURCE_BYTES", "PARSER_EXECUTIONS", "LLM_CALLS"))

    ledger = read_json(extract, "T6B_FINAL_RELEASE_LEDGER.json")
    assert ledger["workflow_run_id"] == EXPECTED_RUN
    assert ledger["workflow_head"] == EXPECTED_HEAD
    assert ledger["qualification"] == "PASS"
    candidate = producer_checkout / ".t6b-validation/ProposalOps_SYN_T6B_APPLICATION_PERSISTENCE_CONSUMER.tar.gz"
    assert candidate.stat().st_size == EXPECTED_CANDIDATE_BYTES
    assert sha256(candidate) == EXPECTED_CANDIDATE_SHA == ledger["candidate_sha256"]
    assert ledger["candidate_bytes"] == EXPECTED_CANDIDATE_BYTES

    server = read_json(extract, "T6B_SQLSERVER_PRE_DB_PROPERTIES.json")
    assert server == {"engine_edition": 3, "product_major_version": 16, "product_version": "16.0.4275.2"}
    schema = read_json(extract, "T6B_SCHEMA_COMPARISON.json")
    assert schema["schema_delta"] == 0
    assert schema["before_sha256"] == schema["after_replay_sha256"]
    tables = read_json(extract, "T6B_TABLE_DELTA_REPORT.json")
    assert tables["unexpected_table_delta_count"] == 0
    assert tables["replay_total_row_delta"] == 0
    protected = read_json(extract, "T6B_PROTECTED_SIDE_EFFECT_REPORT.json")
    assert all(value == 0 for value in protected.values())
    cleanup = read_json(extract, "T6B_CLEANUP.json")
    external = read_json(extract, "T6B_EXTERNAL_POSTRUN_CHECK.json")
    assert cleanup == {"ephemeral_password_persisted": False, "sqlserver_container_remains": 0}
    assert external["container_removed"] is True
    assert external["password_material_in_evidence"] is False
    adapter = read_json(extract, "T6B_HARNESS_ADAPTER.json")
    assert adapter["frozen_consumer_archive_hashes_verified"] is True
    assert adapter["scope"] == "server-property probe only"
    print(json.dumps({"result": "T6B_INDEPENDENT_ACCEPTANCE=PASS", "producer_run": EXPECTED_RUN, "producer_head": EXPECTED_HEAD, "verifier": "stdlib-read-only-v1"}, sort_keys=True))


if __name__ == "__main__":
    main()
