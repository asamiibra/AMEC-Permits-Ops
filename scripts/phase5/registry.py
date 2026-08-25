from __future__ import annotations

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
    "classifier-cross-context", "classifier-path-counterfactual", "acceptance", "finalizer",
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


def category_policy_audit(categories: set[str] | None = None) -> dict[str, Any]:
    expected = categories if categories is not None else set(CATEGORY_EVIDENCE_POLICY)
    unknown = sorted(set(CATEGORY_EVIDENCE_POLICY) - expected)
    missing = sorted(expected - set(CATEGORY_EVIDENCE_POLICY))
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
