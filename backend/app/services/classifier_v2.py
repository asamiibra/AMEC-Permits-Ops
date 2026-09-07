"""Deterministic, proposal-only Phase 5 classifier over the Phase 4 seams."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from ..models import Role
from ..schemas.classifier_v2 import ClassifierV2Request, DocumentEvidenceEnvelope
from ..schemas.phase4 import ClassificationEnvelopeIn, SourceChangeEventIn
from .phase4 import (
    PHASE3C_MODULE_TRUTH_SHA,
    PHASE4_CORPUS_APP_SHA,
    create_classification_envelope,
    ingest_evidence_envelope,
    record_source_event,
)


CLASSIFIER_VERSION = "classifier-v2-rules-only-1.0.0"
RULES_VERSION = "classifier-v2-rules-1.0.0"
TAXONOMY_REVISION = "phase3c-taxonomy-v6c"
LEARNED_CLASSIFIER_MODE = "NOT_PROMOTED_DATA_INSUFFICIENT"
LLM_REAL_CONTENT_MODE = "DISABLED"
LLM_EXTERNAL_CALL_COUNT = 0
ALLOWED_L0_MODES = {
    "EXISTING_KNOWN_SOURCE", "NEW_UNKNOWN_SOURCE", "MODIFIED_KNOWN_SOURCE", "MOVE_RENAME_CANDIDATE",
}
_SAFE_EVIDENCE_PREFIX = "synthetic-evidence://"


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _stable_request_fields(payload: ClassifierV2Request) -> dict[str, Any]:
    return payload.model_dump(exclude={"correlation_id"})


def logical_replay_identity(payload: ClassifierV2Request) -> str:
    return _sha({
        "event_type": payload.source_mode,
        "source_artifact_id": payload.source_artifact_id,
        "source_version_token": payload.source_version_token,
        "evidence_identity": sorted(payload.evidence_ids),
        "classifier_version": CLASSIFIER_VERSION,
        "rules_version": RULES_VERSION,
        "taxonomy_revision": TAXONOMY_REVISION,
        "request": _stable_request_fields(payload),
    })


def stable_observed_at(payload: ClassifierV2Request) -> str:
    """Stable synthetic first-seen value; wall-clock time never enters replay identity."""
    seconds = int(logical_replay_identity(payload)[:8], 16) % (365 * 24 * 60 * 60)
    return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def _event_type(source_mode: str) -> str:
    return {"EXISTING_KNOWN_SOURCE": "NEW_VERSION", "NEW_UNKNOWN_SOURCE": "NEW_VERSION", "MODIFIED_KNOWN_SOURCE": "MODIFIED_CANDIDATE", "MOVE_RENAME_CANDIDATE": "MOVE_RENAME_CANDIDATE"}[source_mode]


def _safe_evidence_ids(ids: list[str]) -> list[str]:
    return [value for value in ids if value.startswith(_SAFE_EVIDENCE_PREFIX)]


def _l0_l1_rules(payload: ClassifierV2Request, evidence_ids: list[str], hard_gate: str) -> list[dict[str, Any]]:
    return [
        {"rule_id": "P5-L0-SOURCE-MODE", "rule_version": RULES_VERSION, "axis": "source_mode", "evidence_ids": evidence_ids, "result": "PASS", "reason": f"Accepted source mode {payload.source_mode}."},
        {"rule_id": "P5-L1-SAFE-RETENTION", "rule_version": RULES_VERSION, "axis": "retention", "evidence_ids": evidence_ids, "result": "BLOCKED" if hard_gate != "NONE" else "PASS", "reason": "Hard gate stops deeper processing." if hard_gate != "NONE" else "Metadata-only evidence is permitted."},
    ]


def evaluate_l2(payload: ClassifierV2Request, evidence_ids: list[str]) -> list[dict[str, Any]]:
    """Typed deterministic rule seam; hard-gate tests spy on this function."""
    return [
        {"rule_id": "P5-L2-TYPED-DOCUMENT", "rule_version": RULES_VERSION, "axis": "document_type", "evidence_ids": evidence_ids, "result": "PASS", "reason": "Document type remains a bounded synthetic proposal."},
        {"rule_id": "P5-L2-DISCIPLINE", "rule_version": RULES_VERSION, "axis": "discipline", "evidence_ids": evidence_ids, "result": "PASS", "reason": "Discipline is metadata-only and cannot authorize work."},
    ]


def evaluate_l5(payload: ClassifierV2Request, evidence_ids: list[str]) -> list[dict[str, Any]]:
    return [{"rule_id": "P5-L5-CROSS-AXIS-CONSISTENCY", "rule_version": RULES_VERSION, "axis": "consistency", "evidence_ids": evidence_ids, "result": "REVIEW" if payload.contradiction_families else "PASS", "reason": ", ".join(payload.contradiction_families) if payload.contradiction_families else "No material contradiction supplied."}]


def classify_document(payload: ClassifierV2Request) -> dict[str, Any]:
    """Build a deterministic ClassificationEnvelope proposal without authority."""
    if payload.source_mode not in ALLOWED_L0_MODES:
        raise ValueError("L0 source mode is not allowed")
    evidence_ids = _safe_evidence_ids(payload.evidence_ids)
    if len(evidence_ids) != len(payload.evidence_ids):
        raise ValueError("Only sanitized synthetic evidence references are accepted")

    hard_gate = "NONE"
    scope = "CORE_IN_SCOPE"
    disposition = "PROPOSED"
    reasons: list[str] = []
    if payload.secret_exclude:
        hard_gate, scope, disposition = "SECRET_EXCLUDE", "OUT_OF_SCOPE", "SECRET_EXCLUDE"
        reasons.append("Secret-like evidence is excluded before deeper classification.")
    elif payload.out_of_scope:
        hard_gate, scope, disposition = "OUT_OF_SCOPE", "OUT_OF_SCOPE", "OUT_OF_SCOPE"
        reasons.append("The source was explicitly marked outside the locked Phase5 scope.")
    elif payload.contradiction_families:
        scope, disposition = "AMBIGUOUS_REVIEW", "NEEDS_REVIEW"
        reasons.append("Material cross-axis contradiction requires a human review decision.")
    elif payload.missing_candidate:
        scope, disposition = "ADJACENT_RECOGNIZED", "MISSING_CANDIDATE"
        reasons.append("No current candidate was fabricated; the missing-candidate issue remains reviewable.")
    elif payload.source_mode == "MOVE_RENAME_CANDIDATE":
        scope, disposition = "ADJACENT_RECOGNIZED", "RELATIONSHIP_REVIEW"
        reasons.append("Move/rename identity requires explicit relationship resolution.")
    else:
        reasons.append("Deterministic rules produced a bounded proposal; a human review decision remains required.")

    document_type = payload.document_type_hint or "CONTROLLED_SYNTHETIC_DOCUMENT"
    discipline = payload.discipline_hint or "ENGINEERING"
    relationship = None
    if payload.source_mode == "MOVE_RENAME_CANDIDATE" and payload.candidate_entity_id:
        relationship = {"source_entity_id": payload.source_artifact_id, "candidate_entity_id": payload.candidate_entity_id, "relationship_type": "SOURCE_RENAME_CANDIDATE", "resolution": "PENDING_HUMAN_REVIEW"}

    # Do not construct deeper rule objects for hard-gated inputs.
    if hard_gate != "NONE":
        return _proposal(payload, evidence_ids, scope, disposition, hard_gate, reasons, _l0_l1_rules(payload, evidence_ids, hard_gate), document_type, discipline, relationship, ["L0", "L1"], 0, 0, 0, 0)

    l2 = evaluate_l2(payload, evidence_ids)
    l5 = evaluate_l5(payload, evidence_ids)
    return _proposal(payload, evidence_ids, scope, disposition, hard_gate, reasons, _l0_l1_rules(payload, evidence_ids, hard_gate) + l2 + l5, document_type, discipline, relationship, ["L0", "L1", "L2", "L3", "L4", "L5"], len(l2), 0, 0, 1)


def _proposal(payload: ClassifierV2Request, evidence_ids: list[str], scope: str, disposition: str, hard_gate: str, reasons: list[str], rule_evaluations: list[dict[str, Any]], document_type: str, discipline: str, relationship: dict[str, Any] | None, executed_layers: list[str], deeper_count: int, learned_count: int, semantic_count: int, l5_count: int) -> dict[str, Any]:
    secret = hard_gate == "SECRET_EXCLUDE"
    return {
        "classifier_version": CLASSIFIER_VERSION, "rules_version": RULES_VERSION, "taxonomy_revision": TAXONOMY_REVISION,
        "source_mode": payload.source_mode, "l0_prior_state": payload.source_mode,
        "scope": {"value": scope, "scope_type": payload.scope_type, "scope_id": payload.scope_id},
        "classification_proposal": {"document_type": document_type, "discipline": discipline, "disposition": disposition, "currentness": "CANDIDATE_ONLY"},
        "hard_gate": {"state": hard_gate, "deeper_processing": hard_gate == "NONE", "llm_allowed": False, "projection_allowed": False},
        "bounded_evidence": [{"evidence_id": value, "content_state": "REFERENCE_ONLY"} for value in evidence_ids], "rule_evaluations": rule_evaluations,
        "executed_layers": executed_layers, "deeper_rule_evaluation_count": deeper_count, "learned_lane_call_count": learned_count, "semantic_resolver_call_count": semantic_count, "l5_call_count": l5_count,
        "contradictions": list(payload.contradiction_families), "review_reason": " ".join(reasons), "review_required": True, "auto_promotion_allowed": False, "projection_allowed": False,
        "learned_lane": {"mode": LEARNED_CLASSIFIER_MODE, "promoted": False}, "semantic_lane": {"mode": "DISABLED_SYNTHETIC_INTERFACE_ONLY", "real_content": False}, "llm": {"real_content_mode": LLM_REAL_CONTENT_MODE, "external_call_count": LLM_EXTERNAL_CALL_COUNT},
        "comparisons": {"prior_state": payload.source_mode, "candidate_state": "PROPOSAL_ONLY", "current_assertion_mutation": False}, "relationship_resolution": relationship,
        "preview_count": 0 if secret or hard_gate != "NONE" else 1, "broad_index_count": 0, "training_count": 0, "projection_count": 0, "root_event_id": None, "correlation_id": payload.correlation_id,
    }


def classify_and_persist(db: Session, payload: ClassifierV2Request, role: Role | str) -> dict[str, Any]:
    proposal = classify_document(payload)
    replay_id = logical_replay_identity(payload)
    event_id = f"phase5-event-{replay_id[:40]}"
    source = SourceChangeEventIn(event_id=event_id, scan_id_or_observation_group=f"phase5-observation-{_sha(payload.fixture_id)[:24]}", source_surface="CONTROLLED_SYNTHETIC_FIXTURE", source_artifact_id_or_locator=payload.source_artifact_id, source_version_token=payload.source_version_token, event_type=_event_type(payload.source_mode), origin="CONTROLLED_SYNTHETIC", correlation_id=payload.correlation_id, observed_at=stable_observed_at(payload), content_identity_proof={"synthetic_fixture_id": payload.fixture_id, "logical_replay_identity": replay_id, "metadata_sha256": _sha(_stable_request_fields(payload))})
    event = record_source_event(db, source, role)
    proposal["root_event_id"] = event.id
    evidence_payload = DocumentEvidenceEnvelope(root_event_id=event.id, source_artifact_id=payload.source_artifact_id, source_version_token=payload.source_version_token, source_surface="CONTROLLED_SYNTHETIC_FIXTURE", evidence_envelope_sha256=_sha({"event": event.id, "evidence_ids": sorted(payload.evidence_ids), "proposal": proposal}), runtime_sha256=_sha({"runtime": "phase5-deterministic-parser-v1"}), capability_id="PHASE5_METADATA_CLASSIFICATION", handler_parser_identity="phase5-synthetic-metadata-parser-v1", metering_json={"external_calls": 0, "bytes_read": 0}, warnings_json=["SYNTHETIC_METADATA_ONLY"], content_retention_class="METADATA_ONLY", unsupported_capability_state=proposal["hard_gate"]["state"] if proposal["hard_gate"]["state"] != "NONE" else None, evidence_json={"evidence_ids": sorted(payload.evidence_ids), "source_mode": payload.source_mode, "logical_replay_identity": replay_id})
    evidence = ingest_evidence_envelope(db, evidence_payload, role)
    classification_payload = ClassificationEnvelopeIn(envelope_id=f"phase5-envelope-{replay_id[:40]}", root_event_id=event.id, source_mode="CONTROLLED_SYNTHETIC", classifier_version=CLASSIFIER_VERSION, rules_version=RULES_VERSION, taxonomy_revision=TAXONOMY_REVISION, module_truth_contract_sha=PHASE3C_MODULE_TRUTH_SHA, corpus_app_contract_sha=PHASE4_CORPUS_APP_SHA, axes_json=proposal)
    envelope = create_classification_envelope(db, classification_payload, role)
    return {"classification": proposal, "source_event": {"id": event.id, "event_id": event.event_id, "root_event_id": event.id, "immutable_payload_hash": event.immutable_payload_hash}, "evidence_envelope": {"id": evidence.id, "evidence_envelope_sha256": evidence.evidence_envelope_sha256}, "classification_envelope": {"id": envelope.id, "envelope_id": envelope.envelope_id, "status": envelope.status, "record_version": envelope.record_version, "immutable_result_hash": envelope.immutable_result_hash}, "shadow_state": "REVIEW_COMPARE_ONLY", "logical_replay_identity": replay_id, "correlation_id": payload.correlation_id}
