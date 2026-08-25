from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from registry import PHASE5_ARTIFACTS, PHASE5_CONTRACTS, ROOT, canonical_path
except ModuleNotFoundError:
    from .registry import PHASE5_ARTIFACTS, PHASE5_CONTRACTS, ROOT, canonical_path


INPUT_IDENTITIES = {
    "phase4_accepted_sha": "707003fc16767fb28b9c968fbcf168ab03ebadc1",
    "phase4_accepted_tree": "af473134f6a92b9dc9919eae71f1e02a3ed81e1e",
    "phase4_acceptance_validation_sha": "d56817d27a9aaaf69aa08b5e314f78297ed45376",
    "phase4_acceptance_run_id": "32778775085",
    "phase4_acceptance_artifact_sha256": "877f1e39c4bb0e16187dcf4de76ba47cff7df3bdf7cb01a2ae6027da1df4f4a6",
    "phase3c_accepted_sha": "44968e3d43571ceb1df8493da683ff9e51a146d9",
    "module_truth_contract_sha256": "d18ebed191b8f2633d5984ff57ab25803fe19beeb9c73999946abffddb974f2c",
    "phase4_corpus_app_contract_sha256": "387a741b2531afb54398fadbe8aac0d73e2a1ba9aab619e48d5dd5b5d7289908",
    "active_alembic_revision": "baseline_phase4_v36_azure_sql",
    "database_engine_target": "AZURE_SQL_SQL_SERVER_ENGINE",
    "phase5_master_design_sha256": "761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b",
    "phase5_design_validation_sha256": "61e57216ca5b8671df7337420bb7d116c94be138da62cde851dcab6236ecbe0f",
    "step3a4c_accepted": False,
    "phase5_step3a4c_entry_gate_superseded": True,
    "phase3c_classifier_handoff_sha256": "0031c5d49cc9a7cc5a3be7ee26bf69a92d977d70968ead4a5f0bee1e487659b7",
    "phase4_freeze_manifest_sha256": "e904b564680581e114228bf988cdfcf1da3a2852ad34c94e652a388f5d303724",
    "phase4_azure_sql_port_contract_sha256": "ef87b18fd644429cbfb6581e2121ca1f4f6c6bb8408870d9b0ddc9002021c2fd",
    "azure_sql_owner_addendum_sha256": "05335b4b535d88155306783e20b94f16e49e3a2b88049d0fa4e270a7e3efbe90",
}
CLASSIFIER_VERSION = "classifier-v2-rules-only-1.0.0"
RULES_VERSION = "classifier-v2-rules-1.0.0"
TAXONOMY_REVISION = "phase3c-taxonomy-v6c"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def synthetic_evidence(case_id: str, index: int) -> str:
    return f"synthetic-evidence://phase5/{case_id}/{index:02d}"


def corpus_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "P5-GOLD-NEW-001", "source_mode": "NEW_UNKNOWN_SOURCE", "expected": "PROPOSED"},
        {"case_id": "P5-GOLD-AMBIG-001", "source_mode": "EXISTING_KNOWN_SOURCE", "contradiction_families": ["DISCIPLINE_CONFLICT"], "expected": "NEEDS_REVIEW"},
        {"case_id": "P5-GOLD-OOS-001", "source_mode": "NEW_UNKNOWN_SOURCE", "out_of_scope": True, "expected": "OUT_OF_SCOPE"},
        {"case_id": "P5-GOLD-SECRET-001", "source_mode": "NEW_UNKNOWN_SOURCE", "secret_exclude": True, "expected": "SECRET_EXCLUDE"},
        {"case_id": "P5-VAL-MODIFIED-001", "source_mode": "MODIFIED_KNOWN_SOURCE", "expected": "PROPOSED"},
        {"case_id": "P5-VAL-MOVE-001", "source_mode": "MOVE_RENAME_CANDIDATE", "candidate_entity_id": "synthetic-project-001", "expected": "RELATIONSHIP_REVIEW"},
        {"case_id": "P5-VAL-MISSING-001", "source_mode": "EXISTING_KNOWN_SOURCE", "missing_candidate": True, "expected": "MISSING_CANDIDATE"},
        {"case_id": "P5-VAL-FINANCE-001", "source_mode": "EXISTING_KNOWN_SOURCE", "document_type_hint": "FINANCE", "expected": "PROPOSED"},
        {"case_id": "P5-HOLDOUT-UNTOUCHED-001", "source_mode": "EXISTING_KNOWN_SOURCE", "document_type_hint": "MASTER_CONTENT", "expected": "PROPOSED"},
        {"case_id": "P5-HOLDOUT-UNTOUCHED-002", "source_mode": "MODIFIED_KNOWN_SOURCE", "contradiction_families": ["CURRENTNESS_CONFLICT"], "expected": "NEEDS_REVIEW"},
        {"case_id": "P5-ADV-CONFLICT-001", "source_mode": "MODIFIED_KNOWN_SOURCE", "contradiction_families": ["CURRENTNESS_CONFLICT", "RELATIONSHIP_CONFLICT"], "expected": "NEEDS_REVIEW"},
        {"case_id": "P5-ADV-SECRET-001", "source_mode": "MOVE_RENAME_CANDIDATE", "secret_exclude": True, "expected": "SECRET_EXCLUDE"},
    ]
