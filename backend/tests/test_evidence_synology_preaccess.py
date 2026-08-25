from __future__ import annotations

import json

import pytest

from scripts.synology_preaccess.generate_evidence import EvidenceUnavailable, build_registry


RAW_NAMES = (
    "entry_git.txt", "phase5_refs_entry.txt", "phase5_overlap_entry.txt", "diff_scope.txt",
    "targeted.junit.xml", "targeted.log", "preaccess_runner.json", "managed_regression.junit.xml",
    "source_intake_regression.junit.xml", "full_backend.junit.xml", "full_backend.log",
    "compileall.log", "secret_scan.txt", "postcommit_git.txt", "phase5_refs_exit.txt", "remote_head.txt",
)


def junit(*, failures=0):
    return f'<testsuite tests="1" failures="{failures}" errors="0" skipped="0"><testcase classname="synthetic" name="check"/></testsuite>\n'


def write_raw(path, *, failed=False, runner_executed=True):
    path.mkdir()
    for name in RAW_NAMES:
        (path / name).write_text("", encoding="utf-8")
    for name in ("targeted.junit.xml", "managed_regression.junit.xml", "source_intake_regression.junit.xml", "full_backend.junit.xml"):
        (path / name).write_text(junit(failures=int(failed)), encoding="utf-8")
    (path / "phase5_refs_entry.txt").write_text("origin/phase5=head\n", encoding="utf-8")
    (path / "phase5_refs_exit.txt").write_text("origin/phase5=head\n", encoding="utf-8")
    (path / "compileall.log").write_text("COMPILEALL_EXIT=0\n", encoding="utf-8")
    (path / "preaccess_runner.json").write_text(json.dumps({
        "status": "PASS", "runner_executed": runner_executed, "pytest_exit_code": 0,
        "counters": {name: 0 for name in (
            "smb_connection_attempts", "synology_connection_attempts", "dsm_api_calls",
            "real_amec_reads", "real_amec_bytes", "source_write_attempts", "nas_write_attempts",
        )}, "unexpected_network_destinations": [],
    }), encoding="utf-8")


def test_evidence_registry_has_no_self_references(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw)
    checks, _ = build_registry(raw)
    assert len(checks) >= 180
    assert all("50_ACCEPTANCE_REGISTRY" not in ref for item in checks for ref in item["evidence_refs"])


def test_evidence_generator_cannot_complete_without_junit(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw)
    (raw / "full_backend.junit.xml").unlink()
    with pytest.raises(EvidenceUnavailable, match="missing raw evidence"):
        build_registry(raw)


def test_evidence_generator_cannot_complete_with_failed_junit(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw, failed=True)
    with pytest.raises(EvidenceUnavailable, match="failed JUnit"):
        build_registry(raw)


def test_zero_access_is_not_assumed_when_runner_missing(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw, runner_executed=False)
    with pytest.raises(EvidenceUnavailable, match="runner was not executed"):
        build_registry(raw)
