from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from common import read_json
    from registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, category_policy_audit, producer_paths
except ModuleNotFoundError:
    from .common import read_json
    from .registry import CATEGORY_EVIDENCE_POLICY, EVIDENCE_PRODUCERS, category_policy_audit, producer_paths


REQUIRED_FIELDS = {"check_id", "requirement_id", "category", "assertion", "method", "evidence", "evidence_ids", "basis_refs", "result"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
STABLE_EVIDENCE_RE = re.compile(r"^evidence://phase5/[a-z0-9_-]+/(?:result|missing|invalid|not-executed)$")
LOCAL_PATH_RE = re.compile(r"(?:^|[\s\"'])(?:/Users/|/home/|/private/tmp/|[A-Za-z]:[\\/])")


def _identity_errors(meta: dict[str, Any], producer_id: str, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> list[str]:
    errors: list[str] = []
    if meta.get("producer_id") != producer_id:
        errors.append("producer_identity_mismatch")
    if meta.get("candidate_sha") != expected_candidate_sha:
        errors.append("candidate_identity_mismatch")
    if meta.get("validation_sha") != expected_validation_sha:
        errors.append("validation_identity_mismatch")
    if str(meta.get("run_id")) != expected_run_id:
        errors.append("run_identity_mismatch")
    if isinstance(meta.get("exit_code"), bool) or not isinstance(meta.get("exit_code"), int) or meta.get("exit_code") != 0:
        errors.append("nonzero_or_noninteger_exit_code")
    return errors


def validate(acceptance_path: Path, evidence_dir: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    if not SHA_RE.fullmatch(expected_candidate_sha) or not SHA_RE.fullmatch(expected_validation_sha) or not expected_run_id:
        errors.append({"error": "invalid_expected_identity_arguments"})
    try:
        acceptance = read_json(acceptance_path)
    except (OSError, json.JSONDecodeError):
        return {"version": 4, "result": "FAIL", "error_count": len(errors) + 1, "errors": errors + [{"error": "invalid_acceptance"}]}

    checks = acceptance.get("checks", [])
    if not isinstance(checks, list):
        checks = []
        errors.append({"error": "checks_not_list"})
    categories = {check.get("category") for check in checks if isinstance(check, dict)}
    policy_audit = category_policy_audit(categories)
    seen: set[str] = set()
    fingerprints: set[tuple[Any, ...]] = set()
    producer_states: dict[str, str] = {}
    identity_mismatch_count = 0
    not_executed_count = 0
    self_reference_only_count = 0
    missing_required_producer_count = 0
    runtime_required_source_only_pass_count = 0

    for check in checks:
        if not isinstance(check, dict):
            errors.append({"error": "check_not_object"})
            continue
        missing = sorted(REQUIRED_FIELDS - set(check))
        if missing:
            errors.append({"check_id": check.get("check_id"), "error": "missing_fields", "fields": missing})
        check_id = check.get("check_id")
        if not isinstance(check_id, str) or not check_id or check_id in seen:
            errors.append({"check_id": check_id, "error": "duplicate_or_missing_check_id"})
        else:
            seen.add(check_id)
        evidence_ids = check.get("evidence_ids", [])
        if not isinstance(evidence_ids, list):
            evidence_ids = []
            errors.append({"check_id": check_id, "error": "evidence_ids_not_list"})
        category = check.get("category")
        policy = CATEGORY_EVIDENCE_POLICY.get(category)
        if policy is None:
            errors.append({"check_id": check_id, "error": "unknown_category", "category": category})
            required_ids: tuple[str, ...] = ()
        else:
            required_ids = tuple(policy["required_producer_ids"])
            if set(evidence_ids) != set(required_ids):
                errors.append({"check_id": check_id, "error": "category_policy_mismatch", "required_producer_ids": list(required_ids), "actual_producer_ids": evidence_ids})
            if policy["runtime_required"] and not any(EVIDENCE_PRODUCERS.get(item, {}).get("runtime_required") for item in evidence_ids):
                runtime_required_source_only_pass_count += int(check.get("result") == "PASS")
                errors.append({"check_id": check_id, "error": "runtime_required_without_runtime_producer"})
        fingerprint = (check.get("requirement_id"), category, str(check.get("assertion", "")).strip().lower(), check.get("method"), tuple(sorted(evidence_ids)))
        if fingerprint in fingerprints:
            errors.append({"check_id": check_id, "error": "duplicate_assertion"})
        fingerprints.add(fingerprint)
        evidence = check.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            errors.append({"check_id": check_id, "error": "missing_evidence"})
            evidence = []
        if any(not isinstance(item, str) or not STABLE_EVIDENCE_RE.fullmatch(item) or LOCAL_PATH_RE.search(item) for item in evidence):
            errors.append({"check_id": check_id, "error": "unstable_or_local_evidence_reference"})
        if evidence and all("acceptance.py" in item or "evidence_validate.py" in item for item in evidence if isinstance(item, str)):
            self_reference_only_count += 1
            errors.append({"check_id": check_id, "error": "self_reference_only"})
        if check.get("result") != "PASS":
            errors.append({"check_id": check_id, "error": "non_pass_primary_check"})

        for producer_id in evidence_ids:
            if producer_id not in EVIDENCE_PRODUCERS:
                errors.append({"check_id": check_id, "error": "unknown_evidence_id", "producer_id": producer_id})
                continue
            paths = producer_paths(producer_id, evidence_dir)
            if any(not path.is_file() or path.stat().st_size == 0 for path in paths.values()):
                missing_required_producer_count += 1
                producer_states[producer_id] = "MISSING"
                errors.append({"check_id": check_id, "error": "missing_required_producer", "producer_id": producer_id})
                continue
            try:
                meta = read_json(paths["meta"])
                payload = read_json(paths["result"])
            except (OSError, json.JSONDecodeError):
                producer_states[producer_id] = "INVALID"
                errors.append({"check_id": check_id, "error": "invalid_producer_json", "producer_id": producer_id})
                continue
            state = str(payload.get("result", "FAIL"))
            producer_states[producer_id] = state
            id_errors = _identity_errors(meta, producer_id, expected_candidate_sha, expected_validation_sha, expected_run_id)
            if id_errors:
                identity_mismatch_count += len(id_errors)
                errors.extend({"check_id": check_id, "error": error, "producer_id": producer_id} for error in id_errors)
            if state in {"NOT_EXECUTED", "DRY_RUN"} or meta.get("exit_code") != 0:
                not_executed_count += 1
                errors.append({"check_id": check_id, "error": "producer_not_executed_or_failed", "producer_id": producer_id, "state": state})
            if state != "PASS":
                errors.append({"check_id": check_id, "error": "producer_result_not_pass", "producer_id": producer_id, "state": state})

    if acceptance.get("result") != "PASS":
        errors.append({"error": "acceptance_not_pass"})
    if acceptance.get("primary_check_count") != 300 or len(seen) != 300:
        errors.append({"error": "primary_check_count_not_exact_300"})
    if policy_audit["result"] != "PASS" or policy_audit["category_count"] != 30:
        errors.append({"error": "category_policy_audit_failed", "audit": policy_audit})
    false_accept_count = sum(item.get("error") in {
        "producer_not_executed_or_failed", "producer_result_not_pass", "runtime_required_without_runtime_producer",
        "candidate_identity_mismatch", "validation_identity_mismatch", "run_identity_mismatch", "producer_identity_mismatch",
        "nonzero_or_noninteger_exit_code", "missing_required_producer", "category_policy_mismatch", "unknown_evidence_id",
    } for item in errors)
    return {
        "version": 4,
        "result": "PASS" if not errors else "FAIL",
        "expected_candidate_sha": expected_candidate_sha,
        "expected_validation_sha": expected_validation_sha,
        "expected_run_id": expected_run_id,
        "required_field_count": len(REQUIRED_FIELDS), "check_count": len(seen), "error_count": len(errors),
        "unknown_evidence_id_count": sum(item.get("error") == "unknown_evidence_id" for item in errors),
        "unresolved_evidence_reference_count": sum(item.get("error") in {"missing_required_producer", "unstable_or_local_evidence_reference", "missing_evidence"} for item in errors),
        "duplicate_assertion_count": sum(item.get("error") == "duplicate_assertion" for item in errors),
        "identity_mismatch_count": identity_mismatch_count,
        "not_executed_count": not_executed_count,
        "self_reference_only_count": self_reference_only_count,
        "missing_required_producer_count": missing_required_producer_count,
        "runtime_required_source_only_pass_count": runtime_required_source_only_pass_count,
        "false_accept_count": false_accept_count,
        "category_policy_audit": policy_audit,
        "producer_states": producer_states,
        "errors": errors,
    }


def run(evidence_dir: Path, acceptance_path: Path, output: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str) -> dict[str, Any]:
    result = validate(acceptance_path, evidence_dir, expected_candidate_sha, expected_validation_sha, expected_run_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--acceptance-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-candidate-sha", required=True)
    parser.add_argument("--expected-validation-sha", required=True)
    parser.add_argument("--expected-run-id", required=True)
    args = parser.parse_args()
    result = run(args.evidence_dir, args.acceptance_result, args.output, args.expected_candidate_sha, args.expected_validation_sha, args.expected_run_id)
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
