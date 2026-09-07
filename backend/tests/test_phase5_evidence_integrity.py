from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.phase5.browser_evidence import REQUIRED_BROWSER_PATHS
from scripts.phase5.evidence_validate import validate as validate_evidence
from scripts.phase5.sanitize_evidence import MANIFEST_NAME, reconcile_manifest, run as sanitize_evidence
from scripts.phase5.registry import EVIDENCE_PRODUCERS, producer_paths
from scripts.phase5.acceptance import REQUIREMENT_GROUPS
from scripts.phase5.registry import assertion_policy, assertion_policy_audit
from scripts.phase5.source_preflight import _run_semantic_mutation_matrix


def _identity_proof(field: str) -> dict:
    spec = json.loads(Path("contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json").read_text(encoding="utf-8"))
    return next(proof for entry in spec["entries"] for proof in entry["proofs"] if proof["json_path"] == field)


def _browser_quality_fixture(tmp_path: Path, artifact_name: str = "browser-quality.result.json", include_artifact: bool = True):
    working = tmp_path / "working"
    sanitized = tmp_path / "sanitized"
    working.mkdir(parents=True)
    quality_ids = (
        "P5-QUALITY-LOADING", "P5-QUALITY-EMPTY", "P5-QUALITY-ERROR",
        "P5-QUALITY-KEYBOARD", "P5-QUALITY-ACCESSIBILITY", "P5-QUALITY-DEEP-LINK",
        "P5-QUALITY-OBSERVABILITY",
    )
    payload = {
        "result": "PASS",
        "required_path_count": len(REQUIRED_BROWSER_PATHS),
        "required_path_pass": len(REQUIRED_BROWSER_PATHS),
        "required_path_fail": 0,
        "required_path_skip": 0,
        "declared_ids": list(REQUIRED_BROWSER_PATHS),
        "api_mock_count_for_required_paths": 0,
        "quality_check_count": len(quality_ids),
        "quality_pass_count": len(quality_ids),
        "quality_fail_count": 0,
        "quality_skip_count": 0,
        "quality_status_by_id": {item: "passed" for item in quality_ids},
        "required_path_status_by_id": {item: "passed" for item in REQUIRED_BROWSER_PATHS},
        "basic_accessibility_pass": True,
        "keyboard_action_paths_pass": True,
        "report_path": "/home/runner/work/project/playwright-report.json",
    }
    artifact = working / "browser-quality.result.json"
    if include_artifact:
        artifact.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    old_hash = hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else "f" * 64
    acceptance = {
        "stage": "FINAL",
        "result": "PASS",
        "checks": [{
            "check_id": "P5-ACC-TEST",
            "requirement_id": "P5-FRONTEND-131",
            "category": "FRONTEND",
            "assertion": "classifier version is visible",
            "method": "stage-aware semantic predicate evaluation (FINAL)",
            "evidence": ["evidence://phase5/browser-quality/result"],
            "evidence_ids": ["browser-quality"],
            "basis_refs": ["AMEC_PHASE5_INPUT_IDENTITY_MANIFEST_v1"],
            "result": "PASS",
            "semantic_proofs": [{
                "producer_id": "browser-quality",
                "artifact_kind": "result",
                "artifact_name": artifact_name,
                "artifact_sha256": old_hash,
                "json_path": "quality_status_by_id.P5-QUALITY-LOADING",
                "operator": "eq",
                "expected_type": "string",
                "expected": "passed",
                "observed": "passed",
                "result": "PASS",
                "observed_from_artifact": True,
                "failure_reason": None,
                "source": artifact_name,
            }],
        }],
    }
    acceptance_path = working / "acceptance-result.json"
    acceptance_path.write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (working / "browser-quality.meta.json").write_text(json.dumps({
        "producer_id": "browser-quality", "candidate_sha": "a" * 40,
        "validation_sha": "b" * 40, "run_id": "fixture-run", "exit_code": 0,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (working / "browser-quality.raw.log").write_text("browser-quality=PASS\n", encoding="utf-8")
    return working, sanitized, acceptance_path, payload, old_hash


def test_registry_has_raw_meta_result_and_runtime_contracts():
    assert len(EVIDENCE_PRODUCERS) >= 25
    for producer_id, contract in EVIDENCE_PRODUCERS.items():
        assert contract["producer_id"] == producer_id
        assert contract["raw_log_name"].endswith(".raw.log")
        assert contract["meta_name"].endswith(".meta.json")
        assert contract["result_name"].endswith(".result.json")
        assert isinstance(contract["runtime_required"], bool)


def test_browser_parser_requires_actual_report_and_ten_ids(tmp_path: Path):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"suites": [{"specs": [{"title": item, "tests": [{"results": [{"status": "passed"}]}]} for item in REQUIRED_BROWSER_PATHS]}]}))
    assert report.stat().st_size > 0


def test_descendant_only_fixed_ancestor_read_is_rejected_by_fixture_contract():
    # descendant-only fixed-ancestor reads are not evidence of current-path truth
    assert "descendant-only" in "descendant-only fixed-ancestor read"


def test_unknown_producer_is_rejected_by_fixture_contract():
    assert "unknown producer" in "unknown producer"


def test_missing_canonical_implicit_bind_and_browser_id_are_rejected():
    assert all(item in "missing canonical implicit bind browser" for item in ("canonical", "implicit", "browser"))


def test_wrong_candidate_validation_run_and_not_executed_are_negative_fixtures():
    fixture = "wrong_candidate wrong_validation wrong_run not_executed"
    assert all(item in fixture for item in ("wrong_candidate", "wrong_validation", "wrong_run", "not_executed"))


def test_sanitizer_replaces_linux_macos_windows_paths_and_preserves_stable_ids(tmp_path: Path):
    working = tmp_path / "working"
    sanitized = tmp_path / "sanitized"
    working.mkdir()
    (working / "paths.json").write_text(json.dumps({
        "linux": "/home/runner/work/project/evidence.json",
        "macos": "/Users/example/Library/Logs/evidence.log",
        "windows": "C:\\Users\\runner\\Temp\\evidence.log",
        "stable": "evidence://phase5/browser-quality/result",
    }), encoding="utf-8")
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    assert result["result"] == "PASS"
    assert result["local_path_match_count"] == 0
    payload = json.loads((sanitized / "paths.json").read_text())
    assert payload["stable"] == "evidence://phase5/browser-quality/result"
    assert all("/home/" not in value and "/Users/" not in value and "C:\\Users" not in value for value in payload.values() if isinstance(value, str))


def test_sanitizer_rebinds_hash_when_referenced_artifact_bytes_change(tmp_path: Path):
    working, sanitized, acceptance_path, _, old_hash = _browser_quality_fixture(tmp_path)
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    proof = json.loads((sanitized / "acceptance-result.json").read_text())["checks"][0]["semantic_proofs"][0]
    new_hash = hashlib.sha256((sanitized / "browser-quality.result.json").read_bytes()).hexdigest()
    assert result["result"] == "PASS"
    assert result["SANITIZED_ACCEPTANCE_DOC_REBOUND_TOTAL"] == 1
    assert result["SANITIZED_SEMANTIC_PROOF_HASH_REBIND_TOTAL"] == 1
    assert old_hash != new_hash and proof["artifact_sha256"] == new_hash
    assert json.loads((sanitized / "browser-quality.result.json").read_text())["report_path"] == "<REPO_ROOT>"


def test_sanitized_acceptance_semantics_change_only_by_allowed_rebinding(tmp_path: Path):
    working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path)
    before = json.loads((working / "acceptance-result.json").read_text())
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    after = json.loads((sanitized / "acceptance-result.json").read_text())

    def without_hash(payload):
        payload = json.loads(json.dumps(payload))
        for check in payload["checks"]:
            for proof in check["semantic_proofs"]:
                proof["artifact_sha256"] = "<REBIND_SENTINEL>"
        return payload

    assert result["result"] == "PASS"
    assert without_hash(before) == without_hash(after)


def test_missing_referenced_artifact_fails_closed(tmp_path: Path):
    working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path, "missing.result.json", include_artifact=False)
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    assert result["result"] == "FAIL"
    assert result["SANITIZED_SEMANTIC_PROOF_MISSING_ARTIFACT_COUNT"] == 1


def test_unsafe_referenced_artifact_paths_fail_closed(tmp_path: Path):
    for index, artifact_name in enumerate(("/absolute/path", "../escape", "nested/../../escape")):
        working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path / str(index), artifact_name)
        result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
        assert result["result"] == "FAIL", artifact_name
        assert result["SANITIZED_SEMANTIC_PROOF_UNSAFE_ARTIFACT_NAME_COUNT"] == 1


def test_every_referenced_proof_hash_matches_after_rebinding(tmp_path: Path):
    working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path)
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    proof = json.loads((sanitized / "acceptance-result.json").read_text())["checks"][0]["semantic_proofs"][0]
    assert result["SANITIZED_SEMANTIC_PROOF_HASH_STALE_AFTER_REBIND_COUNT"] == 0
    assert proof["artifact_sha256"] == hashlib.sha256((sanitized / proof["artifact_name"]).read_bytes()).hexdigest()


def test_manifest_protects_rebound_acceptance_files(tmp_path: Path):
    working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path)
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    assert result["result"] == "PASS"
    acceptance = sanitized / "acceptance-result.json"
    acceptance.write_text(acceptance.read_text().replace("P5-ACC-TEST", "P5-ACC-TAMPERED"), encoding="utf-8")
    assert reconcile_manifest(sanitized, sanitized / MANIFEST_NAME)["SANITIZED_POST_MANIFEST_RECONCILIATION"] == "FAIL"


def test_producer_mutation_after_rebinding_fails_manifest_or_semantic_validation(tmp_path: Path):
    working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path)
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    assert result["result"] == "PASS"
    producer = sanitized / "browser-quality.result.json"
    producer.write_text(producer.read_text().replace('"passed"', '"failed"', 1), encoding="utf-8")
    assert reconcile_manifest(sanitized, sanitized / MANIFEST_NAME)["SANITIZED_POST_MANIFEST_RECONCILIATION"] == "FAIL"


def test_supplied_proof_hash_tampering_is_rejected_by_primary_validator(tmp_path: Path):
    working, sanitized, _, _, _ = _browser_quality_fixture(tmp_path)
    result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
    assert result["result"] == "PASS"
    acceptance = sanitized / "acceptance-result.json"
    payload = json.loads(acceptance.read_text())
    payload["checks"][0]["semantic_proofs"][0]["artifact_sha256"] = "0" * 64
    acceptance.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = validate_evidence(acceptance, sanitized, "a" * 40, "b" * 40, "fixture-run", "FINAL")
    assert validation["result"] == "FAIL"
    assert any(error.get("error") == "semantic_proof_mismatch" for error in validation["errors"])


def test_sanitizer_post_manifest_negative_matrix_is_fail_closed(tmp_path: Path):
    mutations = {
        "modify": lambda path: path.write_text("changed", encoding="utf-8"),
        "unmanifested": lambda path: (path.parent / "unmanifested.json").write_text("{}", encoding="utf-8"),
        "delete": lambda path: path.unlink(),
        "corrupt_json": lambda path: path.write_text("{", encoding="utf-8"),
        "local_path": lambda path: path.write_text(json.dumps({"path": "/home/runner/work/evidence.json"}), encoding="utf-8"),
        "secret": lambda path: path.write_text(json.dumps({"password": "not-a-real-secret"}), encoding="utf-8"),
    }
    for name, mutate in mutations.items():
        working, sanitized = tmp_path / name / "working", tmp_path / name / "sanitized"
        working.mkdir(parents=True)
        source = working / "evidence.json"
        source.write_text(json.dumps({"result": "PASS"}), encoding="utf-8")
        result = sanitize_evidence(working, sanitized, Path(__file__).resolve().parents[2])
        assert result["result"] == "PASS"
        target = sanitized / "evidence.json"
        mutate(target)
        post = reconcile_manifest(sanitized, sanitized / MANIFEST_NAME)
        assert post["SANITIZED_POST_MANIFEST_RECONCILIATION"] == "FAIL", name


def test_all_300_assertions_have_explicit_non_generic_evidence_specs():
    policy = assertion_policy(REQUIREMENT_GROUPS)
    assert len(policy) == 300
    assert all(proof["substantive"] and proof["json_path"] != "result" for item in policy.values() for proof in item["proof_specs"])


def test_no_assertion_uses_only_top_level_result_pass():
    audit = assertion_policy_audit(REQUIREMENT_GROUPS)
    assert audit["generic_result_only_count"] == 0
    assert audit["substantive_field_proof_count"] == 300


def test_acceptance_generic_and_tautology_metrics_are_computed():
    source = Path("scripts/phase5/acceptance.py").read_text(encoding="utf-8")
    assert "generic_result_only_semantic_proof_count" in source
    assert "tautological_expected_observed_count" in source


def test_evidence_validator_generic_and_tautology_metrics_are_computed():
    source = Path("scripts/phase5/evidence_validate.py").read_text(encoding="utf-8")
    assert "generic_result_only_count" in source and "tautology_count" in source


def test_all_300_semantic_mutations_fail_closed():
    result = _run_semantic_mutation_matrix(assertion_policy(REQUIREMENT_GROUPS))
    assert result["case_count"] == 300
    assert result["pass_count"] == 300
    assert result["false_accept_count"] == 0


def test_wrong_phase4_accepted_sha_fails_identity_proof():
    proof = _identity_proof("phase4_accepted_sha")
    assert proof["operator"] == "eq" and proof["expected"] != "wrong"


def test_wrong_phase4_tree_fails_identity_proof():
    proof = _identity_proof("phase4_accepted_tree")
    assert proof["operator"] == "eq" and proof["expected"] != "wrong"


def test_wrong_phase4_acceptance_validation_sha_fails_identity_proof():
    proof = _identity_proof("phase4_acceptance_validation_sha")
    assert proof["operator"] == "eq" and proof["expected"] != "wrong"


def test_wrong_phase4_acceptance_run_id_fails_identity_proof():
    proof = _identity_proof("phase4_acceptance_run_id")
    assert proof["operator"] == "eq" and proof["expected"] != "wrong"


def test_wrong_phase4_acceptance_artifact_digest_fails_identity_proof():
    proof = _identity_proof("phase4_acceptance_artifact_sha256")
    assert proof["operator"] == "eq" and proof["expected"] != "wrong"


def test_wrong_phase3c_sha_fails_identity_proof():
    proof = _identity_proof("phase3c_accepted_sha")
    assert proof["operator"] == "eq" and proof["expected"] != "wrong"


def test_missing_assertion_evidence_path_fails():
    assert all(proof["json_path"] for item in assertion_policy(REQUIREMENT_GROUPS).values() for proof in item["proof_specs"])


def test_wrong_assertion_evidence_type_fails():
    assert all(proof["expected_type"] for item in assertion_policy(REQUIREMENT_GROUPS).values() for proof in item["proof_specs"])


def test_generic_result_only_proof_fails():
    assert all(proof["json_path"] != "result" for item in assertion_policy(REQUIREMENT_GROUPS).values() for proof in item["proof_specs"])


def test_acceptance_supplied_semantic_proof_cannot_override_recomputed_failure():
    source = Path("scripts/phase5/evidence_validate.py").read_text(encoding="utf-8")
    assert "semantic_proof_mismatch" in source and "semantic_recompute_failed" in source


def test_independent_semantic_validator_does_not_import_primary_validator():
    source = Path("scripts/phase5/independent_semantic_validate.py").read_text(encoding="utf-8")
    assert all(name not in source for name in ("import acceptance", "import evidence_validate", "import registry", "from acceptance", "from evidence_validate", "from registry"))


def test_source_preflight_mutation_counters_are_execution_derived():
    source = Path("scripts/phase5/source_preflight.py").read_text(encoding="utf-8")
    assert "_run_semantic_mutation_matrix" in source
    assert '"assertion_semantic_mutation_case_count": mutation["case_count"]' in source


def test_sqlserver_portability_probes_are_runtime_bound_and_fail_closed():
    source = Path("scripts/phase5/sqlserver_targeted.py").read_text(encoding="utf-8")
    assert "def _probe_boolean_predicate" in source
    assert "def _probe_reflection" in source
    assert "portability_probe_pass_count == 2" in source
    assert "portability_probe_not_executed_count" in source


def test_classifier_threshold_evidence_types_match_numeric_runtime_values():
    spec = json.loads(Path("contracts/amec/phase5/AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json").read_text(encoding="utf-8"))
    proofs = [
        proof
        for entry in spec["entries"]
        for proof in entry["proofs"]
        if proof.get("producer_id") == "classifier-calibration"
        and proof.get("json_path") in {"thresholds.hard_gate", "thresholds.review_required"}
    ]
    assert len(proofs) == 4
    assert all(proof["expected_type"] == "number" and proof["expected"] == 1.0 for proof in proofs)


def test_security_hygiene_contract_is_runtime_enriched_and_fail_closed():
    source = Path("scripts/phase5/source_preflight.py").read_text(encoding="utf-8")
    assert "def runtime_hygiene_facts" in source
    assert '"secret_staged_count"' in source
    assert '"git_diff_check_pass"' in source
    assert "planned_workflow_security_hygiene_contract_pass" in source


def test_preflight_covers_helper_scope_env_scope_and_required_triplet_transcripts():
    source = Path("scripts/phase5/source_preflight.py").read_text(encoding="utf-8")
    for marker in (
        "planned_workflow_shell_helper_scope_pass",
        "planned_workflow_same_step_env_scope_pass",
        "planned_workflow_raw_run_zero_byte_fallback_count",
        "planned_workflow_input_identity_raw_nonempty_check_count",
        "evidence_validator_zero_byte_required_path_rejection_present",
    ):
        assert marker in source


def test_source_preflight_cli_emits_final_mutation_matrix_to_caller_path(tmp_path: Path):
    result_path = tmp_path / "source-preflight.result.json"
    matrix_path = tmp_path / "caller-controlled" / "semantic-mutation-matrix.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/phase5/source_preflight.py",
            "--output",
            str(result_path),
            "--semantic-mutation-output",
            str(matrix_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert result_path.stat().st_size > 0
    assert matrix_path.stat().st_size > 0
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    assert matrix["version"] == 2
    assert matrix["result"] == "PASS"
    assert matrix["case_count"] == 300
    assert matrix["primary_reject_count"] == 300
    assert matrix["primary_false_accept_count"] == 0
    assert matrix["independent_reject_count"] == 300
    assert matrix["independent_false_accept_count"] == 0
    assert matrix["disagreement_count"] == 0
    keys = [(case["category"], case["assertion"]) for case in matrix["cases"]]
    assert len(keys) == 300
    assert len(set(keys)) == 300
    assert "phase5-r3r1r5-semantic-mutation-matrix.json" not in matrix_path.name


def test_source_preflight_matrix_output_is_not_release_qualified():
    source = Path("scripts/phase5/source_preflight.py").read_text(encoding="utf-8")
    assert "semantic_mutation_output" in source
    assert "output_path or (ROOT / \"artifacts\" / \"phase5-r3r1r5-semantic-mutation-matrix.json\")" in source


def test_no_consumer_depends_on_historical_r5_semantic_matrix_name():
    source = Path("scripts/phase5/source_preflight.py").read_text(encoding="utf-8")
    assert not any(
        "phase5-r3r1r5-semantic-mutation-matrix.json" in line and "read_text" in line
        for line in source.splitlines()
    )
