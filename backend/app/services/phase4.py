"""Deterministic, review-gated Phase 4 corpus integration service."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AssertionStatus,
    AuditEvent,
    Finding,
    FindingStatus,
    NotificationEvent,
    NotificationStatus,
    PermitApplication,
    Phase4ClassifierCorrectionEvent,
    Phase4ClassificationEnvelope,
    Phase4DocumentEvidenceEnvelope,
    Phase4ProjectionPlan,
    Phase4ProjectionReceipt,
    Phase4ReviewDecision,
    Phase4SourceChangeEvent,
    Phase4VerifiedAssertionBridge,
    Role,
    VerifiedAssertion,
    WorkflowTask,
    WorkflowTaskStatus,
)
from ..models.base import utcnow
from ..schemas.phase4 import (
    ClassificationEnvelopeIn,
    EvidenceEnvelopeIn,
    ProjectionRequest,
    PromotionIn,
    ReviewDecisionIn,
    SourceChangeEventIn,
)
from .backend_realignment import require_capability


PHASE3C_MODULE_TRUTH_SHA = "d18ebed191b8f2633d5984ff57ab25803fe19beeb9c73999946abffddb974f2c"
PHASE4_CORPUS_APP_SHA = "387a741b2531afb54398fadbe8aac0d73e2a1ba9aab619e48d5dd5b5d7289908"
PHASE4_CONTRACT_VERSION = "AMEC_CORPUS_APP_INTEGRATION_CONTRACT_V1"
ALLOWED_SOURCE_SURFACES = {"APP_UPLOAD", "SYNOLOGY_EXTERNAL_EVIDENCE", "CONTROLLED_SYNTHETIC_FIXTURE", "IMPORTED_EVIDENCE_ENVELOPE", "ACCEPTED_PHASE3C_PACKAGE"}
ALLOWED_EVENT_TYPES = {"NEW", "MODIFIED_CANDIDATE", "MISSING_CANDIDATE", "MOVE_RENAME_CANDIDATE", "UNCHANGED", "NEW_VERSION", "CONTENT_CHANGED", "METADATA_CHANGED", "SUPERSEDED", "NO_MATERIAL_CHANGE"}
ALLOWED_DECISIONS = {"ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP", "REJECT"}
PROTECTED_OPERATIONS = {"SEND", "SUBMIT", "APPROVE", "ACTIVATE", "CLOSE_CONTRACT", "WRITEBACK", "MUTATE_EXTERNAL"}
REVIEW_SCOPE_TYPES = {"PROJECT", "ENTITY", "AMEC"}
RELATIONSHIP_FIELDS = ("source_entity_id", "candidate_entity_id", "relationship_type", "resolution")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _error(status: int, code: str, **details: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, **details})


def _role_value(role: Role | str) -> str:
    return role.value if isinstance(role, Role) else str(role)


def _idempotency_lock(db: Session, key: str) -> None:
    """Serialize retries on PostgreSQL without holding an application lock."""
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        lock_key = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:15], 16)
        db.execute(text("select pg_advisory_xact_lock(:phase4_lock_key)"), {"phase4_lock_key": lock_key})


def _require_phase4(role: Role | str, capability: str) -> str:
    try:
        return require_capability(role, capability)
    except HTTPException:
        raise


def _review_capability(decision: str) -> str:
    return "PHASE4_RESOLVE_RELATIONSHIP" if decision == "RESOLVE_RELATIONSHIP" else "PHASE4_REVIEW_DECISION"


def _server_principal(role: Role | str) -> str:
    """Return the explicitly local, non-production principal for the role context."""
    return f"local-phase4-role:{_role_value(role)}"


def _bound_scope(envelope: Phase4ClassificationEnvelope) -> tuple[str, str] | None:
    """Read the declared scope from server-held envelope data, without defaults."""
    axes = envelope.axes_json if isinstance(envelope.axes_json, dict) else {}
    declared = axes.get("scope") if isinstance(axes.get("scope"), dict) else axes
    expected_type = declared.get("scope_type")
    expected_id = declared.get("scope_id")
    if not isinstance(expected_type, str) or not expected_type.strip():
        return None
    if not isinstance(expected_id, str) or not expected_id.strip():
        return None
    return expected_type.strip(), expected_id.strip()


def _scope_matches(envelope: Phase4ClassificationEnvelope, payload: ReviewDecisionIn) -> bool:
    bound = _bound_scope(envelope)
    return bound == (payload.scope_type, payload.scope_id)


def _bound_relationship(envelope: Phase4ClassificationEnvelope) -> dict[str, Any] | None:
    axes = envelope.axes_json if isinstance(envelope.axes_json, dict) else {}
    candidate = axes.get("relationship_resolution")
    if not isinstance(candidate, dict) or not candidate:
        return None
    if any(not isinstance(candidate.get(field), str) or not candidate[field].strip() for field in RELATIONSHIP_FIELDS):
        return None
    return candidate


def _relationship_payload_is_bound(envelope: Phase4ClassificationEnvelope, payload: ReviewDecisionIn) -> bool:
    """Require the client to echo the exact server-held relationship candidate."""
    candidate = _bound_relationship(envelope)
    return len(payload.corrections_json) == 1 and candidate is not None and _json(payload.corrections_json[0]) == _json(candidate)


def _classification_axes(envelope: Phase4ClassificationEnvelope) -> dict[str, Any]:
    axes = envelope.axes_json if isinstance(envelope.axes_json, dict) else {}
    proposal = axes.get("classification_proposal") or axes.get("classification_axes")
    if isinstance(proposal, dict):
        return proposal
    excluded = {"scope", "relationship_resolution", "bounded_evidence", "evidence", "evidence_refs", "candidate_links", "deep_links", "work_issue_notification_links", "contradictions", "conflicts"}
    return {key: value for key, value in axes.items() if key not in excluded}


def _validate_corrections(envelope: Phase4ClassificationEnvelope, payload: ReviewDecisionIn) -> None:
    if not payload.corrections_json:
        raise _error(422, "CORRECTION_REQUIRED")
    available = _classification_axes(envelope)
    for correction in payload.corrections_json:
        required = {"axis", "old_value", "new_value", "reason", "evidence_ids"}
        if set(correction) < required:
            raise _error(422, "CORRECTION_PAYLOAD_INVALID", required=sorted(required))
        axis = correction["axis"]
        if not isinstance(axis, str) or axis not in available:
            raise _error(422, "CORRECTION_AXIS_NOT_BOUND", axis=axis)
        if _json(correction["old_value"]) != _json(available[axis]):
            raise _error(409, "CORRECTION_OLD_VALUE_MISMATCH", axis=axis)
        if _json(correction["new_value"]) == _json(correction["old_value"]):
            raise _error(422, "CORRECTION_NEW_VALUE_UNCHANGED", axis=axis)
        if not isinstance(correction["reason"], str) or not correction["reason"].strip():
            raise _error(422, "CORRECTION_REASON_REQUIRED", axis=axis)
        if not isinstance(correction["evidence_ids"], list):
            raise _error(422, "CORRECTION_EVIDENCE_IDS_REQUIRED", axis=axis)


def _lock_review_envelope(db: Session, envelope_id: str) -> Phase4ClassificationEnvelope | None:
    statement = select(Phase4ClassificationEnvelope).where(Phase4ClassificationEnvelope.id == envelope_id).with_for_update()
    return db.scalar(statement)


def _as_dict(item: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        result[column.name] = value
    return result


def record_source_event(db: Session, payload: SourceChangeEventIn, role: Role | str) -> Phase4SourceChangeEvent:
    _require_phase4(role, "PHASE4_SOURCE_REVIEW")
    if payload.source_surface not in ALLOWED_SOURCE_SURFACES:
        raise _error(422, "SOURCE_SURFACE_NOT_ALLOWED", source_surface=payload.source_surface)
    if payload.event_type not in ALLOWED_EVENT_TYPES:
        raise _error(422, "SOURCE_EVENT_TYPE_NOT_ALLOWED", event_type=payload.event_type)
    _idempotency_lock(db, f"source:{payload.event_id}")
    existing = db.scalar(select(Phase4SourceChangeEvent).where(Phase4SourceChangeEvent.event_id == payload.event_id))
    if existing:
        return existing
    content = payload.model_dump()
    item = Phase4SourceChangeEvent(**content, immutable_payload_hash=_sha(content), record_version=1)
    db.add(item)
    db.flush()
    audit(db, correlation_id=payload.correlation_id, event_type="PHASE4_SOURCE_CHANGE_RECORDED", entity_type="Phase4SourceChangeEvent", entity_id=item.id, actor_id=_role_value(role), after={"event_id": payload.event_id, "source_surface": payload.source_surface})
    return item


def ingest_evidence_envelope(db: Session, payload: EvidenceEnvelopeIn, role: Role | str) -> Phase4DocumentEvidenceEnvelope:
    _require_phase4(role, "PHASE4_SOURCE_REVIEW")
    if payload.source_surface not in ALLOWED_SOURCE_SURFACES:
        raise _error(422, "SOURCE_SURFACE_NOT_ALLOWED", source_surface=payload.source_surface)
    event = db.get(Phase4SourceChangeEvent, payload.root_event_id)
    if event is None:
        raise _error(404, "ROOT_SOURCE_EVENT_NOT_FOUND", root_event_id=payload.root_event_id)
    if event.source_version_token != payload.source_version_token:
        raise _error(409, "SOURCE_VERSION_MISMATCH", expected=event.source_version_token, received=payload.source_version_token)
    _idempotency_lock(db, f"evidence:{payload.evidence_envelope_sha256}")
    existing = db.scalar(select(Phase4DocumentEvidenceEnvelope).where(Phase4DocumentEvidenceEnvelope.evidence_envelope_sha256 == payload.evidence_envelope_sha256))
    if existing:
        return existing
    item = Phase4DocumentEvidenceEnvelope(**payload.model_dump())
    db.add(item)
    db.flush()
    return item


def create_classification_envelope(db: Session, payload: ClassificationEnvelopeIn, role: Role | str) -> Phase4ClassificationEnvelope:
    _require_phase4(role, "PHASE4_SOURCE_REVIEW")
    if payload.source_mode not in {"APP_UPLOAD", "SYNOLOGY_EXTERNAL_EVIDENCE", "RULES_ONLY", "IMPORTED_CLASSIFIER_RESULT", "CONTROLLED_SYNTHETIC"}:
        raise _error(422, "CLASSIFIER_SOURCE_MODE_NOT_ALLOWED", source_mode=payload.source_mode)
    if payload.classifier_version.lower().startswith(("llm", "live-model", "production-model")):
        raise _error(422, "LIVE_CLASSIFIER_NOT_AUTHORIZED")
    event = db.get(Phase4SourceChangeEvent, payload.root_event_id)
    if event is None:
        raise _error(404, "ROOT_SOURCE_EVENT_NOT_FOUND", root_event_id=payload.root_event_id)
    if payload.module_truth_contract_sha != PHASE3C_MODULE_TRUTH_SHA or payload.corpus_app_contract_sha != PHASE4_CORPUS_APP_SHA:
        raise _error(409, "CONTRACT_IDENTITY_MISMATCH")
    _idempotency_lock(db, f"classification:{payload.envelope_id}")
    existing = db.scalar(select(Phase4ClassificationEnvelope).where(Phase4ClassificationEnvelope.envelope_id == payload.envelope_id))
    if existing:
        return existing
    axes = payload.axes_json
    item = Phase4ClassificationEnvelope(**payload.model_dump(), immutable_result_hash=_sha(axes), status="PENDING_REVIEW", record_version=1)
    db.add(item)
    db.flush()
    return item


def review_queue(db: Session, role: Role | str, scope_type: str | None = None, scope_id: str | None = None) -> list[dict[str, Any]]:
    _require_phase4(role, "PHASE4_REVIEW_QUEUE")
    if not scope_type or not scope_id:
        raise _error(422, "REVIEW_SCOPE_REQUIRED")
    if scope_type not in REVIEW_SCOPE_TYPES:
        raise _error(422, "REVIEW_SCOPE_TYPE_NOT_ALLOWED", scope_type=scope_type)
    query = select(Phase4ClassificationEnvelope).where(Phase4ClassificationEnvelope.status.in_(("PENDING_REVIEW", "CORRECTED", "DEFERRED"))).order_by(Phase4ClassificationEnvelope.created_at)
    requested_scope = (scope_type, scope_id)
    return [_as_dict(item) for item in db.scalars(query).all() if _bound_scope(item) == requested_scope]


def record_review_decision(db: Session, payload: ReviewDecisionIn, role: Role | str) -> Phase4ReviewDecision:
    _require_phase4(role, _review_capability(payload.decision))
    if payload.decision not in ALLOWED_DECISIONS:
        raise _error(422, "REVIEW_DECISION_NOT_ALLOWED", decision=payload.decision)
    expected_capability = "PHASE4_RESOLVE_RELATIONSHIP" if payload.decision == "RESOLVE_RELATIONSHIP" else "PHASE4_REVIEW_DECISION"
    if payload.capability != expected_capability:
        raise _error(403, "CAPABILITY_PROVENANCE_MISMATCH")
    if not payload.scope_type or not payload.scope_id:
        raise _error(422, "REVIEW_SCOPE_REQUIRED")
    if payload.scope_type not in REVIEW_SCOPE_TYPES:
        raise _error(422, "REVIEW_SCOPE_TYPE_NOT_ALLOWED", scope_type=payload.scope_type)
    server_actor = _server_principal(role)
    canonical_payload = payload.model_dump()
    canonical_payload["actor_id"] = server_actor
    canonical_hash = _sha(canonical_payload)
    _idempotency_lock(db, f"decision:{payload.idempotency_key}")
    existing = db.scalar(select(Phase4ReviewDecision).where(Phase4ReviewDecision.idempotency_key == payload.idempotency_key))
    if existing:
        if existing.immutable_hash != canonical_hash:
            raise _error(409, "IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return existing
    envelope = _lock_review_envelope(db, payload.classification_envelope_id)
    if envelope is None:
        raise _error(404, "CLASSIFICATION_ENVELOPE_NOT_FOUND")
    if _bound_scope(envelope) is None:
        raise _error(409, "REVIEW_SCOPE_NOT_BOUND")
    if not _scope_matches(envelope, payload):
        raise _error(403, "REVIEW_SCOPE_MISMATCH", scope_type=payload.scope_type, scope_id=payload.scope_id)
    if envelope.record_version != payload.record_version:
        raise _error(409, "CLASSIFICATION_RECORD_VERSION_CONFLICT", expected=envelope.record_version, received=payload.record_version)
    if payload.decision == "RESOLVE_RELATIONSHIP":
        if _bound_relationship(envelope) is None:
            raise _error(409, "RELATIONSHIP_SERVER_CANDIDATE_NOT_BOUND")
        if not _relationship_payload_is_bound(envelope, payload):
            raise _error(403, "RELATIONSHIP_RESOLUTION_CANDIDATE_MISMATCH")
    if payload.decision == "CORRECT":
        _validate_corrections(envelope, payload)
    item = Phase4ReviewDecision(**canonical_payload, immutable_hash=canonical_hash)
    db.add(item)
    if payload.decision == "CORRECT":
        for correction in payload.corrections_json:
            event = Phase4ClassifierCorrectionEvent(
                source_version=str(envelope.document_version_id or envelope.root_event_id),
                classification_envelope_id=envelope.id,
                axis=str(correction.get("axis", "UNSPECIFIED")),
                old_value_json=correction.get("old_value"),
                new_value_json=correction.get("new_value"),
                reason=str(correction.get("reason", "Human correction")),
                reviewer=server_actor,
                evidence_ids_json=list(correction.get("evidence_ids", [])),
                classifier_version=envelope.classifier_version,
                rules_version=envelope.rules_version,
                taxonomy_revision=envelope.taxonomy_revision,
                module_truth_contract_sha=envelope.module_truth_contract_sha,
                immutable_hash=_sha(correction),
            )
            db.add(event)
        envelope.status = "CORRECTED"
    elif payload.decision == "ACCEPT":
        envelope.status = "ACCEPTED_FOR_ASSERTION_REVIEW"
    elif payload.decision == "DEFER":
        envelope.status = "DEFERRED"
    elif payload.decision == "MARK_OUT_OF_SCOPE":
        envelope.status = "OUT_OF_SCOPE"
    elif payload.decision == "RESOLVE_RELATIONSHIP":
        envelope.status = "RELATIONSHIP_RESOLVED"
    elif payload.decision == "REJECT":
        envelope.status = "REJECTED"
    envelope.record_version += 1
    db.flush()
    audit(
        db,
        correlation_id=f"phase4-review:{payload.idempotency_key}",
        event_type=f"PHASE4_REVIEW_DECISION_{payload.decision}",
        entity_type="Phase4ClassificationEnvelope",
        entity_id=envelope.id,
        actor_id=server_actor,
        after={
            "review_decision_id": item.id,
            "decision": payload.decision,
            "scope_type": payload.scope_type,
            "scope_id": payload.scope_id,
            "record_version": payload.record_version,
            "next_record_version": envelope.record_version,
        },
    )
    db.flush()
    return item


def promote_verified_assertion(db: Session, payload: PromotionIn, role: Role | str) -> Phase4VerifiedAssertionBridge:
    _require_phase4(role, "PHASE4_PROMOTE_VERIFIED_ASSERTION")
    decision = db.get(Phase4ReviewDecision, payload.review_decision_id)
    assertion = db.get(VerifiedAssertion, payload.verified_assertion_id)
    if decision is None or assertion is None:
        raise _error(404, "PROMOTION_LINEAGE_NOT_FOUND")
    if decision.decision not in {"ACCEPT", "CORRECT"}:
        raise _error(409, "REVIEW_DECISION_NOT_PROMOTABLE", decision=decision.decision)
    if decision.decision == "CORRECT":
        correction = db.scalar(select(Phase4ClassifierCorrectionEvent).where(Phase4ClassifierCorrectionEvent.classification_envelope_id == decision.classification_envelope_id))
        if correction is None:
            raise _error(409, "CORRECTION_REQUIRED_FOR_PROMOTION")
    envelope = db.get(Phase4ClassificationEnvelope, decision.classification_envelope_id)
    if envelope is None:
        raise _error(404, "CLASSIFICATION_ENVELOPE_NOT_FOUND")
    _idempotency_lock(db, f"promotion:{payload.idempotency_key}")
    existing = db.scalar(select(Phase4VerifiedAssertionBridge).where(Phase4VerifiedAssertionBridge.idempotency_key == payload.idempotency_key))
    if existing:
        return existing
    item = Phase4VerifiedAssertionBridge(
        bridge_id=str(uuid4()),
        classification_envelope_id=envelope.id,
        review_decision_id=decision.id,
        verified_assertion_id=assertion.id,
        strategy="EXISTING_VERIFIED_ASSERTION_ONLY",
        lineage_json={"module_truth_contract_sha": envelope.module_truth_contract_sha, "evidence_envelope_id": envelope.root_event_id, "source_status": assertion.status.value if hasattr(assertion.status, "value") else str(assertion.status)},
        idempotency_key=payload.idempotency_key,
    )
    db.add(item)
    db.flush()
    return item


def plan_projection(db: Session, payload: ProjectionRequest, role: Role | str) -> Phase4ProjectionPlan:
    _require_phase4(role, "PHASE4_TYPED_PROJECTION")
    if payload.operation.upper() in PROTECTED_OPERATIONS:
        raise _error(403, "PROTECTED_OPERATION_REQUIRES_HUMAN_AUTHORITY", operation=payload.operation)
    assertion = db.get(VerifiedAssertion, payload.verified_assertion_id)
    if assertion is None:
        raise _error(404, "VERIFIED_ASSERTION_NOT_FOUND")
    if assertion.status != AssertionStatus.CURRENT:
        raise _error(409, "VERIFIED_ASSERTION_NOT_CURRENT")
    _idempotency_lock(db, f"plan:{payload.idempotency_key}")
    existing = db.scalar(select(Phase4ProjectionPlan).where(Phase4ProjectionPlan.idempotency_key == payload.idempotency_key))
    if existing:
        return existing
    item = Phase4ProjectionPlan(
        verified_assertion_id=payload.verified_assertion_id,
        target_domain=payload.target_domain,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
        precondition_version=payload.precondition_version,
        plan_json={**payload.plan_json, "operation": payload.operation},
        idempotency_key=payload.idempotency_key,
        result="PLANNED",
    )
    db.add(item)
    db.flush()
    return item


def execute_projection(db: Session, payload: ProjectionRequest, role: Role | str) -> Phase4ProjectionReceipt:
    _require_phase4(role, "PHASE4_TYPED_PROJECTION")
    if payload.operation.upper() in PROTECTED_OPERATIONS:
        raise _error(403, "PROTECTED_OPERATION_REQUIRES_HUMAN_AUTHORITY", operation=payload.operation)
    _idempotency_lock(db, f"projection:{payload.idempotency_key}")
    existing = db.scalar(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.idempotency_key == payload.idempotency_key))
    if existing:
        return existing
    plan = db.scalar(select(Phase4ProjectionPlan).where(Phase4ProjectionPlan.idempotency_key == payload.idempotency_key))
    if plan is None:
        plan = plan_projection(db, payload, role)
    assertion = db.get(VerifiedAssertion, payload.verified_assertion_id)
    if assertion is None or assertion.status != AssertionStatus.CURRENT:
        raise _error(409, "VERIFIED_ASSERTION_NOT_CURRENT")
    work_ids: list[str] = []
    issue_ids: list[str] = []
    notification_ids: list[str] = []
    audit_ids: list[str] = []
    correlation_id = payload.correlation_id
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == assertion.project_id).order_by(PermitApplication.created_at))
    issue = None
    if application is not None:
        issue = Finding(
            project_id=assertion.project_id,
            application_id=application.id,
            source_type="INTERNAL_PREFLIGHT",
            source_reference=f"phase4:{payload.projection_id}",
            source_timestamp=utcnow(),
            captured_by=_role_value(role),
            title="Review typed corpus projection",
            raw_text="A synthetic corpus-derived projection requires human review before any protected action.",
            normalized_summary="Phase4 projection review required",
            language="en",
            discipline="ENGINEERING",
            severity="ADVISORY",
            blocking=False,
            status=FindingStatus.OPEN,
            correlation_id=correlation_id,
            domain="PHASE4_CORPUS",
            owner_persona="ENGINEERING",
            deep_link=f"/phase4/projections/{payload.projection_id}",
        )
        db.add(issue)
        db.flush()
        issue_ids.append(issue.id)
    work = WorkflowTask(
        task_type="PHASE4_TYPED_PROJECTION_REVIEW",
        title=f"Review corpus projection for {payload.target_entity_type}",
        description="Review a typed projection produced from an existing VerifiedAssertion.",
        project_id=assertion.project_id,
        application_id=application.id if application is not None else None,
        finding_id=issue.id if issue is not None else None,
        owner_role="RESPONSIBLE_ENGINEER",
        status=WorkflowTaskStatus.OPEN,
        priority="NORMAL",
        correlation_id=correlation_id,
        task_family="PHASE4_CORPUS",
        context_type="PHASE4_PROJECTION",
        context_id=payload.target_entity_id if len(payload.target_entity_id) <= 36 else hashlib.sha256(payload.target_entity_id.encode("utf-8")).hexdigest()[:36],
        blocking=False,
        next_action_code="REVIEW_PHASE4_PROJECTION",
        deep_link=f"/phase4/projections/{payload.projection_id}",
        evidence_summary={"verified_assertion_id": assertion.id, "precondition_version": payload.precondition_version},
    )
    db.add(work)
    db.flush()
    work_ids.append(work.id)
    notification = NotificationEvent(
        finding_id=issue.id if issue is not None else None,
        workflow_task_id=work.id,
        recipient_role="RESPONSIBLE_ENGINEER",
        channel="IN_APP",
        event_type="PHASE4_PROJECTION_REVIEW_REQUIRED",
        status=NotificationStatus.PENDING,
        subject="Corpus projection review required",
        body_preview="A typed projection is ready for human review; no protected action was performed.",
        correlation_id=correlation_id,
        domain="PHASE4_CORPUS",
        audience=["ENGINEERING", "OWNER"],
        actor=_role_value(role),
        deep_link=f"/phase4/projections/{payload.projection_id}",
    )
    db.add(notification)
    db.flush()
    notification_ids.append(notification.id)
    event = audit(db, correlation_id=correlation_id, event_type="PHASE4_TYPED_PROJECTION_EXECUTED", entity_type="Phase4ProjectionReceipt", entity_id=payload.projection_id, actor_id=_role_value(role), after={"verified_assertion_id": assertion.id, "operation": payload.operation})
    audit_ids.append(event.id)
    receipt = Phase4ProjectionReceipt(
        projection_id=payload.projection_id,
        root_event_id=payload.root_event_id,
        verified_assertion_id=assertion.id,
        module_truth_contract_sha=PHASE3C_MODULE_TRUTH_SHA,
        corpus_app_contract_sha=PHASE4_CORPUS_APP_SHA,
        target_domain=payload.target_domain,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
        operation=payload.operation,
        precondition_version=payload.precondition_version,
        postcondition_version=f"{payload.precondition_version}:phase4-review",
        idempotency_key=payload.idempotency_key,
        result="PROJECTED_REVIEW_REQUIRED",
        created_ids_json=[],
        updated_ids_json=[],
        work_ids_json=work_ids,
        issue_ids_json=issue_ids,
        notification_ids_json=notification_ids,
        audit_ids_json=audit_ids,
        failure_or_review_reason="Human review required; protected actions remain blocked.",
        correlation_id=correlation_id,
    )
    db.add(receipt)
    db.flush()
    return receipt


def serialize(item: Any) -> dict[str, Any]:
    return _as_dict(item)
