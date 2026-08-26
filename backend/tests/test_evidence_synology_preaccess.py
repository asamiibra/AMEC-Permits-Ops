from __future__ import annotations

import json

import pytest

from scripts.synology_preaccess.generate_evidence import EvidenceUnavailable, V21_SHA, build_registry

CANDIDATE_SHA = "f" * 40
CANDIDATE_TREE = "e" * 40


RAW_FILES = (
    "entry_git.txt", "phase5_refs_entry.txt", "phase5_overlap_entry.txt", "diff_scope.txt",
    "preaccess_runner.json", "targeted.junit.xml", "targeted.log", "managed_regression.junit.xml", "managed_regression.log",
    "source_intake_regression.junit.xml", "source_intake_regression.log", "full_backend.junit.xml", "full_backend.log", "compileall.log", "secret_scan.json",
    "postcommit_git.txt", "phase5_refs_exit.txt", "phase5_overlap_exit.txt", "remote_head.txt",
)
TARGETED_NAMES = (
    "test_direct_open_without_explicit_length_rejected", "test_direct_oversize_open_rejected_before_fake_open",
    "test_explicit_bounded_open_works", "test_zero_length_direct_open_is_safe", "test_helper_file_budget_remains_effective",
    "test_helper_total_run_budget_remains_effective", "test_stability_does_not_count_observation_before_interval",
)


def junit(names, failures=0):
    cases = "".join(f'<testcase classname="synthetic" name="{name}"/>' for name in names)
    return f'<testsuite tests="{len(names)}" failures="{failures}" errors="0" skipped="0">{cases}</testsuite>\n'


def write_fixture(root, *, failed=False, runner=True, scanner=None):
    raw = root / "raw"
    raw.mkdir(parents=True)
    for name in RAW_FILES:
        (raw / name).write_text("", encoding="utf-8")
    (raw / "entry_git.txt").write_text(f"HEAD={CANDIDATE_SHA}\nPARENT={V21_SHA}\nTREE={CANDIDATE_TREE}\n", encoding="utf-8")
    (raw / "postcommit_git.txt").write_text(f"STATUS_CLEAN=true\nHEAD={CANDIDATE_SHA}\nPARENT={V21_SHA}\n", encoding="utf-8")
    (raw / "remote_head.txt").write_text(f"repair_sha={CANDIDATE_SHA}\nvalidation_sha=" + "b" * 40 + f"\nvalidation_parent={CANDIDATE_SHA}\nvalidation_changed_paths=1\nvalidation_workflow_only=true\n", encoding="utf-8")
    (raw / "phase5_refs_entry.txt").write_text("a" * 40 + " refs/heads/phase5-synthetic\n", encoding="utf-8")
    (raw / "phase5_refs_exit.txt").write_text("a" * 40 + " refs/heads/phase5-synthetic\n", encoding="utf-8")
    (raw / "compileall.log").write_text("COMPILEALL_EXIT=0\n", encoding="utf-8")
    (raw / "preaccess_runner.json").write_text(json.dumps({"status": "PASS", "runner_executed": runner, "unexpected_network_destinations": [], "counters": {name: 0 for name in ("smb_connection_attempts", "synology_connection_attempts", "dsm_api_calls", "real_amec_reads", "real_amec_bytes", "source_write_attempts", "nas_write_attempts")}}), encoding="utf-8")
    (raw / "secret_scan.json").write_text(json.dumps(scanner or {"scanner_executed": True, "files_scanned": 1, "patterns_checked": ["GHP_TOKEN"], "match_count": 0, "matches": [], "errors": [], "status": "PASS"}), encoding="utf-8")
    (raw / "targeted.junit.xml").write_text(junit(TARGETED_NAMES, int(failed)), encoding="utf-8")
    for name in ("managed_regression.junit.xml", "source_intake_regression.junit.xml", "full_backend.junit.xml"):
        (raw / name).write_text(junit(("synthetic_pass",), int(failed)), encoding="utf-8")
    (root / "source_manifest.json").write_text(json.dumps({"repo": "asamiibra/AMEC-Permits-Ops", "candidate_sha": CANDIDATE_SHA, "rows": [{"repo": "asamiibra/AMEC-Permits-Ops", "candidate_sha": CANDIDATE_SHA, "path": path, "blob_sha": "c" * 40, "sha256": "d" * 64} for path in ("backend/app/storage/smb.py", "backend/app/storage/external.py", "scripts/synology_preaccess/generate_evidence.py")]}, indent=2), encoding="utf-8")
    return raw


def test_evidence_registry_has_90_distinct_checks_without_invariant_rounds(tmp_path):
    raw = write_fixture(tmp_path)
    checks, _ = build_registry(raw, artifact_root=tmp_path)
    assert len(checks) >= 90
    assert len({item["assertion"].lower() for item in checks}) == len(checks)
    assert all("round" not in item["assertion"].lower() for item in checks)
    assert all(item["independence_basis"] for item in checks)


def test_evidence_generator_cannot_complete_without_junit(tmp_path):
    raw = write_fixture(tmp_path)
    (raw / "full_backend.junit.xml").unlink()
    with pytest.raises(EvidenceUnavailable, match="missing raw evidence"):
        build_registry(raw, artifact_root=tmp_path)


def test_evidence_generator_cannot_complete_with_failed_junit(tmp_path):
    raw = write_fixture(tmp_path, failed=True)
    with pytest.raises(EvidenceUnavailable, match="failed JUnit"):
        build_registry(raw, artifact_root=tmp_path)


def test_zero_access_is_not_assumed_when_runner_missing(tmp_path):
    raw = write_fixture(tmp_path, runner=False)
    with pytest.raises(EvidenceUnavailable, match="runner was not executed"):
        build_registry(raw, artifact_root=tmp_path)


def test_missing_scanner_is_not_executed(tmp_path):
    raw = write_fixture(tmp_path)
    (raw / "secret_scan.json").unlink()
    with pytest.raises(EvidenceUnavailable, match="missing raw evidence"):
        build_registry(raw, artifact_root=tmp_path)


def test_scanner_error_cannot_produce_all_pass(tmp_path):
    raw = write_fixture(tmp_path, scanner={"scanner_executed": True, "files_scanned": 1, "patterns_checked": [], "match_count": 0, "matches": [], "errors": ["synthetic"], "status": "FAIL"})
    checks, _ = build_registry(raw, artifact_root=tmp_path)
    assert any(item["result"] == "FAIL" for item in checks if item["requirement_id"] == "SECRET")
