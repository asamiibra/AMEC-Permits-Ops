from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    from common import CLASSIFIER_VERSION, INPUT_IDENTITIES, PHASE5_ARTIFACTS, PHASE5_CONTRACTS, RULES_VERSION, TAXONOMY_REVISION, read_json, sha256_file, write_json
    from registry import CANONICAL_ARTIFACTS, EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS, producer_paths, validate_producer_payload_contract
except ModuleNotFoundError:
    from .common import CLASSIFIER_VERSION, INPUT_IDENTITIES, PHASE5_ARTIFACTS, PHASE5_CONTRACTS, RULES_VERSION, TAXONOMY_REVISION, read_json, sha256_file, write_json
    from .registry import CANONICAL_ARTIFACTS, EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS, producer_paths, validate_producer_payload_contract


# Normative, machine-readable source map. Every governing summary value is
# derived from one of these producer/path/transform entries.
SUMMARY_FIELD_SOURCE_MAP: dict[str, dict[str, Any]] = {
    "browser_required_path_count": {"producer_ids": ["browser-required-paths"], "json_paths": ["required_path_count"], "transform": "identity", "expected_type": "integer"},
    "browser_required_path_pass": {"producer_ids": ["browser-required-paths"], "json_paths": ["required_path_pass"], "transform": "identity", "expected_type": "integer"},
    "browser_required_path_fail": {"producer_ids": ["browser-required-paths"], "json_paths": ["required_path_fail"], "transform": "identity", "expected_type": "integer"},
    "sqlserver_validation_result": {"producer_ids": ["sqlserver-targeted"], "json_paths": ["result"], "transform": "identity", "expected_type": "string"},
    "sqlserver_major": {"producer_ids": ["sqlserver-bootstrap"], "json_paths": ["sqlserver_major"], "transform": "identity", "expected_type": "integer"},
    "migration_head": {"producer_ids": ["sqlserver-bootstrap"], "json_paths": ["migration_head"], "transform": "identity", "expected_type": "string"},
    "critical_false_promotions": {"producer_ids": ["classifier-calibration", "classifier-validation", "classifier-holdout", "classifier-cross-context", "classifier-path-counterfactual"], "json_paths": ["critical_false_promotions"], "transform": "sum", "expected_type": "integer"},
    "shadow_state": {"producer_ids": ["shadow-replay"], "json_paths": ["shadow_state"], "transform": "identity", "expected_type": "string"},
    "promotion_requires_human_review": {"producer_ids": ["source-preflight"], "json_paths": ["authority.promotion_requires_human_review"], "transform": "identity", "expected_type": "boolean"},
    "projection_requires_existing_verified_assertion": {"producer_ids": ["source-preflight"], "json_paths": ["authority.projection_requires_existing_verified_assertion"], "transform": "identity", "expected_type": "boolean"},
    "backend_regression": {"producer_ids": ["backend-full"], "json_paths": ["result"], "transform": "identity", "expected_type": "string"},
    "frontend_regression": {"producer_ids": ["frontend-full"], "json_paths": ["result"], "transform": "identity", "expected_type": "string"},
    "frontend_build": {"producer_ids": ["frontend-build"], "json_paths": ["result"], "transform": "identity", "expected_type": "string"},
    "new_source_reads": {"producer_ids": ["shadow-replay"], "json_paths": ["new_source_reads"], "transform": "identity", "expected_type": "integer"},
    "auto_promotion_enabled": {"producer_ids": ["source-preflight"], "json_paths": ["authority.auto_promotion_enabled"], "transform": "identity", "expected_type": "boolean"},
    "llm_real_content_mode": {"producer_ids": ["shadow-replay"], "json_paths": ["real_content"], "transform": "boolean_to_mode", "expected_type": "string"},
    "llm_external_call_count": {"producer_ids": ["shadow-replay"], "json_paths": ["llm_external_call_count"], "transform": "identity", "expected_type": "integer"},
}
REQUIRED_SUMMARY_FIELDS = tuple(SUMMARY_FIELD_SOURCE_MAP)
RESULT_KEYS = ("validation_results", "holdout_results", "cross_context_results", "path_counterfactual_results")
PRE_FINALIZER_KEYS = ("input_identity", "envelope_schema", "rules", "corpus", "calibration_manifest", "validation_manifest", "holdout_manifest", "calibration_results", *RESULT_KEYS, "shadow_contract", "acceptance_schema", "final_summary_schema")


def _at(payload: Any, path: str) -> Any:
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def _transform(name: str, values: list[Any]) -> Any:
    if name == "identity":
        if len(values) != 1:
            raise ValueError("identity transform requires one value")
        return values[0]
    if name == "sum":
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
            raise TypeError("sum requires integers")
        return sum(values)
    if name == "boolean_to_mode":
        if len(values) != 1 or not isinstance(values[0], bool):
            raise TypeError("boolean_to_mode requires one boolean")
        return "ENABLED" if values[0] else "DISABLED"
    raise ValueError(f"unknown summary transform: {name}")


def derive_summary(evidence_dir: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field, mapping in SUMMARY_FIELD_SOURCE_MAP.items():
        source_values = []
        for producer_id in mapping["producer_ids"]:
            paths = producer_paths(producer_id, evidence_dir)
            payload = read_json(paths["result"]); meta = read_json(paths["meta"])
            contract = validate_producer_payload_contract(producer_id, payload)
            if contract["result"] != "PASS":
                raise RuntimeError(f"FINALIZER_STOP:summary-source-contract:{producer_id}:{','.join(contract['errors'])}")
            if payload.get("result") == "FAIL" or meta.get("producer_id") != producer_id or meta.get("candidate_sha") != expected_candidate_sha or meta.get("validation_sha") != expected_validation_sha or str(meta.get("run_id")) != expected_run_id or meta.get("exit_code") != 0:
                raise RuntimeError(f"FINALIZER_STOP:summary-source-failed:{producer_id}")
            source_values.append(_at(payload, mapping["json_paths"][0]))
        value = _transform(mapping["transform"], source_values)
        expected_type = mapping["expected_type"]
        valid = ((expected_type == "integer" and isinstance(value, int) and not isinstance(value, bool)) or (expected_type == "boolean" and isinstance(value, bool)) or (expected_type == "string" and isinstance(value, str)))
        if not valid:
            raise RuntimeError(f"FINALIZER_STOP:summary-source-type:{field}")
        values[field] = value
    return values


def _identity_meta(producer_id: str, candidate: str, validation: str, run_id: str, exit_code: int = 0) -> dict[str, Any]:
    return {"producer_id": producer_id, "candidate_sha": candidate, "validation_sha": validation, "run_id": run_id, "exit_code": exit_code}


def _producer_errors(contracts_dir: Path, evidence_dir: Path, expected: tuple[str, str, str], *, include_finalizer: bool = False) -> list[str]:
    errors: list[str] = []
    candidate, validation, run_id = expected
    for producer_id in EVIDENCE_PRODUCERS:
        if producer_id == "finalizer" and not include_finalizer:
            continue
        if producer_id == "acceptance-integrity" and not include_finalizer:
            continue
        paths = producer_paths(producer_id, evidence_dir)
        for kind, path in paths.items():
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"missing-producer:{producer_id}:{kind}")
        if not paths["meta"].is_file() or not paths["result"].is_file():
            continue
        try:
            meta = read_json(paths["meta"]); payload = read_json(paths["result"])
        except (OSError, json.JSONDecodeError):
            errors.append(f"invalid-producer:{producer_id}"); continue
        if meta.get("producer_id") != producer_id or meta.get("candidate_sha") != candidate or meta.get("validation_sha") != validation or str(meta.get("run_id")) != run_id or meta.get("exit_code") != 0:
            errors.append(f"identity-or-exit:{producer_id}")
        if payload.get("result") != "PASS":
            errors.append(f"producer-failed:{producer_id}")
        contract = validate_producer_payload_contract(producer_id, payload)
        if contract["result"] != "PASS":
            errors.extend(f"producer-contract:{producer_id}:{item}" for item in contract["errors"])
    for key in RESULT_KEYS:
        try:
            payload = read_json(contracts_dir / CANONICAL_ARTIFACTS[key])
            if payload.get("result") != "PASS" or payload.get("critical_false_promotions") != 0:
                errors.append(f"canonical-result-failed:{key}")
        except (OSError, json.JSONDecodeError):
            errors.append(f"canonical-result-invalid:{key}")
    return errors


def _require_stage_result(path: Path, expected_count: int, label: str) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get("result") != "PASS" or payload.get("primary_check_count") != expected_count or payload.get("primary_check_fail_count") != 0 or payload.get("primary_check_not_executed_count") != 0:
        raise RuntimeError(f"FINALIZER_STOP:{label}-not-pass")
    return payload


def _require_truth_metrics(payload: dict[str, Any], expected_count: int, label: str) -> None:
    if payload.get("generic_result_only_semantic_proof_count") != 0 or payload.get("specific_field_semantic_proof_count") != expected_count or payload.get("tautological_expected_observed_count") != 0 or payload.get("acceptance_pass_with_failed_semantic_proof_count") != 0 or payload.get("acceptance_pass_with_missing_producer_count") != 0 or payload.get("acceptance_pass_with_contract_invalid_producer_count") != 0:
        raise RuntimeError(f"FINALIZER_STOP:{label}-evidence-truth-metrics")


def validate_final_summary_schema(payload: dict[str, Any], contracts_dir: Path) -> list[str]:
    """Validate the governing schema subset without adding a dependency."""
    schema = read_json(contracts_dir / CANONICAL_ARTIFACTS["final_summary_schema"])
    errors: list[str] = []
    for field in schema.get("required", []):
        if field not in payload:
            errors.append(f"missing:{field}")
    for field, rule in schema.get("properties", {}).items():
        if field not in payload:
            continue
        if "const" in rule and payload[field] != rule["const"]:
            errors.append(f"const:{field}")
        if rule.get("type") == "integer" and (not isinstance(payload[field], int) or isinstance(payload[field], bool)):
            errors.append(f"type:{field}")
        if "minimum" in rule and payload[field] < rule["minimum"]:
            errors.append(f"minimum:{field}")
    return errors


def _write_finalizer_triplet(evidence_dir: Path, candidate: str, validation: str, run_id: str, payload: dict[str, Any]) -> None:
    paths = producer_paths("finalizer", evidence_dir)
    paths["raw"].write_text("finalizer=PASS\n", encoding="utf-8")
    paths["meta"].write_text(json.dumps(_identity_meta("finalizer", candidate, validation, run_id), sort_keys=True) + "\n", encoding="utf-8")
    paths["result"].write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def produce(*, contracts_dir: Path, evidence_dir: Path, pre_finalizer_acceptance_path: Path, pre_finalizer_validation_path: Path, output_path: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_candidate_sha) or not re.fullmatch(r"[0-9a-f]{40}", expected_validation_sha) or not expected_run_id:
        raise RuntimeError("FINALIZER_STOP:invalid-identity")
    expected = (expected_candidate_sha, expected_validation_sha, expected_run_id)
    pre_acceptance = _require_stage_result(pre_finalizer_acceptance_path, 280, "pre-finalizer-acceptance")
    _require_truth_metrics(pre_acceptance, 280, "pre-finalizer-acceptance")
    validation = read_json(pre_finalizer_validation_path)
    if validation.get("result") != "PASS" or validation.get("stage") != "PRE_FINALIZER" or validation.get("check_count") != 280 or validation.get("false_accept_count") != 0 or validation.get("generic_result_only_semantic_proof_count") != 0 or validation.get("specific_field_semantic_proof_count") != 280 or validation.get("tautological_expected_observed_count") != 0:
        raise RuntimeError("FINALIZER_STOP:pre-finalizer-validation-not-pass")
    missing_contracts = [name for key, name in CANONICAL_ARTIFACTS.items() if key in PRE_FINALIZER_KEYS and not (contracts_dir / name).is_file()]
    errors = missing_contracts + _producer_errors(contracts_dir, evidence_dir, expected)
    if errors:
        raise RuntimeError("FINALIZER_STOP:" + ",".join(errors))
    summary = derive_summary(evidence_dir, *expected)
    hashes = {CANONICAL_ARTIFACTS[key]: sha256_file(contracts_dir / CANONICAL_ARTIFACTS[key]) for key in PRE_FINALIZER_KEYS}
    manifest = {"version": 4, "manifest_id": "AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_V1", "freeze_state": "FROZEN", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "taxonomy_revision": TAXONOMY_REVISION, "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION, "classification_envelope_schema_path": CANONICAL_ARTIFACTS["envelope_schema"], "classification_envelope_schema_sha256": sha256_file(contracts_dir / CANONICAL_ARTIFACTS["envelope_schema"]), "phase4_accepted_sha": INPUT_IDENTITIES["phase4_accepted_sha"], "input_identity_manifest_path": CANONICAL_ARTIFACTS["input_identity"], "input_identity_manifest_sha256": sha256_file(contracts_dir / CANONICAL_ARTIFACTS["input_identity"]), "robustness_corpus_path": CANONICAL_ARTIFACTS["corpus"], "robustness_corpus_sha256": sha256_file(contracts_dir / CANONICAL_ARTIFACTS["corpus"]), "artifact_sha256": hashes, "classifier_source_path": "backend/app/services/classifier_v2.py", "classifier_source_sha256": sha256_file(Path(__file__).resolve().parents[2] / "backend/app/services/classifier_v2.py"), "final_commit_identity": "POST_COMMIT_EXTERNAL_HANDOFF", "final_tree_identity": "POST_COMMIT_EXTERNAL_HANDOFF", "recursive_self_hash": False, "synthetic_only": True, "llm_external_call_count": summary["llm_external_call_count"]}
    write_json(evidence_dir / "runtime-freeze-manifest.json", manifest)
    payload = {"version": 1, "producer_id": "finalizer", "result": "PASS", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "derived_summary": summary, **summary, "derived_summary_field_count": len(summary), "summary_source_map_count": len(SUMMARY_FIELD_SOURCE_MAP), "summary_source_map_missing_count": 0, "summary_literal_fallback_count": 0, "handoff_state": "FINALIZER_COMPLETE_PENDING_FULL_ACCEPTANCE", "runtime_freeze_manifest": "runtime-freeze-manifest.json", "synthetic_only": True, "real_data_used": False}
    _write_finalizer_triplet(evidence_dir, expected_candidate_sha, expected_validation_sha, expected_run_id, payload)
    stage_result = {"version": 1, "stage": "FINALIZER_PRODUCE", "result": "PASS", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "derived_summary_field_count": len(summary), "summary_source_map_count": len(SUMMARY_FIELD_SOURCE_MAP), "summary_literal_fallback_count": 0, "handoff_state": "FINALIZER_COMPLETE_PENDING_FULL_ACCEPTANCE", "synthetic_only": True}
    write_json(output_path, stage_result)
    return {"result": "PASS", "summary": summary, "stage_result": stage_result, "manifest": manifest}


def seal(*, contracts_dir: Path, evidence_dir: Path, acceptance_path: Path, validation_path: Path, acceptance_integrity_path: Path, output_path: Path, handoff_path: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> dict[str, Any]:
    expected = (expected_candidate_sha, expected_validation_sha, expected_run_id)
    acceptance = _require_stage_result(acceptance_path, 300, "final-acceptance")
    _require_truth_metrics(acceptance, 300, "final-acceptance")
    validation = read_json(validation_path); integrity = read_json(acceptance_integrity_path); finalizer = read_json(producer_paths("finalizer", evidence_dir)["result"])
    if validation.get("result") != "PASS" or validation.get("stage") != "FINAL" or validation.get("check_count") != 300 or validation.get("false_accept_count") != 0 or validation.get("generic_result_only_semantic_proof_count") != 0 or validation.get("specific_field_semantic_proof_count") != 300 or validation.get("tautological_expected_observed_count") != 0:
        raise RuntimeError("HANDOFF_SEAL_STOP:final-validation-not-pass")
    if integrity.get("result") != "PASS" or integrity.get("draft_check_count") != 290:
        raise RuntimeError("HANDOFF_SEAL_STOP:acceptance-integrity-not-pass")
    if finalizer.get("result") != "PASS" or finalizer.get("derived_summary_field_count") != 17 or finalizer.get("summary_literal_fallback_count") != 0:
        raise RuntimeError("HANDOFF_SEAL_STOP:finalizer-summary-not-complete")
    errors = _producer_errors(contracts_dir, evidence_dir, expected, include_finalizer=True)
    if errors:
        raise RuntimeError("HANDOFF_SEAL_STOP:" + ",".join(errors))
    summary = {field: finalizer[field] for field in REQUIRED_SUMMARY_FIELDS}
    final = {"version": 1, "result": "PASS", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "summary": summary, **summary, "acceptance_check_count": acceptance["primary_check_count"], "failed_acceptance_check_count": acceptance.get("primary_check_fail_count", 0), "required_evidence_files_present": True, "freeze_manifest": "runtime-freeze-manifest.json", "classifier_version": finalizer.get("classifier_version", CLASSIFIER_VERSION), "rules_version": finalizer.get("rules_version", RULES_VERSION), "handoff_state": "READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE", "RUN_EVIDENCE_STATE": "COMPLETE_PASS", "synthetic_only": True, "real_data_used": False}
    schema_errors = validate_final_summary_schema(final, contracts_dir)
    if schema_errors:
        raise RuntimeError("HANDOFF_SEAL_STOP:final-summary-schema:" + ",".join(schema_errors))
    write_json(output_path, final)
    handoff = {"version": 1, "result": "PASS", "stage": "HANDOFF_SEAL", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "final_acceptance_check_count": acceptance["primary_check_count"], "final_validation_result": validation["result"], "finalizer_result": finalizer["result"], "acceptance_integrity_result": integrity["result"], "derived_summary_field_count": len(summary), "runtime_freeze_present": (evidence_dir / "runtime-freeze-manifest.json").is_file(), "synthetic_only": True}
    write_json(handoff_path, handoff)
    return {"result": "PASS", "summary": final, "handoff": handoff}


# Compatibility API for existing repository tests. The production workflow
# uses the explicit produce/seal functions and never uses an implicit stage.
def run(contracts_dir: Path = PHASE5_CONTRACTS, acceptance_path: Path | None = None, evidence_dir: Path | None = None, output_path: Path | None = None, *, expected_candidate_sha: str | None = None, expected_validation_sha: str | None = None, expected_run_id: str | None = None, validation_result_path: Path | None = None, local_test_mode: bool = False) -> dict[str, Any]:
    if evidence_dir is None or acceptance_path is None or validation_result_path is None or not expected_candidate_sha or not expected_validation_sha or not expected_run_id:
        raise RuntimeError("FINALIZER_STOP:required arguments")
    expected = (expected_candidate_sha, expected_validation_sha, expected_run_id)
    acceptance = read_json(acceptance_path)
    if acceptance.get("primary_check_count") != 300:
        return produce(contracts_dir=contracts_dir, evidence_dir=evidence_dir, pre_finalizer_acceptance_path=acceptance_path, pre_finalizer_validation_path=validation_result_path, output_path=output_path or PHASE5_ARTIFACTS / "phase5-final-summary.json", expected_candidate_sha=expected_candidate_sha, expected_validation_sha=expected_validation_sha, expected_run_id=expected_run_id)
    if acceptance.get("result") != "PASS" or acceptance.get("primary_check_fail_count") != 0 or acceptance.get("primary_check_not_executed_count") != 0 or any(check.get("result") != "PASS" for check in acceptance.get("checks", [])):
        raise RuntimeError("FINALIZER_STOP:acceptance-not-pass")
    try:
        validation = read_json(validation_result_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("FINALIZER_STOP:validation-invalid") from exc
    if validation.get("result") != "PASS" or validation.get("false_accept_count") != 0:
        raise RuntimeError("FINALIZER_STOP:validation-not-pass")
    required_contracts = [contracts_dir / CANONICAL_ARTIFACTS[key] for key in PRE_FINALIZER_KEYS]
    if any(not path.is_file() or path.stat().st_size == 0 for path in required_contracts):
        raise RuntimeError("FINALIZER_STOP:missing-contract")
    errors = _producer_errors(contracts_dir, evidence_dir, expected)
    if errors:
        raise RuntimeError("FINALIZER_STOP:" + ",".join(errors))
    summary = derive_summary(evidence_dir, *expected)
    payload = {"version": 1, "result": "PASS", "candidate_sha": expected_candidate_sha, "validation_sha": expected_validation_sha, "run_id": expected_run_id, "derived_summary": summary, **summary, "derived_summary_field_count": len(summary), "summary_source_map_count": len(SUMMARY_FIELD_SOURCE_MAP), "summary_literal_fallback_count": 0, "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION, "freeze_manifest": "runtime-freeze-manifest.json", "handoff_state": "READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE"}
    write_json(output_path or PHASE5_ARTIFACTS / "phase5-final-summary.json", payload)
    _write_finalizer_triplet(evidence_dir, *expected, {"producer_id": "finalizer", **payload})
    return {"summary": payload, "manifest": {}}
