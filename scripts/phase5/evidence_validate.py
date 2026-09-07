from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from acceptance import REQUIREMENT_GROUPS
    from registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, assertion_policy, category_policy_audit, producer_paths, semantic_proofs, validate_producer_payload_contract
except ModuleNotFoundError:
    from .acceptance import REQUIREMENT_GROUPS
    from .registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, assertion_policy, category_policy_audit, producer_paths, semantic_proofs, validate_producer_payload_contract

REQUIRED_FIELDS = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "semantic_proofs", "result"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
STABLE_EVIDENCE_RE = re.compile(r"^evidence://phase5/[a-z0-9_-]+/(?:result|missing|invalid|not-executed)$")
LOCAL_PATH_RE = re.compile(r"(?:^|[\s\"'])(?:/Users/|/home/|/private/tmp/|[A-Za-z]:[\\/])")


def _categories(stage: str) -> list[str]:
    if stage == "PRE_FINALIZER": return [c for c in REQUIREMENT_GROUPS if c not in {"FINALIZER", "EVIDENCE"}]
    if stage == "DRAFT_FINAL": return [c for c in REQUIREMENT_GROUPS if c != "EVIDENCE"]
    if stage == "FINAL": return list(REQUIREMENT_GROUPS)
    raise ValueError(f"unknown validation stage: {stage}")


def _identity_errors(meta: dict[str, Any], producer_id: str, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> list[str]:
    errors = []
    if meta.get("producer_id") != producer_id: errors.append("producer_identity_mismatch")
    if meta.get("candidate_sha") != expected_candidate_sha: errors.append("candidate_identity_mismatch")
    if meta.get("validation_sha") != expected_validation_sha: errors.append("validation_identity_mismatch")
    if str(meta.get("run_id")) != expected_run_id: errors.append("run_identity_mismatch")
    if isinstance(meta.get("exit_code"), bool) or not isinstance(meta.get("exit_code"), int) or meta.get("exit_code") != 0: errors.append("nonzero_or_noninteger_exit_code")
    return errors


def validate(acceptance_path: Path, evidence_dir: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str, stage: str = "FINAL") -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    if not SHA_RE.fullmatch(expected_candidate_sha) or not SHA_RE.fullmatch(expected_validation_sha) or not expected_run_id:
        errors.append({"error": "invalid_expected_identity_arguments"})
    try:
        acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 5, "stage": stage, "result": "FAIL", "error_count": len(errors) + 1, "errors": errors + [{"error": "invalid_acceptance"}]}
    expected_categories = _categories(stage)
    checks = acceptance.get("checks", [])
    if not isinstance(checks, list): checks = []; errors.append({"error": "checks_not_list"})
    policy = assertion_policy(REQUIREMENT_GROUPS)
    policy_audit = category_policy_audit({check.get("category") for check in checks if isinstance(check, dict)}, policy)
    seen: set[str] = set(); fingerprints: set[tuple[Any, ...]] = set(); producer_states: dict[str, str] = {}
    identity_mismatch_count = 0; not_executed_count = 0; self_reference_only_count = 0; missing_required_producer_count = 0; runtime_required_source_only_pass_count = 0; semantic_recompute_count = 0; semantic_recompute_fail_count = 0; semantic_proof_mismatch_count = 0; producer_contract_failure_count = 0; generic_result_only_count = 0; specific_field_count = 0; tautology_count = 0; expected_type_mismatch_count = 0
    contract_failure_producers: set[str] = set()
    contract_failure_errors: dict[str, set[str]] = {}
    contract_failure_reference_count = 0
    assertion_rows_impacted_by_contract_failure: set[str] = set()

    for check in checks:
        if not isinstance(check, dict): errors.append({"error": "check_not_object"}); continue
        missing = sorted(REQUIRED_FIELDS - set(check))
        if missing: errors.append({"check_id": check.get("check_id"), "error": "missing_fields", "fields": missing})
        check_id = check.get("check_id")
        if not isinstance(check_id, str) or not check_id or check_id in seen: errors.append({"check_id": check_id, "error": "duplicate_or_missing_check_id"})
        else: seen.add(check_id)
        category = check.get("category"); assertion = check.get("assertion")
        if category not in expected_categories: errors.append({"check_id": check_id, "error": "stage_category_mismatch", "category": category})
        entry = policy.get((category, assertion))
        evidence_ids = check.get("evidence_ids", [])
        if not isinstance(evidence_ids, list): evidence_ids = []; errors.append({"check_id": check_id, "error": "evidence_ids_not_list"})
        if entry is None:
            errors.append({"check_id": check_id, "error": "unknown_assertion_policy"})
            required_ids = ()
        else:
            required_ids = tuple(entry["required_producer_ids"])
            if set(evidence_ids) != set(required_ids): errors.append({"check_id": check_id, "error": "assertion_policy_mismatch", "required_producer_ids": list(required_ids), "actual_producer_ids": evidence_ids})
            if entry["runtime_required"] and not any(EVIDENCE_PRODUCERS.get(item, {}).get("runtime_required") for item in evidence_ids):
                runtime_required_source_only_pass_count += int(check.get("result") == "PASS"); errors.append({"check_id": check_id, "error": "runtime_required_without_runtime_producer"})
        fingerprint = (check.get("requirement_id"), category, str(assertion).strip().lower(), check.get("method"), tuple(sorted(evidence_ids)))
        if fingerprint in fingerprints: errors.append({"check_id": check_id, "error": "duplicate_assertion"})
        fingerprints.add(fingerprint)
        evidence = check.get("evidence", [])
        if not isinstance(evidence, list) or not evidence: errors.append({"check_id": check_id, "error": "missing_evidence"}); evidence = []
        if any(not isinstance(item, str) or not STABLE_EVIDENCE_RE.fullmatch(item) or LOCAL_PATH_RE.search(item) for item in evidence): errors.append({"check_id": check_id, "error": "unstable_or_local_evidence_reference"})
        if check.get("result") != "PASS": errors.append({"check_id": check_id, "error": "non_pass_primary_check"})
        for producer_id in evidence_ids:
            if producer_id not in EVIDENCE_PRODUCERS: errors.append({"check_id": check_id, "error": "unknown_evidence_id", "producer_id": producer_id}); continue
            paths = producer_paths(producer_id, evidence_dir)
            if any(not path.is_file() or path.stat().st_size == 0 for path in paths.values()):
                missing_required_producer_count += 1; producer_states[producer_id] = "MISSING"; errors.append({"check_id": check_id, "error": "missing_required_producer", "producer_id": producer_id}); continue
            try:
                meta = json.loads(paths["meta"].read_text(encoding="utf-8")); payload = json.loads(paths["result"].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                producer_states[producer_id] = "INVALID"; errors.append({"check_id": check_id, "error": "invalid_producer_json", "producer_id": producer_id}); continue
            state = str(payload.get("result", "FAIL")); producer_states[producer_id] = state
            contract = validate_producer_payload_contract(producer_id, payload)
            if contract["result"] != "PASS":
                producer_contract_failure_count += 1
                contract_failure_reference_count += 1
                contract_failure_producers.add(producer_id)
                assertion_rows_impacted_by_contract_failure.add(f"{category}::{assertion}")
                contract_failure_errors.setdefault(producer_id, set()).update(str(error) for error in contract.get("errors", []))
                errors.append({"check_id": check_id, "error": "producer_result_contract_failure", "producer_id": producer_id, "details": contract["errors"]})
            id_errors = _identity_errors(meta, producer_id, expected_candidate_sha, expected_validation_sha, expected_run_id)
            if id_errors: identity_mismatch_count += len(id_errors); errors.extend({"check_id": check_id, "error": error, "producer_id": producer_id} for error in id_errors)
            if state in {"NOT_EXECUTED", "DRY_RUN"} or meta.get("exit_code") != 0: not_executed_count += 1; errors.append({"check_id": check_id, "error": "producer_not_executed_or_failed", "producer_id": producer_id, "state": state})
            if state != "PASS": errors.append({"check_id": check_id, "error": "producer_result_not_pass", "producer_id": producer_id, "state": state})
        if entry is not None:
            semantic_recompute_count += 1
            recomputed = semantic_proofs(check, evidence_dir, expected_candidate_sha, expected_validation_sha, expected_run_id, REQUIREMENT_GROUPS)
            supplied = check.get("semantic_proofs", [])
            signature = lambda rows: [(row.get("predicate_id"), row.get("producer_id"), row.get("artifact_kind"), row.get("artifact_name"), row.get("json_path"), row.get("observed"), row.get("expected"), row.get("result"), row.get("artifact_sha256"), row.get("observed_from_artifact")) for row in rows]
            if signature(recomputed) != signature(supplied): semantic_proof_mismatch_count += 1; errors.append({"check_id": check_id, "error": "semantic_proof_mismatch"})
            expected_type_mismatch_count += sum(row.get("failure_reason") == "EXPECTED_TYPE_MISMATCH" for row in recomputed)
            if any(row.get("result") != "PASS" for row in recomputed): semantic_recompute_fail_count += 1; errors.append({"check_id": check_id, "error": "semantic_recompute_failed"})
            if recomputed and all(row.get("json_path") == "result" for row in recomputed): generic_result_only_count += 1
            elif recomputed and any(row.get("json_path") != "result" and row.get("observed_from_artifact") is True for row in recomputed): specific_field_count += 1
            tautology_count += sum(1 for row in recomputed if row.get("observed_from_artifact") is not True or not row.get("artifact_sha256") or row.get("json_path") == "result")
    expected_count = sum(len(REQUIREMENT_GROUPS[c]) for c in expected_categories)
    if len(checks) != expected_count or len(seen) != expected_count: errors.append({"error": "stage_check_count_mismatch", "expected": expected_count, "actual": len(seen)})
    if acceptance.get("stage") not in {stage, "LEGACY", None}: errors.append({"error": "stage_mismatch"})
    if acceptance.get("result") != "PASS": errors.append({"error": "acceptance_not_pass"})
    if stage == "FINAL":
        if producer_states.get("finalizer") != "PASS": errors.append({"error": "finalizer_not_pass"})
        if producer_states.get("acceptance-integrity") != "PASS": errors.append({"error": "acceptance_integrity_not_pass"})
    false_accept_count = sum(item.get("error") in {"producer_not_executed_or_failed","producer_result_not_pass","producer_result_contract_failure","runtime_required_without_runtime_producer","candidate_identity_mismatch","validation_identity_mismatch","run_identity_mismatch","producer_identity_mismatch","nonzero_or_noninteger_exit_code","missing_required_producer","assertion_policy_mismatch","unknown_evidence_id","semantic_recompute_failed","semantic_proof_mismatch"} for item in errors)
    return {"version": 6, "stage": stage, "result": "PASS" if not errors else "FAIL", "expected_candidate_sha": expected_candidate_sha, "expected_validation_sha": expected_validation_sha, "expected_run_id": expected_run_id, "required_field_count": len(REQUIRED_FIELDS), "check_count": len(seen), "error_count": len(errors), "unknown_evidence_id_count": sum(item.get("error") == "unknown_evidence_id" for item in errors), "unresolved_evidence_reference_count": sum(item.get("error") in {"missing_required_producer","unstable_or_local_evidence_reference","missing_evidence"} for item in errors), "duplicate_assertion_count": sum(item.get("error") == "duplicate_assertion" for item in errors), "identity_mismatch_count": identity_mismatch_count, "not_executed_count": not_executed_count, "self_reference_only_count": self_reference_only_count, "missing_required_producer_count": missing_required_producer_count, "runtime_required_source_only_pass_count": runtime_required_source_only_pass_count, "false_accept_count": false_accept_count, "assertion_semantic_recompute_count": semantic_recompute_count, "assertion_semantic_recompute_fail_count": semantic_recompute_fail_count, "assertion_semantic_proof_fail_count": semantic_recompute_fail_count, "assertion_semantic_proof_mismatch_count": semantic_proof_mismatch_count, "assertion_proof_type_mismatch_count": expected_type_mismatch_count, "producer_result_contract_failure_count": producer_contract_failure_count, "producer_result_contract_unique_failure_count": len(contract_failure_producers), "producer_result_contract_failed_producer_ids": sorted(contract_failure_producers), "producer_result_contract_failure_reference_count": contract_failure_reference_count, "producer_result_contract_errors_by_producer": {producer: sorted(items) for producer, items in sorted(contract_failure_errors.items())}, "assertion_rows_impacted_by_contract_failure_count": len(assertion_rows_impacted_by_contract_failure), "generic_result_only_semantic_proof_count": generic_result_only_count, "specific_field_semantic_proof_count": specific_field_count, "tautological_expected_observed_count": tautology_count, "category_policy_audit": policy_audit, "producer_states": producer_states, "errors": errors}


def run(evidence_dir: Path, acceptance_path: Path, output: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str, stage: str = "FINAL") -> dict[str, Any]:
    result = validate(acceptance_path, evidence_dir, expected_candidate_sha, expected_validation_sha, expected_run_id, stage)
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps(result, indent=2, sort_keys=True)); return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True); parser.add_argument("--acceptance-result", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidate-sha", required=True); parser.add_argument("--expected-validation-sha", required=True); parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--stage", choices=("PRE_FINALIZER","DRAFT_FINAL","FINAL"), default="FINAL")
    args = parser.parse_args()
    result = run(args.evidence_dir, args.acceptance_result, args.output, args.expected_candidate_sha, args.expected_validation_sha, args.expected_run_id, args.stage)
    raise SystemExit(0 if result["result"] == "PASS" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
