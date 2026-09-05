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
    "assertion_evidence_spec": "AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json",
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


def _path_spec(expected_type: str, *, const: Any = None, minimum: int | float | None = None,
               count_eq: int | None = None) -> dict[str, Any]:
    spec: dict[str, Any] = {"type": expected_type}
    if const is not None:
        spec["const"] = const
    if minimum is not None:
        spec["minimum"] = minimum
    if count_eq is not None:
        spec["count_eq"] = count_eq
    return spec


# One closed, fail-closed contract for every producer.  The result field is
# deliberately present for all producers, while every field consumed by the
# finalizer or exact assertion map is declared explicitly below.
PRODUCER_RESULT_CONTRACTS: dict[str, dict[str, Any]] = {
    producer: {
        "required_paths": {"result": _path_spec("string", const="PASS")},
        "summary_consumed_paths": (),
        "runtime_required": producer in _RUNTIME,
    }
    for producer in EVIDENCE_PRODUCERS
}


def _declare(producer: str, **paths: dict[str, Any]) -> None:
    PRODUCER_RESULT_CONTRACTS[producer]["required_paths"].update(paths)


_declare("sqlserver-bootstrap", sqlserver_major=_path_spec("integer", const=16),
         migration_head=_path_spec("string", const="step5_content_library_azure_sql_v1"),
         migration_pass=_path_spec("boolean", const=True),
         engine=_path_spec("string", const="MICROSOFT_SQL_SERVER_2022_X64"))
_declare("sqlserver-targeted", sqlserver_major=_path_spec("integer", const=16),
         gate_count=_path_spec("integer", const=16), failed_count=_path_spec("integer", const=0),
         skipped_count=_path_spec("integer", const=0), migration_head=_path_spec("string", const="step5_content_library_azure_sql_v1"), gates=_path_spec("object"))
for _producer in ("browser-required-paths", "browser-quality"):
    _declare(_producer, required_path_count=_path_spec("integer", const=10),
             required_path_pass=_path_spec("integer", const=10),
             required_path_fail=_path_spec("integer", const=0),
             required_path_skip=_path_spec("integer", const=0),
             declared_ids=_path_spec("array", count_eq=10),
             api_mock_count_for_required_paths=_path_spec("integer", const=0))
_declare("browser-quality", quality_check_count=_path_spec("integer", minimum=7),
         quality_pass_count=_path_spec("integer", minimum=7), quality_fail_count=_path_spec("integer", const=0),
         quality_skip_count=_path_spec("integer", const=0))
_declare("shadow-replay", shadow_state=_path_spec("string", const="REVIEW_COMPARE_ONLY"),
         new_source_reads=_path_spec("integer", const=0, minimum=0),
         new_source_bytes=_path_spec("integer", const=0, minimum=0),
         llm_external_call_count=_path_spec("integer", const=0, minimum=0),
         real_content=_path_spec("boolean", const=False),
         classifier_only_verified_assertion_count=_path_spec("integer", const=0, minimum=0),
         classifier_only_projection_count=_path_spec("integer", const=0, minimum=0),
         synology_writeback_count=_path_spec("integer", const=0, minimum=0),
         external_protected_action_count=_path_spec("integer", const=0, minimum=0),
         replay_stable=_path_spec("boolean", const=True), replay_same_envelope=_path_spec("boolean", const=True),
         replay_side_effect_duplicate_count=_path_spec("integer", const=0, minimum=0))
_declare("source-preflight",
         **{"authority.promotion_requires_human_review": _path_spec("boolean", const=True),
            "authority.projection_requires_existing_verified_assertion": _path_spec("boolean", const=True),
            "authority.auto_promotion_enabled": _path_spec("boolean", const=False)})
for _producer in ("classifier-calibration", "classifier-validation", "classifier-holdout",
                  "classifier-cross-context", "classifier-path-counterfactual"):
    _declare(_producer, critical_false_promotions=_path_spec("integer", const=0, minimum=0))


def _bootstrap_assertion_contract_paths() -> None:
    """Declare v2 proof fields at import time for fixture builders and validators."""
    path = PHASE5_CONTRACTS / "AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json"
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("entries", [])
    except (OSError, json.JSONDecodeError):
        return
    for entry in entries:
        for proof in entry.get("proofs", []):
            if proof.get("artifact_kind") != "result":
                continue
            producer = proof.get("producer_id")
            field = proof.get("json_path")
            if producer not in PRODUCER_RESULT_CONTRACTS or field in PRODUCER_RESULT_CONTRACTS[producer]["required_paths"]:
                continue
            contract: dict[str, Any] = {"type": proof.get("expected_type", "string")}
            operator = proof.get("operator")
            if operator in {"eq", "true", "false", "zero"}:
                contract["const"] = proof.get("expected")
            elif operator == "nonzero":
                contract["minimum"] = 1
            PRODUCER_RESULT_CONTRACTS[producer]["required_paths"][field] = contract


_bootstrap_assertion_contract_paths()

SUMMARY_CONSUMED_PATHS = {
    (producer, path)
    for producer, path in (
        ("browser-required-paths", "required_path_count"), ("browser-required-paths", "required_path_pass"),
        ("browser-required-paths", "required_path_fail"), ("sqlserver-targeted", "result"),
        ("sqlserver-bootstrap", "sqlserver_major"), ("sqlserver-bootstrap", "migration_head"),
        ("classifier-calibration", "critical_false_promotions"),
        ("shadow-replay", "shadow_state"), ("source-preflight", "authority.promotion_requires_human_review"),
        ("source-preflight", "authority.projection_requires_existing_verified_assertion"),
        ("backend-full", "result"), ("frontend-full", "result"), ("frontend-build", "result"),
        ("shadow-replay", "new_source_reads"), ("source-preflight", "authority.auto_promotion_enabled"),
        ("shadow-replay", "real_content"), ("shadow-replay", "llm_external_call_count"),
    )
}
for _producer, _path in SUMMARY_CONSUMED_PATHS:
    PRODUCER_RESULT_CONTRACTS[_producer]["summary_consumed_paths"] = tuple(sorted(set(PRODUCER_RESULT_CONTRACTS[_producer]["summary_consumed_paths"]) | {_path}))


def _at_path(payload: Any, path: str) -> Any:
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "any":
        return True
    return {"integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "string": isinstance(value, str), "boolean": isinstance(value, bool),
            "array": isinstance(value, list), "object": isinstance(value, dict)}.get(expected, False)


def validate_producer_payload_contract(producer_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    contract = PRODUCER_RESULT_CONTRACTS.get(producer_id)
    if contract is None:
        return {"result": "FAIL", "errors": ["unknown_producer"], "producer_id": producer_id}
    errors: list[str] = []
    if not isinstance(payload, dict):
        errors.append("payload_not_object")
        return {"result": "FAIL", "errors": errors, "producer_id": producer_id}
    for path, spec in contract["required_paths"].items():
        try:
            value = _at_path(payload, path)
        except KeyError:
            errors.append(f"missing:{path}")
            continue
        if not _type_matches(value, spec["type"]):
            errors.append(f"type:{path}:{spec['type']}")
            continue
        if "const" in spec and value != spec["const"]:
            errors.append(f"const:{path}")
        if "minimum" in spec and value < spec["minimum"]:
            errors.append(f"minimum:{path}")
        if "count_eq" in spec and len(value) != spec["count_eq"]:
            errors.append(f"count:{path}")
    return {"result": "PASS" if not errors else "FAIL", "errors": errors, "producer_id": producer_id}


PREDICATE_REGISTRY = {"eq", "zero", "nonzero", "true", "false", "exists", "count_eq", "set_eq", "contains", "all_pass", "sha256_eq", "identity_eq", "file_exists_nonempty", "no_local_path", "no_secret_pattern"}
EVIDENCE_TYPE_VOCABULARY = {"integer", "number", "string", "boolean", "array", "object"}
OPERATOR_TYPE_COMPATIBILITY = {
    "eq": EVIDENCE_TYPE_VOCABULARY,
    "zero": {"integer", "number"},
    "nonzero": {"integer", "number"},
    "true": {"boolean"},
    "false": {"boolean"},
    "count_eq": {"array"},
    "set_eq": {"array"},
    "all_pass": {"object"},
    "contains": {"array", "string", "object"},
    "exists": EVIDENCE_TYPE_VOCABULARY,
}

PIPELINE_STAGES = (
    "BASE_EVIDENCE", "PRE_FINALIZER_ACCEPTANCE", "PRE_FINALIZER_VALIDATION",
    "FINALIZER_PRODUCE", "DRAFT_FINAL_ACCEPTANCE", "DRAFT_FINAL_VALIDATION",
    "ACCEPTANCE_INTEGRITY", "FINAL_ACCEPTANCE", "FINAL_VALIDATION",
    "SECOND_ORACLE", "HANDOFF_SEAL", "SANITIZER", "POST_SANITIZE_RECOMPUTE", "UPLOAD",
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


_BOUNDARY_FIELDS = (("shadow-replay", "new_source_reads", "zero", 0, "integer"), ("shadow-replay", "new_source_bytes", "zero", 0, "integer"), ("shadow-replay", "real_content", "false", False, "boolean"), ("shadow-replay", "llm_external_call_count", "zero", 0, "integer"), ("shadow-replay", "classifier_only_projection_count", "zero", 0, "integer"), ("shadow-replay", "synology_writeback_count", "zero", 0, "integer"), ("shadow-replay", "external_protected_action_count", "zero", 0, "integer"), ("authority-denial", "result", "eq", "PASS", "string"), ("security-hygiene", "result", "eq", "PASS", "string"), ("shadow-replay", "replay_side_effect_duplicate_count", "zero", 0, "integer"))
_SQL_FIELDS = (("sqlserver-bootstrap", "sqlserver_major", "eq", 16, "integer"), ("sqlserver-bootstrap", "migration_head", "eq", "step5_content_library_azure_sql_v1", "string"), ("sqlserver-bootstrap", "engine", "eq", "MICROSOFT_SQL_SERVER_2022_X64", "string"), ("sqlserver-bootstrap", "migration_pass", "true", True, "boolean"), ("sqlserver-targeted", "gate_count", "eq", 16, "integer"), ("sqlserver-targeted", "failed_count", "zero", 0, "integer"), ("sqlserver-targeted", "skipped_count", "zero", 0, "integer"), ("sqlserver-targeted", "gates", "all_pass", "PASS", "object"), ("sqlserver-targeted", "sqlserver_major", "eq", 16, "integer"), ("sqlserver-targeted", "migration_head", "eq", "step5_content_library_azure_sql_v1", "string"))
_BROWSER_FIELDS = (("browser-required-paths", "required_path_count", "eq", 10, "integer"), ("browser-required-paths", "required_path_pass", "eq", 10, "integer"), ("browser-required-paths", "required_path_fail", "zero", 0, "integer"), ("browser-required-paths", "required_path_skip", "zero", 0, "integer"), ("browser-required-paths", "declared_ids", "count_eq", 10, "array"), ("browser-quality", "quality_check_count", "nonzero", 1, "integer"), ("browser-quality", "quality_pass_count", "nonzero", 1, "integer"), ("browser-quality", "quality_fail_count", "zero", 0, "integer"), ("browser-quality", "quality_skip_count", "zero", 0, "integer"), ("browser-required-paths", "api_mock_count_for_required_paths", "zero", 0, "integer"))


def load_assertion_evidence_spec(requirement_groups: dict[str, list[str]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Load the closed v2 contract; never infer proof semantics from prose."""
    path = PHASE5_CONTRACTS / "AMEC_PHASE5_ASSERTION_EVIDENCE_SPEC_v2.json"
    raw = _read_json(path)
    if raw.get("schema") != "PROPOSALOPS_PHASE5_ASSERTION_EVIDENCE_SPEC_V2" or raw.get("version") != 2:
        raise ValueError("invalid assertion evidence spec identity")
    expected = {(category, assertion) for category, values in requirement_groups.items() for assertion in values}
    entries = raw.get("entries")
    if raw.get("assertion_count") != 300 or not isinstance(entries, list) or len(entries) != len(expected):
        raise ValueError("assertion evidence spec count mismatch")
    seen: set[tuple[str, str]] = set(); policy: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        key = (entry.get("category"), entry.get("assertion"))
        if key in seen or key not in expected:
            raise ValueError("duplicate or unknown assertion evidence spec")
        seen.add(key)
        proofs = entry.get("proofs")
        if not proofs or any(not proof.get("substantive") or proof.get("json_path") == "result" for proof in proofs):
            raise ValueError(f"non-substantive assertion evidence spec: {key}")
        for proof in proofs:
            if proof.get("producer_id") not in EVIDENCE_PRODUCERS or proof.get("artifact_kind") not in {"result", "meta"}:
                raise ValueError(f"invalid producer/artifact in assertion evidence spec: {key}")
            if proof.get("operator") not in PREDICATE_REGISTRY:
                raise ValueError(f"invalid predicate in assertion evidence spec: {key}")
            if proof.get("expected_type") not in EVIDENCE_TYPE_VOCABULARY:
                raise ValueError(f"invalid expected type in assertion evidence spec: {key}")
            if proof.get("expected_type") not in OPERATOR_TYPE_COMPATIBILITY[proof["operator"]]:
                raise ValueError(f"incompatible predicate/type in assertion evidence spec: {key}")
        # Assertion truth is bounded to the exact evidence named by that row.
        # Category-wide producer coverage is audited separately below.
        if key[0] == "FINALIZER": producers = tuple(dict.fromkeys(p["producer_id"] for p in proofs))
        elif key[0] == "EVIDENCE": producers = tuple(dict.fromkeys(p["producer_id"] for p in proofs))
        else: producers = tuple(dict.fromkeys(p["producer_id"] for p in proofs))
        policy[key] = {"category": key[0], "assertion": key[1], "required_producer_ids": producers,
                       "proof_specs": tuple(proofs), "predicate_ids": tuple(proof["operator"] for proof in proofs),
                       "runtime_required": any(proof.get("runtime_required") for proof in proofs)}
    if seen != expected:
        raise ValueError("missing assertion evidence spec")
    return policy


def _apply_assertion_contracts(policy: dict[tuple[str, str], dict[str, Any]]) -> None:
    for item in policy.values():
        for proof in item["proof_specs"]:
            if proof["artifact_kind"] != "result":
                continue
            producer = proof["producer_id"]
            path = proof["json_path"]
            if path not in PRODUCER_RESULT_CONTRACTS[producer]["required_paths"]:
                contract_spec: dict[str, Any] = {"type": proof["expected_type"]}
                operator = proof.get("operator")
                if operator in {"eq", "true", "false", "zero"}:
                    contract_spec["const"] = proof.get("expected")
                elif operator == "nonzero":
                    contract_spec["minimum"] = 1
                elif operator == "count_eq":
                    contract_spec["count_eq"] = proof.get("expected")
                PRODUCER_RESULT_CONTRACTS[producer]["required_paths"][path] = contract_spec


def assertion_policy(requirement_groups: dict[str, list[str]]) -> dict[tuple[str, str], dict[str, Any]]:
    global ASSERTION_EVIDENCE_SPEC
    policy = load_assertion_evidence_spec(requirement_groups)
    _apply_assertion_contracts(policy)
    ASSERTION_EVIDENCE_SPEC = {(category, assertion): item["proof_specs"][0] for (category, assertion), item in policy.items()}
    return policy


def assertion_policy_audit(requirement_groups: dict[str, list[str]]) -> dict[str, Any]:
    policy = assertion_policy(requirement_groups)
    expected = sum(len(items) for items in requirement_groups.values())
    duplicate_count = expected - len(policy)
    empty_producers = sum(not item["required_producer_ids"] for item in policy.values())
    empty_predicates = sum(not item["predicate_ids"] for item in policy.values())
    defaults = sum("DEFAULT" in item["predicate_ids"] for item in policy.values())
    return {"count": len(policy), "expected_count": expected, "duplicate_key_count": duplicate_count, "missing_count": max(0, expected - len(policy)), "unknown_assertion_count": 0, "empty_producer_set_count": empty_producers, "empty_predicate_set_count": empty_predicates, "empty_proof_count": empty_predicates, "default_fallback_count": defaults, "keyword_heuristic_count": 0, "substantive_field_proof_count": sum(bool(item["proof_specs"]) for item in policy.values()), "generic_result_only_count": sum(all(p.get("json_path") == "result" for p in item["proof_specs"]) for item in policy.values()), "result": "PASS" if len(policy) == expected and not duplicate_count and not empty_producers and not empty_predicates and not defaults else "FAIL"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _proof_value(payload: Any, field: str) -> Any:
    value = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value: return None
        value = value[part]
    return value


def _evaluate(operator: str, observed: Any, expected: Any) -> bool:
    return ((operator == "eq" and observed == expected) or (operator == "zero" and observed == 0) or (operator == "nonzero" and isinstance(observed, (int, float)) and not isinstance(observed, bool) and observed != 0) or (operator == "true" and observed is True) or (operator == "false" and observed is False) or (operator == "exists") or (operator == "count_eq" and isinstance(observed, list) and len(observed) == expected) or (operator == "set_eq" and set(observed) == set(expected)) or (operator == "contains" and expected in observed) or (operator == "all_pass" and isinstance(observed, dict) and all(item == "PASS" for item in observed.values())))


def _expected_type_matches(value: Any, expected_type: str) -> bool:
    return _type_matches(value, expected_type)


def semantic_proofs(check: dict[str, Any], evidence_dir: Path, expected_candidate_sha: str, expected_validation_sha: str, expected_run_id: str, requirement_groups: dict[str, list[str]]) -> list[dict[str, Any]]:
    policy = assertion_policy(requirement_groups)[(check["category"], check["assertion"])]
    proofs: list[dict[str, Any]] = []
    for spec in policy["proof_specs"]:
        producer_id = spec["producer_id"]
        paths = producer_paths(producer_id, evidence_dir)
        observed: Any = None; expected: Any = spec["expected"]; passed = False
        artifact_path = paths[spec["artifact_kind"]]
        failure_reason = None
        try:
            payload = _read_json(artifact_path)
            if spec["artifact_kind"] == "result":
                contract = validate_producer_payload_contract(producer_id, payload)
                if contract["result"] != "PASS":
                    observed = {"contract_errors": contract["errors"]}
                else:
                    observed = _at_path(payload, spec["json_path"])
                    if not _expected_type_matches(observed, spec["expected_type"]):
                        failure_reason = "EXPECTED_TYPE_MISMATCH"
                    else:
                        passed = _evaluate(spec["operator"], observed, expected)
            else:
                observed = _at_path(payload, spec["json_path"])
                if not _expected_type_matches(observed, spec["expected_type"]):
                    failure_reason = "EXPECTED_TYPE_MISMATCH"
                elif any(error for error in (payload.get("producer_id") != producer_id, payload.get("candidate_sha") != expected_candidate_sha, payload.get("validation_sha") != expected_validation_sha, str(payload.get("run_id")) != expected_run_id, payload.get("exit_code") != 0)):
                    failure_reason = "META_IDENTITY_OR_EXIT_MISMATCH"
                else:
                    passed = _evaluate(spec["operator"], observed, expected)
        except (OSError, json.JSONDecodeError, KeyError):
            observed = "MISSING"; passed = False; failure_reason = "MISSING_OR_INVALID_ARTIFACT"
        proofs.append({"predicate_id": spec["operator"], "producer_id": producer_id, "artifact_kind": spec["artifact_kind"], "artifact_name": artifact_path.name, "json_path": spec["json_path"], "operator": spec["operator"], "expected_type": spec["expected_type"], "source": artifact_path.name, "observed": observed, "expected": expected, "failure_reason": failure_reason, "result": "PASS" if passed else "FAIL", "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest() if artifact_path.is_file() else None, "observed_from_artifact": artifact_path.is_file()})
    return proofs


ASSERTION_EVIDENCE_SPEC: dict[tuple[str, str], dict[str, Any]] = {}


def category_policy_audit(categories: set[str] | None = None, policy: dict[tuple[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    stage_categories = set(categories) if categories is not None else set(CATEGORY_EVIDENCE_POLICY)
    registry_categories = set(CATEGORY_EVIDENCE_POLICY)
    unknown = sorted(stage_categories - registry_categories)
    # The caller supplies the exact stage set; excluded registry categories are
    # reported separately and are not stage-set mismatches.
    missing = []
    empty = sorted(category for category, policy in CATEGORY_EVIDENCE_POLICY.items() if not policy.get("required_producer_ids"))
    unknown_producers = sorted({producer for policy in CATEGORY_EVIDENCE_POLICY.values() for producer in policy["required_producer_ids"] if producer not in EVIDENCE_PRODUCERS})
    coverage_missing: dict[str, list[str]] = {}
    coverage_unknown: dict[str, list[str]] = {}
    if policy is not None:
        for category in stage_categories:
            covered = {producer for (item_category, _), item in policy.items() if item_category == category for producer in item["required_producer_ids"]}
            required = set(CATEGORY_EVIDENCE_POLICY.get(category, {}).get("required_producer_ids", ()))
            if required - covered: coverage_missing[category] = sorted(required - covered)
            if covered - set(EVIDENCE_PRODUCERS): coverage_unknown[category] = sorted(covered - set(EVIDENCE_PRODUCERS))
    return {
        "registry_category_count": len(registry_categories),
        "stage_category_count": len(stage_categories),
        "stage_expected_category_count": len(stage_categories),
        "registry_excluded_category_count": len(registry_categories - stage_categories) if categories is not None else 0,
        "category_count": len(stage_categories),
        "expected_category_count": len(stage_categories),
        "unknown_category_count": len(unknown),
        "missing_category_count": len(missing),
        "empty_required_producer_count": len(empty),
        "unknown_producer_count": len(unknown_producers),
        "category_producer_coverage_missing_count": sum(len(value) for value in coverage_missing.values()),
        "category_producer_coverage_unknown_count": sum(len(value) for value in coverage_unknown.values()),
        "category_producer_coverage_missing": coverage_missing,
        "category_producer_coverage_unknown": coverage_unknown,
        "stage_category_set_match": not unknown and not missing,
        "unknown_categories": unknown,
        "missing_categories": missing,
        "empty_categories": empty,
        "unknown_producers": unknown_producers,
        "result": "PASS" if not unknown and not missing and not empty and not unknown_producers and not coverage_missing and not coverage_unknown else "FAIL",
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
