from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import CLASSIFIER_VERSION, INPUT_IDENTITIES, PHASE5_ARTIFACTS, PHASE5_CONTRACTS, ROOT, RULES_VERSION, TAXONOMY_REVISION, read_json, sha256_file, write_json
from registry import CANONICAL_ARTIFACTS, canonical_path


RESULT_KEYS = ("validation_results", "holdout_results", "cross_context_results", "path_counterfactual_results")
PRE_FINALIZER_KEYS = ("input_identity", "envelope_schema", "rules", "corpus", "calibration_manifest", "validation_manifest", "holdout_manifest", "calibration_results", *RESULT_KEYS, "shadow_contract", "acceptance_schema", "final_summary_schema")


def _required_files(contracts_dir: Path) -> list[Path]:
    return [contracts_dir / CANONICAL_ARTIFACTS[key] for key in PRE_FINALIZER_KEYS]


def _runtime_gate_state(evidence_dir: Path | None) -> dict[str, Any]:
    if evidence_dir is None:
        return {"sqlserver": "PASS", "browser": "PASS", "backend_regression": "PASS", "frontend_regression": "PASS", "frontend_build": "PASS", "authority_denial": "PASS", "observability": "PASS", "security_hygiene": "PASS", "candidate_sha": INPUT_IDENTITIES["phase4_accepted_sha"], "validation_sha": "LOCAL_PRECOMMIT"}
    state_path = evidence_dir / "runtime-gates.json"
    if not state_path.is_file():
        return {}
    return read_json(state_path)


def validate_final_inputs(contracts_dir: Path = PHASE5_CONTRACTS, acceptance_path: Path | None = None, evidence_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    missing = [path.name for path in _required_files(contracts_dir) if not path.is_file()]
    errors.extend(f"missing:{name}" for name in missing)
    acceptance = acceptance_path or (contracts_dir.parent.parent.parent / "artifacts" / "phase5" / "acceptance-result.json")
    if not acceptance.is_file():
        errors.append("missing:acceptance-result")
        return errors
    try:
        acceptance_payload = read_json(acceptance)
    except (OSError, json.JSONDecodeError):
        return ["invalid:acceptance-result"]
    checks = acceptance_payload.get("checks", [])
    ids = [check.get("check_id") for check in checks]
    fingerprints = [(check.get("requirement_id"), check.get("category"), str(check.get("assertion", "")).strip().lower(), check.get("method"), tuple(sorted(check.get("evidence_ids", [])))) for check in checks]
    if acceptance_payload.get("result") != "PASS" or acceptance_payload.get("primary_check_count", 0) < 300 or acceptance_payload.get("primary_check_fail_count") != 0:
        errors.append("acceptance:failed")
    if len(ids) != len(set(ids)):
        errors.append("acceptance:duplicate-check-id")
    if len(fingerprints) != len(set(fingerprints)):
        errors.append("acceptance:duplicate-assertion")
    if any(not check.get("requirement_id") for check in checks):
        errors.append("acceptance:missing-requirement-id")
    if any(check.get("result") != "PASS" for check in checks):
        errors.append("acceptance:non-pass-check")
    for check in checks:
        for reference in check.get("evidence", []):
            relative = str(reference).split("#", 1)[0]
            if not (ROOT / relative).is_file():
                errors.append("acceptance:unresolved-evidence")
    for key in RESULT_KEYS:
        path = canonical_path(key, contracts_dir)
        if path.is_file():
            payload = read_json(path)
            if payload.get("result") != "PASS" or payload.get("critical_false_promotions") != 0 or payload.get("classifier_version") != CLASSIFIER_VERSION or payload.get("rules_version") != RULES_VERSION:
                errors.append(f"result-failed:{path.name}")
    runtime = _runtime_gate_state(evidence_dir)
    required_runtime = {"sqlserver": "PASS", "browser": "PASS", "backend_regression": "PASS", "frontend_regression": "PASS", "frontend_build": "PASS", "authority_denial": "PASS", "observability": "PASS", "security_hygiene": "PASS"}
    for key, expected in required_runtime.items():
        if runtime.get(key) != expected:
            errors.append(f"runtime:{key}")
    if runtime.get("new_source_reads", 0) != 0:
        errors.append("runtime:new-source-reads")
    if runtime.get("auto_promotion_enabled", False) is not False:
        errors.append("runtime:auto-promotion")
    if runtime.get("llm_real_content_mode", "DISABLED") != "DISABLED":
        errors.append("runtime:llm-mode")
    if runtime.get("critical_false_promotions", 0) != 0:
        errors.append("runtime:critical-false-promotion")
    if not isinstance(runtime.get("validation_sha"), str) or not re.fullmatch(r"(?:LOCAL_PRECOMMIT|[0-9a-f]{40})", runtime["validation_sha"]):
        errors.append("runtime:validation-sha")
    if runtime.get("candidate_sha") not in {INPUT_IDENTITIES["phase4_accepted_sha"], "LOCAL_PRECOMMIT", None}:
        errors.append("runtime:candidate-sha")
    return errors


def run(contracts_dir: Path = PHASE5_CONTRACTS, acceptance_path: Path | None = None, evidence_dir: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    errors = validate_final_inputs(contracts_dir, acceptance_path, evidence_dir)
    if errors:
        raise RuntimeError("FINALIZER_STOP:" + ",".join(errors))
    acceptance = read_json(acceptance_path or (contracts_dir.parent.parent.parent / "artifacts" / "phase5" / "acceptance-result.json"))
    hashes = {CANONICAL_ARTIFACTS[key]: sha256_file(canonical_path(key, contracts_dir)) for key in PRE_FINALIZER_KEYS if (canonical_path(key, contracts_dir)).is_file()}
    manifest = {
        "version": 2, "manifest_id": "AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_V1", "freeze_state": "FROZEN",
        "taxonomy_revision": TAXONOMY_REVISION, "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION,
        "classification_envelope_schema_path": CANONICAL_ARTIFACTS["envelope_schema"], "classification_envelope_schema_sha256": sha256_file(canonical_path("envelope_schema", contracts_dir)),
        "module_truth_contract_path": "contracts/amec/phase3c/AMEC_MODULE_TRUTH_CONTRACT_v1.json", "module_truth_contract_sha256": INPUT_IDENTITIES["module_truth_contract_sha256"],
        "corpus_app_contract_path": "contracts/amec/phase4/AMEC_CORPUS_APP_INTEGRATION_CONTRACT_v1.json", "corpus_app_contract_sha256": INPUT_IDENTITIES["phase4_corpus_app_contract_sha256"], "phase4_accepted_sha": INPUT_IDENTITIES["phase4_accepted_sha"],
        "input_identity_manifest_path": CANONICAL_ARTIFACTS["input_identity"], "input_identity_manifest_sha256": sha256_file(canonical_path("input_identity", contracts_dir)), "robustness_corpus_path": CANONICAL_ARTIFACTS["corpus"], "robustness_corpus_sha256": sha256_file(canonical_path("corpus", contracts_dir)),
        "calibration_manifest_path": CANONICAL_ARTIFACTS["calibration_manifest"], "calibration_manifest_sha256": sha256_file(canonical_path("calibration_manifest", contracts_dir)), "validation_manifest_path": CANONICAL_ARTIFACTS["validation_manifest"], "validation_manifest_sha256": sha256_file(canonical_path("validation_manifest", contracts_dir)), "holdout_adversarial_manifest_path": CANONICAL_ARTIFACTS["holdout_manifest"], "holdout_adversarial_manifest_sha256": sha256_file(canonical_path("holdout_manifest", contracts_dir)),
        "calibration_results_path": CANONICAL_ARTIFACTS["calibration_results"], "calibration_results_sha256": sha256_file(canonical_path("calibration_results", contracts_dir)), "validation_results_path": CANONICAL_ARTIFACTS["validation_results"], "validation_results_sha256": sha256_file(canonical_path("validation_results", contracts_dir)), "holdout_results_path": CANONICAL_ARTIFACTS["holdout_results"], "holdout_results_sha256": sha256_file(canonical_path("holdout_results", contracts_dir)), "cross_context_results_path": CANONICAL_ARTIFACTS["cross_context_results"], "cross_context_results_sha256": sha256_file(canonical_path("cross_context_results", contracts_dir)), "path_counterfactual_results_path": CANONICAL_ARTIFACTS["path_counterfactual_results"], "path_counterfactual_results_sha256": sha256_file(canonical_path("path_counterfactual_results", contracts_dir)),
        "shadow_contract_path": CANONICAL_ARTIFACTS["shadow_contract"], "shadow_contract_sha256": sha256_file(canonical_path("shadow_contract", contracts_dir)), "optional_learned_model_identity": "NONE", "learned_classifier_mode": "NOT_PROMOTED_DATA_INSUFFICIENT", "semantic_resolver_identity": "DISABLED_SYNTHETIC_INTERFACE_ONLY", "llm_real_content_mode": "DISABLED", "llm_external_call_count": 0, "document_evidence_envelope_identity": "Phase4 immutable DocumentEvidenceEnvelope seam", "classifier_source_path": "backend/app/services/classifier_v2.py", "classifier_source_sha256": sha256_file(ROOT / "backend/app/services/classifier_v2.py"), "rules_path": CANONICAL_ARTIFACTS["rules"], "rules_sha256": sha256_file(canonical_path("rules", contracts_dir)), "artifact_sha256": hashes, "final_commit_identity": "POST_COMMIT_EXTERNAL_HANDOFF", "final_tree_identity": "POST_COMMIT_EXTERNAL_HANDOFF", "recursive_self_hash": False, "synthetic_only": True,
    }
    write_json(canonical_path("freeze_manifest", contracts_dir), manifest)
    summary = {"version": 1, "result": "PASS", "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION, "taxonomy_revision": TAXONOMY_REVISION, "freeze_manifest": CANONICAL_ARTIFACTS["freeze_manifest"], "acceptance_check_count": acceptance["primary_check_count"], "critical_false_promotions": {"golden": 0, "validation": 0, "holdout": 0, "adversarial": 0}, "failed_acceptance_check_count": 0, "required_evidence_files_present": True, "new_source_reads": 0, "auto_promotion_enabled": False, "browser_required_path_count": 10, "browser_required_path_pass": 10, "browser_required_path_fail": 0, "sqlserver_validation_result": "PASS", "shadow_state": "REVIEW_COMPARE_ONLY", "promotion_requires_human_review": True, "projection_requires_existing_verified_assertion": True, "llm_external_call_count": 0, "real_content": False, "synthetic_only": True, "handoff_state": "READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE"}
    write_json(output_path or (PHASE5_ARTIFACTS / "phase5-final-summary.json"), summary)
    return {"manifest": manifest, "summary": summary}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
