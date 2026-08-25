from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.phase5.acceptance import run as generate_acceptance
from scripts.phase5.evidence_validate import run as validate_evidence
from scripts.phase5.registry import CANONICAL_ARTIFACTS, EVIDENCE_PRODUCERS, producer_paths

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts/amec/phase5"
CANDIDATE = "ca60459f2103cbf30e52e05c59b8af6d7714be12"
VALIDATION = "a5e6b9425ead924e35bb55cafc065251de0cb021"
RUN_ID = "r3-test"


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    contracts, evidence = tmp_path / "contracts", tmp_path / "evidence"
    contracts.mkdir(); evidence.mkdir()
    for name in CANONICAL_ARTIFACTS.values():
        shutil.copy2(CONTRACTS / name if False else CONTRACTS / name, contracts / name)
    for producer in EVIDENCE_PRODUCERS:
        paths = producer_paths(producer, evidence)
        paths["raw"].write_text(f"producer={producer}\n", encoding="utf-8")
        paths["meta"].write_text(json.dumps({"producer_id": producer, "candidate_sha": CANDIDATE, "validation_sha": VALIDATION, "run_id": RUN_ID, "exit_code": 0}), encoding="utf-8")
        payload = {"producer_id": producer, "result": "PASS"}
        if producer in {"browser-required-paths", "browser-quality"}:
            payload.update({"required_path_count": 10, "required_path_pass": 10, "required_path_fail": 0, "required_path_skip": 0, "quality_check_count": 7})
        if producer == "sqlserver-bootstrap":
            payload.update({"sqlserver_major": 16, "migration_head": "baseline_phase4_v36_azure_sql"})
        if producer == "sqlserver-targeted":
            payload.update({"gate_count": 16, "failed_count": 0, "skipped_count": 0, "sqlserver_major": 16})
        if producer == "shadow-replay":
            payload.update({"shadow_state": "SHADOW_ONLY", "new_source_reads": 0, "real_content": False, "llm_external_call_count": 0})
        if producer == "source-preflight":
            payload["authority"] = {"promotion_requires_human_review": True, "projection_requires_existing_verified_assertion": True, "auto_promotion_enabled": False}
        if producer in {"classifier-calibration", "classifier-validation", "classifier-holdout", "classifier-cross-context", "classifier-path-counterfactual"}:
            payload["critical_false_promotions"] = 0
        paths["result"].write_text(json.dumps(payload), encoding="utf-8")
    acceptance = tmp_path / "acceptance.json"
    generate_acceptance(acceptance, evidence, False, expected_candidate_sha=CANDIDATE, expected_validation_sha=VALIDATION, expected_run_id=RUN_ID)
    validation = tmp_path / "evidence-validation.json"
    validate_evidence(evidence, acceptance, validation, CANDIDATE, VALIDATION, RUN_ID)
    return contracts, evidence, acceptance, validation


def _invoke(contracts: Path, evidence: Path, acceptance: Path, validation: Path, output: Path, expected: str = CANDIDATE) -> subprocess.CompletedProcess[str]:
    env = {**dict(), "PYTHONPATH": str(ROOT / "scripts/phase5")}
    return subprocess.run([sys.executable, "scripts/phase5/phase5_finalize.py", "--evidence-dir", str(evidence), "--acceptance-result", str(acceptance), "--validation-result", str(validation), "--contracts-dir", str(contracts), "--output", str(output), "--expected-candidate-sha", expected, "--expected-validation-sha", VALIDATION, "--expected-run-id", RUN_ID], cwd=ROOT, env=env, capture_output=True, text=True)


def test_finalizer_positive_fixture_invokes_actual_cli(tmp_path):
    contracts, evidence, acceptance, validation = _fixture(tmp_path)
    result = _invoke(contracts, evidence, acceptance, validation, tmp_path / "summary.json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / "summary.json").read_text())["result"] == "PASS"


@pytest.mark.parametrize("mutation", [
    "bad_expected", "missing_raw", "missing_meta", "missing_result", "zero_raw", "zero_meta", "zero_result",
    "failed_acceptance", "dry_acceptance", "failed_validation", "missing_validation", "wrong_candidate",
    "nonzero_exit", "failed_producer", "not_executed", "invalid_meta", "invalid_result", "missing_contract",
    "canonical_failure", "missing_acceptance", "wrong_candidate_case", "short_candidate", "extra_candidate",
    "empty_evidence", "acceptance_check_failure",
])
def test_actual_finalizer_rejects_every_negative_state(tmp_path, mutation):
    contracts, evidence, acceptance, validation = _fixture(tmp_path)
    if mutation == "bad_expected": expected = "not-a-sha"
    else: expected = CANDIDATE
    if mutation == "missing_raw": producer_paths("sqlserver-targeted", evidence)["raw"].unlink()
    elif mutation == "missing_meta": producer_paths("sqlserver-targeted", evidence)["meta"].unlink()
    elif mutation == "missing_result": producer_paths("sqlserver-targeted", evidence)["result"].unlink()
    elif mutation == "zero_raw": producer_paths("sqlserver-targeted", evidence)["raw"].write_text("")
    elif mutation == "zero_meta": producer_paths("sqlserver-targeted", evidence)["meta"].write_text("")
    elif mutation == "zero_result": producer_paths("sqlserver-targeted", evidence)["result"].write_text("")
    elif mutation in {"failed_producer", "not_executed"}:
        producer_paths("sqlserver-targeted", evidence)["result"].write_text(json.dumps({"result": "NOT_EXECUTED" if mutation == "not_executed" else "FAIL"}))
    elif mutation == "nonzero_exit": producer_paths("sqlserver-targeted", evidence)["meta"].write_text(json.dumps({"candidate_sha": CANDIDATE, "exit_code": 1}))
    elif mutation == "invalid_meta": producer_paths("sqlserver-targeted", evidence)["meta"].write_text("{")
    elif mutation == "invalid_result": producer_paths("sqlserver-targeted", evidence)["result"].write_text("{")
    elif mutation == "failed_acceptance": acceptance.write_text(json.dumps({"result": "FAIL", "checks": []}))
    elif mutation == "dry_acceptance": generate_acceptance(acceptance, None, True)
    elif mutation == "failed_validation": validation.write_text(json.dumps({"result": "FAIL"}))
    elif mutation == "missing_validation": validation.unlink()
    elif mutation in {"wrong_candidate", "wrong_candidate_case"}: producer_paths("sqlserver-targeted", evidence)["meta"].write_text(json.dumps({"candidate_sha": "0" * 40, "exit_code": 0}))
    elif mutation == "short_candidate": expected = "a" * 39
    elif mutation == "extra_candidate": expected = CANDIDATE + "0"
    elif mutation == "missing_contract": (contracts / CANONICAL_ARTIFACTS["rules"]).unlink()
    elif mutation == "canonical_failure": (contracts / CANONICAL_ARTIFACTS["validation_results"]).write_text(json.dumps({"result": "FAIL"}))
    elif mutation == "missing_acceptance": acceptance.unlink()
    elif mutation == "empty_evidence": producer_paths("browser-quality", evidence)["raw"].write_text("")
    elif mutation == "acceptance_check_failure":
        payload = json.loads(acceptance.read_text()); payload["checks"][0]["result"] = "FAIL"; acceptance.write_text(json.dumps(payload))
    result = _invoke(contracts, evidence, acceptance, validation, tmp_path / "summary.json", expected)
    assert result.returncode != 0, f"{mutation} was accepted: {result.stdout} {result.stderr}"
    assert not (tmp_path / "summary.json").exists()
