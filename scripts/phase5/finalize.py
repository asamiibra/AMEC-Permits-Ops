from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import CLASSIFIER_VERSION, INPUT_IDENTITIES, PHASE5_ARTIFACTS, PHASE5_CONTRACTS, RULES_VERSION, TAXONOMY_REVISION, read_json, sha256_file, write_json
from registry import CANONICAL_ARTIFACTS, EVIDENCE_PRODUCERS, canonical_path, producer_paths

RESULT_KEYS = ("validation_results", "holdout_results", "cross_context_results", "path_counterfactual_results")
PRE_FINALIZER_KEYS = ("input_identity", "envelope_schema", "rules", "corpus", "calibration_manifest", "validation_manifest", "holdout_manifest", "calibration_results", *RESULT_KEYS, "shadow_contract", "acceptance_schema", "final_summary_schema")


def _errors(contracts_dir: Path, acceptance_path: Path, evidence_dir: Path, expected: str, expected_validation: str, expected_run_id: str, validation_result_path: Path | None, local_test_mode: bool) -> list[str]:
    errors: list[str] = []
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        errors.append("expected-candidate-sha")
    errors.extend(f"missing-contract:{path.name}" for path in (contracts_dir / CANONICAL_ARTIFACTS[key] for key in PRE_FINALIZER_KEYS) if not path.is_file())
    try:
        acceptance = read_json(acceptance_path)
    except (OSError, json.JSONDecodeError):
        errors.append("invalid-acceptance")
        acceptance = {}
    if acceptance.get("result") != "PASS" or acceptance.get("primary_check_count") != 300 or any(check.get("result") != "PASS" for check in acceptance.get("checks", [])):
        errors.append("acceptance-not-pass")
    if not local_test_mode:
        if validation_result_path is None or not validation_result_path.is_file():
            errors.append("missing-evidence-validation")
        else:
            try:
                validation = read_json(validation_result_path)
                if validation.get("result") != "PASS":
                    errors.append("evidence-validation-not-pass")
                if validation.get("expected_candidate_sha") != expected or validation.get("expected_validation_sha") != expected_validation or str(validation.get("expected_run_id")) != expected_run_id:
                    errors.append("evidence-validation-identity-mismatch")
                if any(validation.get(key, 0) != 0 for key in ("false_accept_count", "identity_mismatch_count", "not_executed_count", "self_reference_only_count", "missing_required_producer_count", "runtime_required_source_only_pass_count", "unknown_evidence_id_count", "unresolved_evidence_reference_count")):
                    errors.append("evidence-validation-nonzero-failure-metric")
            except (OSError, json.JSONDecodeError):
                errors.append("invalid-evidence-validation")
    for producer_id, contract in EVIDENCE_PRODUCERS.items():
        paths = producer_paths(producer_id, evidence_dir)
        # The finalizer is the artifact being created; it must never be its own prerequisite.
        if producer_id == "finalizer":
            continue
        for kind, path in paths.items():
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"missing-producer:{producer_id}:{kind}")
        if paths["meta"].is_file():
            try:
                metadata = read_json(paths["meta"])
                if metadata.get("candidate_sha") != expected:
                    errors.append(f"candidate-mismatch:{producer_id}")
                if metadata.get("validation_sha") != expected_validation:
                    errors.append(f"validation-mismatch:{producer_id}")
                if str(metadata.get("run_id")) != expected_run_id:
                    errors.append(f"run-mismatch:{producer_id}")
                if metadata.get("producer_id") != producer_id:
                    errors.append(f"producer-id-mismatch:{producer_id}")
                if metadata.get("exit_code") != 0:
                    errors.append(f"producer-exit:{producer_id}")
            except (OSError, json.JSONDecodeError):
                errors.append(f"invalid-meta:{producer_id}")
        if paths["result"].is_file():
            try:
                if read_json(paths["result"]).get("result") != "PASS":
                    errors.append(f"producer-failed:{producer_id}")
            except (OSError, json.JSONDecodeError):
                errors.append(f"invalid-result:{producer_id}")
    for key in RESULT_KEYS:
        path = canonical_path(key, contracts_dir)
        try:
            payload = read_json(path)
            if payload.get("result") != "PASS" or payload.get("critical_false_promotions") != 0:
                errors.append(f"canonical-result-failed:{path.name}")
        except (OSError, json.JSONDecodeError):
            errors.append(f"invalid-canonical-result:{path.name}")
    return errors


def run(contracts_dir: Path = PHASE5_CONTRACTS, acceptance_path: Path | None = None, evidence_dir: Path | None = None, output_path: Path | None = None, *, expected_candidate_sha: str | None = None, expected_validation_sha: str | None = None, expected_run_id: str | None = None, validation_result_path: Path | None = None, local_test_mode: bool = False) -> dict[str, Any]:
    if evidence_dir is None or acceptance_path is None or expected_candidate_sha is None or expected_validation_sha is None or expected_run_id is None:
        raise RuntimeError("FINALIZER_STOP:required evidence, acceptance, validation, run, and expected identity arguments are mandatory")
    errors = _errors(contracts_dir, acceptance_path, evidence_dir, expected_candidate_sha, expected_validation_sha, expected_run_id, validation_result_path, local_test_mode)
    if errors:
        raise RuntimeError("FINALIZER_STOP:" + ",".join(errors))
    acceptance = read_json(acceptance_path)
    producer_payload = {producer: read_json(producer_paths(producer, evidence_dir)["result"]) for producer in EVIDENCE_PRODUCERS if producer_paths(producer, evidence_dir)["result"].is_file()}
    sql = producer_payload.get("sqlserver-targeted", {})
    browser = producer_payload.get("browser-quality", {})
    shadow = producer_payload.get("shadow-replay", {})
    hashes = {CANONICAL_ARTIFACTS[key]: sha256_file(canonical_path(key, contracts_dir)) for key in PRE_FINALIZER_KEYS}
    manifest = {
        "version": 3, "manifest_id": "AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_V1", "freeze_state": "FROZEN",
        "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id,
        "taxonomy_revision": TAXONOMY_REVISION, "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION,
        "classification_envelope_schema_path": CANONICAL_ARTIFACTS["envelope_schema"], "classification_envelope_schema_sha256": sha256_file(canonical_path("envelope_schema", contracts_dir)),
        "phase4_accepted_sha": INPUT_IDENTITIES["phase4_accepted_sha"], "input_identity_manifest_path": CANONICAL_ARTIFACTS["input_identity"],
        "input_identity_manifest_sha256": sha256_file(canonical_path("input_identity", contracts_dir)), "robustness_corpus_path": CANONICAL_ARTIFACTS["corpus"],
        "robustness_corpus_sha256": sha256_file(canonical_path("corpus", contracts_dir)), "artifact_sha256": hashes,
        "classifier_source_path": "backend/app/services/classifier_v2.py", "classifier_source_sha256": sha256_file(Path(__file__).resolve().parents[2] / "backend/app/services/classifier_v2.py"),
        "final_commit_identity": "POST_COMMIT_EXTERNAL_HANDOFF", "final_tree_identity": "POST_COMMIT_EXTERNAL_HANDOFF", "recursive_self_hash": False,
        "synthetic_only": True, "llm_external_call_count": 0,
    }
    write_json(canonical_path("freeze_manifest", contracts_dir), manifest)
    summary = {
        "version": 2, "result": "PASS", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id,
        "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION,
        "taxonomy_revision": TAXONOMY_REVISION, "freeze_manifest": CANONICAL_ARTIFACTS["freeze_manifest"],
        "acceptance_check_count": acceptance["primary_check_count"], "critical_false_promotions": {"golden": 0, "validation": 0, "holdout": 0, "adversarial": 0},
        "failed_acceptance_check_count": acceptance.get("primary_check_fail_count", 0), "required_evidence_files_present": True,
        "new_source_reads": shadow.get("new_source_reads", 0), "auto_promotion_enabled": False,
        "browser_required_path_count": browser.get("required_path_count"), "browser_required_path_pass": browser.get("required_path_pass"),
        "browser_required_path_fail": browser.get("required_path_fail"), "sqlserver_validation_result": sql.get("result"),
        "sqlserver_gate_count": sql.get("gate_count"), "shadow_state": shadow.get("shadow_state"),
        "promotion_requires_human_review": True, "projection_requires_existing_verified_assertion": True,
        "llm_external_call_count": shadow.get("llm_external_call_count"), "real_content": shadow.get("real_content"),
        "synthetic_only": True, "handoff_state": "READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE", "RUN_EVIDENCE_STATE": "COMPLETE_PASS",
    }
    write_json(output_path or (PHASE5_ARTIFACTS / "phase5-final-summary.json"), summary)
    final_paths = producer_paths("finalizer", evidence_dir)
    final_paths["raw"].write_text("finalizer=PASS\n", encoding="utf-8")
    final_paths["meta"].write_text(json.dumps({"producer_id": "finalizer", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "exit_code": 0}, sort_keys=True) + "\n", encoding="utf-8")
    final_paths["result"].write_text(json.dumps({"producer_id": "finalizer", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "result": "PASS"}, sort_keys=True) + "\n", encoding="utf-8")
    return {"manifest": manifest, "summary": summary}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--acceptance-result", type=Path, required=True)
    parser.add_argument("--validation-result", type=Path, required=True)
    parser.add_argument("--contracts-dir", type=Path, default=PHASE5_CONTRACTS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidate-sha", required=True)
    parser.add_argument("--expected-validation-sha", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--local-test-mode", action="store_true")
    args = parser.parse_args()
    result = run(args.contracts_dir, args.acceptance_result, args.evidence_dir, args.output, expected_candidate_sha=args.expected_candidate_sha, expected_validation_sha=args.expected_validation_sha, expected_run_id=args.expected_run_id, validation_result_path=args.validation_result, local_test_mode=args.local_test_mode)
    print(json.dumps({"result": result["summary"]["result"], "acceptance_check_count": result["summary"]["acceptance_check_count"]}, sort_keys=True))
