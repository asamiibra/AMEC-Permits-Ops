from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.phase5.acceptance import run as generate_acceptance
from scripts.phase5.registry import CANONICAL_ARTIFACTS


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts/amec/phase5"


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    contracts = tmp_path / "contracts"
    evidence = tmp_path / "evidence"
    artifacts = tmp_path / "artifacts"
    contracts.mkdir()
    evidence.mkdir()
    artifacts.mkdir()
    for name in CANONICAL_ARTIFACTS.values():
        source = CONTRACTS / name
        if source.is_file():
            shutil.copy2(source, contracts / name)
    acceptance = artifacts / "acceptance-result.json"
    generate_acceptance(acceptance)
    runtime = {"sqlserver": "PASS", "browser": "PASS", "backend_regression": "PASS", "frontend_regression": "PASS", "frontend_build": "PASS", "authority_denial": "PASS", "observability": "PASS", "security_hygiene": "PASS", "candidate_sha": "LOCAL_PRECOMMIT", "validation_sha": "LOCAL_PRECOMMIT", "new_source_reads": 0, "auto_promotion_enabled": False, "llm_real_content_mode": "DISABLED", "critical_false_promotions": 0}
    (evidence / "runtime-gates.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
    return contracts, evidence, acceptance


def _invoke(contracts: Path, evidence: Path, acceptance: Path, output: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "scripts/phase5")}
    return subprocess.run([sys.executable, "scripts/phase5/phase5_finalize.py", "--evidence-dir", str(evidence), "--acceptance-result", str(acceptance), "--contracts-dir", str(contracts), "--output", str(output)], cwd=ROOT, env=env, capture_output=True, text=True)


def test_finalizer_positive_fixture_invokes_actual_cli(tmp_path):
    contracts, evidence, acceptance = _fixture(tmp_path)
    result = _invoke(contracts, evidence, acceptance, tmp_path / "summary.json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / "summary.json").read_text())["result"] == "PASS"


def _mutations():
    return [
        ("missing_required_evidence", lambda c, e, a: (e / "runtime-gates.json").unlink()),
        ("failed_acceptance", lambda c, e, a: a.write_text(a.read_text().replace('"result": "PASS"', '"result": "FAIL"', 1))),
        ("duplicate_check_id", lambda c, e, a: _mutate_acceptance(a, lambda p: p["checks"].__setitem__(1, {**p["checks"][1], "check_id": p["checks"][0]["check_id"]}))),
        ("duplicate_normalized_assertion", lambda c, e, a: _mutate_acceptance(a, lambda p: p["checks"].__setitem__(1, {**p["checks"][1], "assertion": p["checks"][0]["assertion"], "requirement_id": p["checks"][0]["requirement_id"], "category": p["checks"][0]["category"], "evidence_ids": p["checks"][0]["evidence_ids"]}))),
        ("missing_requirement_id", lambda c, e, a: _mutate_acceptance(a, lambda p: p["checks"][0].__setitem__("requirement_id", ""))),
        ("critical_false_promotion", lambda c, e, a: _mutate_result(c, CANONICAL_ARTIFACTS["validation_results"], "critical_false_promotions", 1)),
        ("new_amec_source_reads", lambda c, e, a: _mutate_runtime(e, "new_source_reads", 1)),
        ("auto_promotion_enabled", lambda c, e, a: _mutate_runtime(e, "auto_promotion_enabled", True)),
        ("llm_real_content", lambda c, e, a: _mutate_runtime(e, "llm_real_content_mode", "ENABLED")),
        ("browser_evidence_missing", lambda c, e, a: _mutate_runtime(e, "browser", "MISSING")),
        ("browser_evidence_failed", lambda c, e, a: _mutate_runtime(e, "browser", "FAIL")),
        ("sqlserver_evidence_missing", lambda c, e, a: _mutate_runtime(e, "sqlserver", "MISSING")),
        ("sqlserver_evidence_failed", lambda c, e, a: _mutate_runtime(e, "sqlserver", "FAIL")),
        ("freeze_digest_mismatch", lambda c, e, a: _mutate_result(c, CANONICAL_ARTIFACTS["validation_results"], "rules_version", "wrong")),
        ("unresolved_acceptance_evidence", lambda c, e, a: _mutate_acceptance(a, lambda p: p["checks"][0].__setitem__("evidence", ["missing/evidence.json"]))),
        ("blank_exit_code", lambda c, e, a: _mutate_runtime(e, "security_hygiene", "")),
        ("zero_byte_required_raw_log", lambda c, e, a: (e / "runtime-gates.json").write_text("")),
        ("candidate_sha_mismatch", lambda c, e, a: _mutate_runtime(e, "candidate_sha", "wrong")),
        ("validation_sha_mismatch", lambda c, e, a: _mutate_runtime(e, "validation_sha", "wrong")),
        ("secret_hygiene_failure", lambda c, e, a: _mutate_runtime(e, "security_hygiene", "FAIL")),
        ("acceptance_check_failure", lambda c, e, a: _mutate_acceptance(a, lambda p: p["checks"][0].__setitem__("result", "FAIL"))),
        ("critical_runtime_failure", lambda c, e, a: _mutate_runtime(e, "critical_false_promotions", 1)),
    ]


def _mutate_acceptance(path: Path, mutate) -> None:
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _mutate_result(contracts: Path, filename: str, key: str, value) -> None:
    path = contracts / filename
    payload = json.loads(path.read_text())
    payload[key] = value
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _mutate_runtime(evidence: Path, key: str, value) -> None:
    path = evidence / "runtime-gates.json"
    payload = json.loads(path.read_text())
    payload[key] = value
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.mark.parametrize("name,mutate", _mutations(), ids=lambda item: item if isinstance(item, str) else None)
def test_actual_finalizer_rejects_every_negative_state(tmp_path, name, mutate):
    contracts, evidence, acceptance = _fixture(tmp_path)
    mutate(contracts, evidence, acceptance)
    result = _invoke(contracts, evidence, acceptance, tmp_path / "summary.json")
    assert result.returncode != 0, f"{name} was accepted: {result.stdout} {result.stderr}"
    assert not (tmp_path / "summary.json").exists()
