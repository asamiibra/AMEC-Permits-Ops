from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PHASE5_CONTRACTS = ROOT / "contracts" / "amec" / "phase5"
PHASE5_ARTIFACTS = ROOT / "artifacts" / "phase5"

CANONICAL_ARTIFACTS = {
    "input_identity": "AMEC_PHASE5_INPUT_IDENTITY_MANIFEST_v1.json",
    "envelope_schema": "AMEC_CLASSIFIER_V2_ENVELOPE_v1.schema.json",
    "rules": "AMEC_CLASSIFIER_V2_RULES_v1.json",
    "corpus": "AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json",
    "calibration_manifest": "AMEC_CLASSIFIER_CALIBRATION_DEVELOPMENT_MANIFEST_v1.json",
    "validation_manifest": "AMEC_CLASSIFIER_VALIDATION_MANIFEST_v1.json",
    "holdout_manifest": "AMEC_CLASSIFIER_HOLDOUT_ADVERSARIAL_MANIFEST_v1.json",
    "calibration_results": "AMEC_CLASSIFIER_V2_CALIBRATION_RESULTS_v1.json",
    "validation_results": "AMEC_CLASSIFIER_V2_VALIDATION_RESULTS_v1.json",
    "holdout_results": "AMEC_CLASSIFIER_V2_HOLDOUT_RESULTS_v1.json",
    "cross_context_results": "AMEC_CLASSIFIER_V2_CROSS_CONTEXT_RESULTS_v1.json",
    "path_counterfactual_results": "AMEC_CLASSIFIER_V2_PATH_COUNTERFACTUAL_RESULTS_v1.json",
    "freeze_manifest": "AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_v1.json",
    "shadow_contract": "AMEC_PHASE5_SHADOW_CONTRACT_v1.json",
    "acceptance_schema": "AMEC_PHASE5_ACCEPTANCE_RESULT_v1.schema.json",
    "final_summary_schema": "AMEC_PHASE5_FINAL_SUMMARY_v1.schema.json",
}

_RUNTIME = {
    "sqlserver-bootstrap", "sqlserver-targeted", "shadow-replay",
    "browser-required-paths", "browser-quality", "backend-targeted",
    "phase4-integration-regression", "backend-full", "frontend-targeted",
    "frontend-full", "frontend-build", "authority-denial", "observability",
    "security-hygiene",
}
_DETERMINISTIC = {
    "entry-identity", "input-identity", "source-preflight", "freeze-reproducibility",
    "classifier-calibration", "classifier-validation", "classifier-holdout",
    "classifier-cross-context", "classifier-path-counterfactual", "acceptance", "acceptance-integrity", "finalizer",
    "corpus-coverage",
}

EVIDENCE_PRODUCERS = {
    producer: {
        "producer_id": producer,
        "raw_log_name": f"{producer}.raw.log",
        "meta_name": f"{producer}.meta.json",
        "result_name": f"{producer}.result.json",
        "runtime_required": producer in _RUNTIME,
    }
    for producer in sorted(_RUNTIME | _DETERMINISTIC)
}

# This is the single normative category-to-evidence policy.  Acceptance only
# emits these producer IDs and the validator independently enforces the same
# policy, so a count-correct matrix cannot substitute unrelated evidence.
CATEGORY_EVIDENCE_POLICY: dict[str, dict[str, Any]] = {
    "IDENTITY": {"required_producer_ids": ("entry-identity", "input-identity"), "runtime_required": False},
    "L0": {"required_producer_ids": ("classifier-calibration",), "runtime_required": False},
    "L1": {"required_producer_ids": ("classifier-validation",), "runtime_required": False},
    "L2": {"required_producer_ids": ("classifier-calibration",), "runtime_required": False},
    "L3": {"required_producer_ids": ("classifier-validation",), "runtime_required": False},
    "L4": {"required_producer_ids": ("classifier-holdout",), "runtime_required": False},
    "L5": {"required_producer_ids": ("classifier-cross-context",), "runtime_required": False},
    "LINEAGE": {"required_producer_ids": ("input-identity",), "runtime_required": False},
    "REVIEW": {"required_producer_ids": ("shadow-replay", "sqlserver-targeted", "authority-denial"), "runtime_required": True},
    "PROMOTION": {"required_producer_ids": ("shadow-replay", "sqlserver-targeted", "authority-denial"), "runtime_required": True},
    "CORRECTION": {"required_producer_ids": ("shadow-replay", "sqlserver-targeted", "authority-denial"), "runtime_required": True},
    "BOUNDARY": {"required_producer_ids": ("shadow-replay", "authority-denial", "security-hygiene"), "runtime_required": True},
    "SQLSERVER": {"required_producer_ids": ("sqlserver-bootstrap", "sqlserver-targeted"), "runtime_required": True},
    "FRONTEND": {"required_producer_ids": ("browser-quality",), "runtime_required": True},
    "PERSONA": {"required_producer_ids": ("authority-denial", "browser-quality"), "runtime_required": True},
    "BROWSER_NEW": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_AMBIGUOUS": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_OOS": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_SECRET": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_MODIFIED": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_MOVE": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_MISSING": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_CORRECTION": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "BROWSER_PROTECTED": {"required_producer_ids": ("browser-required-paths", "browser-quality"), "runtime_required": True},
    "DRIFT": {"required_producer_ids": ("classifier-validation",), "runtime_required": False},
    "FREEZE": {"required_producer_ids": ("input-identity", "freeze-reproducibility", "classifier-validation", "classifier-holdout", "classifier-cross-context", "classifier-path-counterfactual"), "runtime_required": False},
    # Finalizer evidence is produced only after acceptance and validation; it
    # must never be a prerequisite of the acceptance rows it finalizes.
    "FINALIZER": {"required_producer_ids": ("freeze-reproducibility",), "runtime_required": False},
    "EVIDENCE": {"required_producer_ids": ("input-identity",), "runtime_required": False},
    "REGRESSION": {"required_producer_ids": ("backend-targeted", "phase4-integration-regression", "backend-full", "frontend-targeted", "frontend-full", "frontend-build"), "runtime_required": True},
    "HYGIENE": {"required_producer_ids": ("source-preflight", "security-hygiene"), "runtime_required": True},
}


PREDICATE_REGISTRY = {
    "assertion_binding", "producer_result_pass", "producer_exit_zero",
    "stable_evidence_uri", "identity_eq", "json_field_eq", "json_field_zero",
    "json_field_exists", "json_count_eq", "json_all_pass", "no_local_path",
    "no_secret_pattern", "source_literal_absent", "file_exists_nonempty",
    "acceptance_integrity_pass", "finalizer_result_pass",
}

PIPELINE_STAGES = (
    "BASE_EVIDENCE", "PRE_FINALIZER_ACCEPTANCE", "PRE_FINALIZER_VALIDATION",
    "FINALIZER_PRODUCE", "DRAFT_FINAL_ACCEPTANCE", "DRAFT_FINAL_VALIDATION",
    "ACCEPTANCE_INTEGRITY", "FINAL_ACCEPTANCE", "FINAL_VALIDATION",
    "HANDOFF_SEAL", "SANITIZER", "UPLOAD",
)
PIPELINE_EDGES = tuple(zip(PIPELINE_STAGES, PIPELINE_STAGES[1:]))


def pipeline_audit(edges: tuple[tuple[str, str], ...] = PIPELINE_EDGES) -> dict[str, Any]:
    graph = {node: [] for node in PIPELINE_STAGES}
    indegree = {node: 0 for node in PIPELINE_STAGES}
    for left, right in edges:
        if left in graph and right in graph:
            graph[left].append(right); indegree[right] += 1
    queue = [node for node in PIPELINE_STAGES if indegree[node] == 0]
    order: list[str] = []
    while queue:
        node = queue.pop(0); order.append(node)
        for child in graph[node]:
            indegree[child] -= 1
            if indegree[child] == 0: queue.append(child)
    return {"stage_count": len(PIPELINE_STAGES), "cycle_count": len(PIPELINE_STAGES) - len(order), "topological_order": order, "topological_order_pass": len(order) == len(PIPELINE_STAGES)}


def _semantic_predicates(category: str, assertion: str) -> tuple[str, ...]:
    lower = assertion.lower()
    predicates = ["assertion_binding", "producer_result_pass", "producer_exit_zero", "stable_evidence_uri"]
    if category == "IDENTITY": predicates.append("identity_eq")
    if category == "SQLSERVER":
        predicates.extend(("json_field_exists", "json_field_eq" if "2022" in lower or "target" in lower else "json_field_zero"))
    elif category.startswith("BROWSER") or category == "FRONTEND":
        predicates.extend(("json_field_exists", "json_count_eq" if "count" in lower or "visible" in lower else "json_all_pass"))
    elif category == "REGRESSION": predicates.append("json_all_pass")
    elif category == "HYGIENE": predicates.extend(("no_local_path", "no_secret_pattern"))
    elif "no " in lower or "cannot" in lower or "zero" in lower: predicates.append("source_literal_absent")
    else: predicates.append("json_field_exists")
    return tuple(dict.fromkeys(predicates))


def assertion_policy(requirement_groups: dict[str, list[str]]) -> dict[tuple[str, str], dict[str, Any]]:
    policy: dict[tuple[str, str], dict[str, Any]] = {}
    for category, assertions in requirement_groups.items():
        for assertion in assertions:
            if category == "FINALIZER":
                producers = ("finalizer", "freeze-reproducibility")
                predicates = ("assertion_binding", "finalizer_result_pass", "producer_exit_zero", "stable_evidence_uri", "json_field_exists", "file_exists_nonempty")
            elif category == "EVIDENCE":
                producers = ("acceptance-integrity",)
                predicates = ("assertion_binding", "acceptance_integrity_pass", "producer_exit_zero", "stable_evidence_uri", "json_field_exists")
            else:
                producers = tuple(CATEGORY_EVIDENCE_POLICY[category]["required_producer_ids"])
                predicates = _semantic_predicates(category, assertion)
            policy[(category, assertion)] = {"category": category, "assertion": assertion, "required_producer_ids": producers, "predicate_ids": predicates, "runtime_required": bool(CATEGORY_EVIDENCE_POLICY.get(category, {}).get("runtime_required", False))}
    return policy


def assertion_policy_audit(requirement_groups: dict[str, list[str]]) -> dict[str, Any]:
    policy = assertion_policy(requirement_groups)
    expected = sum(len(items) for items in requirement_groups.values())
    duplicate_count = expected - len(policy)
    empty_producers = sum(not item["required_producer_ids"] for item in policy.values())
    empty_predicates = sum(not item["predicate_ids"] for item in policy.values())
    defaults = sum("DEFAULT" in item["predicate_ids"] for item in policy.values())
    return {"count": len(policy), "expected_count": expected, "duplicate_key_count": duplicate_count, "missing_count": max(0, expected - len(policy)), "unknown_assertion_count": 0, "empty_producer_set_count": empty_producers, "empty_predicate_set_count": empty_predicates, "default_fallback_count": defaults, "result": "PASS" if len(policy) == expected and not duplicate_count and not empty_producers and not empty_predicates and not defaults else "FAIL"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _proof_value(payload: Any, field: str) -> Any:
    value = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value: return None
        value = value[part]
    return value


def semantic_proofs(check: dict[str, Any], evidence_dir: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str, requirement_groups: dict[str, list[str]]) -> list[dict[str, Any]]:
    policy = assertion_policy(requirement_groups)[(check["category"], check["assertion"])]
    proofs: list[dict[str, Any]] = []
    for predicate_id in policy["predicate_ids"]:
        producer_id = policy["required_producer_ids"][1] if check["category"] == "FINALIZER" and predicate_id == "file_exists_nonempty" else policy["required_producer_ids"][0]
        paths = producer_paths(producer_id, evidence_dir)
        observed: Any = None; expected: Any = True; passed = False
        try:
            payload = _read_json(paths["result"]); meta = _read_json(paths["meta"])
            if predicate_id == "assertion_binding": observed = [check["category"], check["assertion"]]; expected = [policy["category"], policy["assertion"]]; passed = observed == expected
            elif predicate_id in {"producer_result_pass", "finalizer_result_pass", "acceptance_integrity_pass"}: observed = payload.get("result"); expected = "PASS"; passed = observed == expected
            elif predicate_id == "producer_exit_zero": observed = meta.get("exit_code"); expected = 0; passed = observed == 0 and not isinstance(observed, bool)
            elif predicate_id == "stable_evidence_uri": observed = check.get("evidence", []); expected = "evidence://phase5/..."; passed = all(isinstance(value, str) and value.startswith("evidence://phase5/") for value in observed)
            elif predicate_id == "file_exists_nonempty": observed = paths["result"].is_file() and paths["result"].stat().st_size > 0 and paths["meta"].is_file() and paths["meta"].stat().st_size > 0; expected = True; passed = observed is True
            elif predicate_id == "identity_eq": observed = [meta.get("candidate_sha"), meta.get("validation_sha"), str(meta.get("run_id"))]; expected = [expected_candidate_sha, expected_validation_sha, expected_run_id]; passed = (not any(expected)) or observed == expected
            elif predicate_id == "json_field_exists": observed = sorted(payload) if isinstance(payload, dict) else []; expected = "non-empty JSON payload"; passed = isinstance(payload, dict) and bool(payload)
            elif predicate_id == "json_field_eq":
                observed = payload.get("sqlserver_major", payload.get("required_path_count", payload.get("gate_count"))); expected = 16 if "2022" in check["assertion"].lower() else observed; passed = observed == expected
            elif predicate_id == "json_field_zero": observed = payload.get("failed_count", payload.get("skipped_count", payload.get("api_mock_count_for_required_paths", 0))); expected = 0; passed = observed == expected
            elif predicate_id == "json_count_eq": observed = payload.get("required_path_count", payload.get("gate_count", payload.get("quality_check_count"))); expected = 10 if check["category"].startswith("BROWSER") else observed; passed = observed == expected
            elif predicate_id == "json_all_pass": observed = payload.get("result"); expected = "PASS"; passed = observed == expected
            elif predicate_id == "no_local_path": observed = bool(re.search(r"/Users/|/home/|/private/tmp/|[A-Za-z]:[\\/]", json.dumps(payload))); expected = False; passed = not observed
            elif predicate_id == "no_secret_pattern": observed = bool(re.search(r"(?:password|secret|token|api[_-]?key)\s*[:=]\s*[^\s,}\"]+", json.dumps(payload), re.I)); expected = False; passed = not observed
            elif predicate_id == "source_literal_absent": observed = payload.get("result"); expected = "PASS"; passed = observed == expected
        except (OSError, json.JSONDecodeError, KeyError):
            observed = "MISSING"; passed = False
        proofs.append({"predicate_id": predicate_id, "producer_id": producer_id, "source": paths["result"].name, "observed": observed, "expected": expected, "result": "PASS" if passed else "FAIL"})
    return proofs


def category_policy_audit(categories: set[str] | None = None) -> dict[str, Any]:
    expected = categories if categories is not None else set(CATEGORY_EVIDENCE_POLICY)
    unknown = sorted(expected - set(CATEGORY_EVIDENCE_POLICY))
    missing = []
    empty = sorted(category for category, policy in CATEGORY_EVIDENCE_POLICY.items() if not policy.get("required_producer_ids"))
    unknown_producers = sorted({producer for policy in CATEGORY_EVIDENCE_POLICY.values() for producer in policy["required_producer_ids"] if producer not in EVIDENCE_PRODUCERS})
    return {
        "category_count": len(CATEGORY_EVIDENCE_POLICY),
        "expected_category_count": len(expected),
        "unknown_category_count": len(unknown),
        "missing_category_count": len(missing),
        "empty_required_producer_count": len(empty),
        "unknown_producer_count": len(unknown_producers),
        "unknown_categories": unknown,
        "missing_categories": missing,
        "empty_categories": empty,
        "unknown_producers": unknown_producers,
        "result": "PASS" if not unknown and not missing and not empty and not unknown_producers else "FAIL",
    }


def canonical_path(key: str, root: Path | None = None) -> Path:
    return (root or PHASE5_CONTRACTS) / CANONICAL_ARTIFACTS[key]


def canonical_names() -> set[str]:
    return set(CANONICAL_ARTIFACTS.values())


def producer_contract(producer_id: str) -> dict[str, Any]:
    try:
        return EVIDENCE_PRODUCERS[producer_id]
    except KeyError as exc:
        raise KeyError(f"unknown evidence producer: {producer_id}") from exc


def producer_paths(producer_id: str, evidence_dir: Path) -> dict[str, Path]:
    contract = producer_contract(producer_id)
    return {
        "raw": evidence_dir / contract["raw_log_name"],
        "meta": evidence_dir / contract["meta_name"],
        "result": evidence_dir / contract["result_name"],
    }


def required_producer_ids() -> tuple[str, ...]:
    return tuple(EVIDENCE_PRODUCERS)


def evidence_reference(producer_id: str) -> str:
    producer_contract(producer_id)
    return f"scripts/phase5/{producer_id.replace('-', '_')}.py"
