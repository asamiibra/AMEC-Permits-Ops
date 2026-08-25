from __future__ import annotations

from pathlib import Path


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

EVIDENCE_PRODUCERS = {
    producer: {"raw": f"{producer}.raw.log", "meta": f"{producer}.meta.json"}
    for producer in (
        "entry-identity", "input-identity", "source-preflight", "freeze-reproducibility",
        "classifier-calibration", "classifier-validation", "classifier-holdout",
        "classifier-cross-context", "classifier-path-counterfactual", "shadow-replay",
        "sqlserver-bootstrap", "sqlserver-targeted", "browser-required-paths", "browser-quality",
        "backend-targeted", "phase4-integration-regression", "backend-full", "frontend-targeted",
        "frontend-full", "frontend-build", "authority-denial", "observability", "security-hygiene",
        "acceptance", "finalizer",
    )
}


def canonical_path(key: str, root: Path | None = None) -> Path:
    return (root or PHASE5_CONTRACTS) / CANONICAL_ARTIFACTS[key]


def canonical_names() -> set[str]:
    return set(CANONICAL_ARTIFACTS.values())


def evidence_reference(producer_id: str) -> str:
    if producer_id not in EVIDENCE_PRODUCERS:
        raise KeyError(producer_id)
    return f"scripts/phase5/{producer_id.replace('-', '_')}.py"
