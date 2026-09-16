"""P07 shared Intelligence foundation control-plane primitives.

This module deliberately contains shared mechanics only.  It does not create
module queues, assign reviewers, mutate domain lifecycle, call providers, or
grant AI canonical/protected authority.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal
from ..audit.service import audit
from ..models import (
    AIExecutionLedger,
    AIWorkProduct,
    AIWorkProductDependency,
    AssertionStatus,
    CandidateAssertion,
    ContextDependency,
    ContextSnapshot,
    Contract,
    ContractRevision,
    DefinitionEntry,
    DefinitionRevision,
    DocumentApprovalState,
    DocumentVersion,
    FieldDefinition,
    FieldObservation,
    IntelligenceEvalPack,
    IntelligenceInvalidation,
    IntelligencePolicy,
    IntelligenceReviewDecision,
    IntelligenceToolDefinition,
    IntelligenceToolInvocation,
    Project,
    Opportunity,
    ProposalAcceptedRevision,
    ProposalRevision,
    VerifiedAssertion,
)
from .intelligence_contracts import IntelligenceContractError, stable_hash


P07_CONTEXT_CHANGED = "AI_CONTEXT_CHANGED_DURING_EXECUTION"
P07_STALE_REPLAY = "AI_STALE_WORK_PRODUCT_REPLAY"
P07_RESERVATION_FENCE = "AI_RESERVATION_FENCE_REJECTED"
P07_SENSITIVITY_DOWNGRADE = "AI_SENSITIVITY_DOWNGRADE_FORBIDDEN"

CLASSIFICATION_RANKS = {
    "SYNTHETIC": 0,
    "PUBLIC": 1,
    "INTERNAL": 10,
    "CONFIDENTIAL": 20,
    "SENSITIVE": 30,
    "RESTRICTED": 40,
    "SECRET": 50,
}

_family_locks: dict[str, threading.Lock] = {}
_family_locks_guard = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lock_for(key: str) -> threading.Lock:
    with _family_locks_guard:
        return _family_locks.setdefault(key, threading.Lock())


def derive_effective_classification(*values: object) -> str:
    """Return the strongest server-known classification; client values cannot lower it."""

    normalized = [str(value or "INTERNAL").upper() for value in values]
    return max(normalized, key=lambda value: CLASSIFICATION_RANKS.get(value, 40), default="INTERNAL")


def is_sensitive_field(field_code: str | None, document_type: object | None = None) -> bool:
    text = f"{field_code or ''} {getattr(document_type, 'value', document_type) or ''}".upper()
    return any(token in text for token in ("QID", "PASSPORT", "RESIDENCY", "PERSONAL", "PHONE", "EMAIL", "CREDENTIAL", "IDENTITY", "OWNER"))


def effective_source_classification(*, source: DocumentVersion | None = None, field: FieldDefinition | None = None, assertion_type: str | None = None, requested: str | None = None) -> tuple[str, bool]:
    source_metadata = (source.metadata_json or {}) if source is not None else {}
    source_policy = source_metadata.get("data_classification") or source_metadata.get("sensitivity_class")
    document_type = getattr(getattr(source, "document", None), "document_type", None)
    field_sensitive = is_sensitive_field(getattr(field, "field_code", None), document_type)
    classification = derive_effective_classification(
        "SYNTHETIC" if source_metadata.get("synthetic_non_business_fixture") else None,
        source_policy,
        "SENSITIVE" if field_sensitive else None,
        "SENSITIVE" if is_sensitive_field(assertion_type, document_type) else None,
        requested,
    )
    return classification, field_sensitive or classification in {"SENSITIVE", "RESTRICTED", "SECRET"}


def _document_version_current(version: DocumentVersion | None, expected_hash: str | None = None) -> bool:
    if version is None or version.document is None:
        return False
    if expected_hash and version.sha256 != expected_hash:
        return False
    return version.document.current_version_id == version.id and version.superseded_by is None and version.approval_state != DocumentApprovalState.SUPERSEDED


def dependency_current(db: Session, dependency: ContextDependency | AIWorkProductDependency) -> bool:
    """Resolve currentness from canonical state, never from a client assertion."""

    kind = str(dependency.dependency_type).upper()
    expected = dependency.dependency_version_or_hash
    if kind == "DOCUMENT_VERSION":
        version = db.get(DocumentVersion, dependency.dependency_id)
        return _document_version_current(version, expected)
    if kind == "CANDIDATE_ASSERTION":
        candidate = db.get(CandidateAssertion, dependency.dependency_id)
        return candidate is not None and str(candidate.status) == "CURRENT" and (not expected or expected == candidate.value_hash)
    if kind == "VERIFIED_ASSERTION":
        assertion = db.get(VerifiedAssertion, dependency.dependency_id)
        if assertion is None or str(getattr(assertion.status, "value", assertion.status)) != AssertionStatus.CURRENT.value:
            return False
        observation = db.get(FieldObservation, assertion.source_observation_id) if assertion.source_observation_id else None
        return observation is not None and _document_version_current(db.get(DocumentVersion, observation.document_version_id))
    if kind == "MASTER_CONTENT_VERSION":
        return _document_version_current(db.get(DocumentVersion, dependency.dependency_id), expected)
    if kind == "DEFINITION_REVISION":
        revision = db.get(DefinitionRevision, dependency.dependency_id)
        if revision is None:
            return False
        definition = db.get(DefinitionEntry, revision.definition_id)
        return definition is not None and definition.current_revision_id == revision.id and revision.status == "CURRENT"
    if kind == "POLICY_VERSION":
        policy = db.get(IntelligencePolicy, dependency.dependency_id)
        return policy is not None and policy.state == "ACTIVE" and policy.immutable_hash == expected
    if kind == "SKILL_MANIFEST":
        return str(expected) == str(dependency.metadata_json.get("manifest_hash", expected))
    if kind == "DOMAIN_ENTITY_REVISION":
        metadata = dependency.metadata_json or {}
        if str(metadata.get("domain_entity", "")).upper() == "PROPOSAL":
            proposal = db.get(Opportunity, dependency.dependency_id)
            if proposal is None:
                return False
            accepted = db.scalars(select(ProposalAcceptedRevision).where(
                ProposalAcceptedRevision.proposal_id == proposal.id,
                ProposalAcceptedRevision.status == "ACCEPTED",
            ).order_by(ProposalAcceptedRevision.revision_number.desc(), ProposalAcceptedRevision.accepted_at.desc())).first()
            working = db.scalar(select(ProposalRevision).where(
                ProposalRevision.proposal_id == proposal.id,
                ProposalRevision.status == "DRAFT",
            ).order_by(ProposalRevision.revision_number.desc()))
            if metadata.get("accepted_revision_required") and accepted is None:
                return False
            if working is not None and accepted is not None and working.base_accepted_revision_id and working.base_accepted_revision_id != accepted.id:
                return False
            selected_revision = accepted if metadata.get("accepted_revision_required") and accepted else (working if working else accepted)
            current = (
                f"{selected_revision.id}:{selected_revision.revision_number}:{selected_revision.content_hash}"
                if selected_revision is not None
                else stable_hash({"proposal_id": proposal.id, "proposal_fields": proposal.proposal_fields_json, "updated_at": proposal.updated_at.isoformat()})
            )
            return current == expected
        if str(metadata.get("domain_entity", "")).upper() == "CONTRACT":
            contract = db.get(Contract, dependency.dependency_id)
            if contract is None or not contract.current_revision_id:
                return False
            revision = db.get(ContractRevision, contract.current_revision_id)
            if revision is None:
                return False
            current = f"{revision.id}:{revision.revision_number}:{revision.content_hash}"
            return current == expected
        project = db.get(Project, dependency.dependency_id)
        if project is None:
            return False
        projection = {
            "entity_type": "PROJECT", "entity_id": project.id,
            "project_number": project.project_number, "project_code": project.project_code,
            "project_name": project.project_name, "workstream": project.workstream,
            "status": project.status, "municipality": project.municipality,
            "permit_type": project.permit_type,
        }
        return stable_hash(projection) == expected
    return bool(dependency.currentness_state_at_capture == "CURRENT")


def ensure_builtin_policy(db: Session, version: str) -> IntelligencePolicy:
    """Materialize the server-owned shared policy identity used by P07 context."""

    return register_policy(
        db,
        policy_code="SHARED_INTELLIGENCE",
        version=version,
        policy={"policy_version": version, "authority": "HUMAN_ONLY", "model_selected_tool_calling": False},
    )


def bind_work_product_dependencies(db: Session, work_product: AIWorkProduct, *, snapshot_id: str | None = None) -> list[AIWorkProductDependency]:
    """Materialize the snapshot's exact dependency identities onto the product."""

    snapshot_id = snapshot_id or work_product.context_snapshot_id
    dependencies = db.scalars(select(ContextDependency).where(ContextDependency.context_snapshot_id == snapshot_id)).all()
    result: list[AIWorkProductDependency] = []
    for dependency in dependencies:
        existing = db.scalar(select(AIWorkProductDependency).where(
            AIWorkProductDependency.work_product_id == work_product.id,
            AIWorkProductDependency.dependency_type == dependency.dependency_type,
            AIWorkProductDependency.dependency_id == dependency.dependency_id,
            AIWorkProductDependency.dependency_version_or_hash == dependency.dependency_version_or_hash,
        ))
        if existing is None:
            existing = AIWorkProductDependency(
                work_product_id=work_product.id,
                dependency_type=dependency.dependency_type,
                dependency_id=dependency.dependency_id,
                dependency_version_or_hash=dependency.dependency_version_or_hash,
                dependency_metadata_json=dict(dependency.metadata_json or {}),
            )
            db.add(existing)
        result.append(existing)
    work_product.lineage_hash = stable_hash([
        {"type": item.dependency_type, "id": item.dependency_id, "version": item.dependency_version_or_hash}
        for item in sorted(result, key=lambda value: (value.dependency_type, value.dependency_id, value.dependency_version_or_hash))
    ])
    db.flush()
    return result


def revalidate_snapshot(db: Session, snapshot_id: str) -> list[ContextDependency]:
    snapshot = db.get(ContextSnapshot, snapshot_id)
    if snapshot is None:
        raise IntelligenceContractError("AI_CONTEXT_SNAPSHOT_NOT_FOUND")
    dependencies = db.scalars(select(ContextDependency).where(ContextDependency.context_snapshot_id == snapshot_id)).all()
    return [dependency for dependency in dependencies if not dependency_current(db, dependency)]


def _invalidation_once(db: Session, *, work_product: AIWorkProduct, dependency_type: str, dependency_id: str, prior_version: str | None, superseding_version: str | None, source_event_id: str, reason_code: str, resulting_state: str = "STALE", metadata: Mapping[str, Any] | None = None) -> IntelligenceInvalidation:
    existing = db.scalar(select(IntelligenceInvalidation).where(IntelligenceInvalidation.work_product_id == work_product.id, IntelligenceInvalidation.source_event_id == source_event_id))
    if existing is not None:
        return existing
    prior_state = str(work_product.state)
    if prior_state not in {"INVALID"}:
        work_product.state = resulting_state
    work_product.stale_at = work_product.stale_at or _now()
    work_product.stale_reason = work_product.stale_reason or reason_code
    work_product.invalidation_count = int(work_product.invalidation_count or 0) + 1
    event = IntelligenceInvalidation(
        work_product_id=work_product.id,
        prior_state=prior_state,
        resulting_state=resulting_state,
        dependency_type=dependency_type,
        dependency_id=dependency_id,
        prior_dependency_version_or_hash=prior_version,
        superseding_dependency_version_or_hash=superseding_version,
        source_event_id=source_event_id,
        reason_code=reason_code,
        metadata_json=dict(metadata or {}),
    )
    db.add(event)
    audit(db, correlation_id=work_product.correlation_id, event_type="AI_WORK_PRODUCT_INVALIDATED", entity_type="AIWorkProduct", entity_id=work_product.id, metadata={"dependency_type": dependency_type, "dependency_id": dependency_id, "source_event_id": source_event_id, "reason_code": reason_code})
    return event


def invalidate_dependency(db: Session, *, dependency_type: str, dependency_id: str, superseding_version_or_hash: str | None = None, source_event_id: str | None = None, reason_code: str = "DEPENDENCY_SUPERSEDED") -> int:
    """Idempotently stale only products causally bound to the changed dependency."""

    source_event_id = source_event_id or f"{dependency_type}:{dependency_id}:{superseding_version_or_hash or 'changed'}"
    edges = db.scalars(select(AIWorkProductDependency).where(AIWorkProductDependency.dependency_type == dependency_type, AIWorkProductDependency.dependency_id == dependency_id)).all()
    count = 0
    for edge in edges:
        product = db.get(AIWorkProduct, edge.work_product_id)
        if product is None:
            continue
        _invalidation_once(db, work_product=product, dependency_type=dependency_type, dependency_id=dependency_id, prior_version=edge.dependency_version_or_hash, superseding_version=superseding_version_or_hash, source_event_id=source_event_id, reason_code=reason_code)
        count += 1
    db.flush()
    if count:
        audit(db, correlation_id=source_event_id, event_type="AI_DEPENDENCY_SUPERSEDED", entity_type=dependency_type, entity_id=dependency_id, metadata={"affected_work_products": count, "source_event_id": source_event_id})
    return count


def finalize_current_work_product(db: Session, *, work_product: AIWorkProduct, snapshot_id: str | None = None, source_event_id: str | None = None) -> AIWorkProduct:
    changed = revalidate_snapshot(db, snapshot_id or work_product.context_snapshot_id)
    if changed:
        for dependency in changed:
            event_id = source_event_id or f"context-finalization:{work_product.id}:{dependency.dependency_type}:{dependency.dependency_id}"
            _invalidation_once(db, work_product=work_product, dependency_type=dependency.dependency_type, dependency_id=dependency.dependency_id, prior_version=dependency.dependency_version_or_hash, superseding_version=None, source_event_id=event_id, reason_code=P07_CONTEXT_CHANGED, resulting_state="STALE")
        raise IntelligenceContractError(P07_CONTEXT_CHANGED)
    bind_work_product_dependencies(db, work_product, snapshot_id=snapshot_id)
    work_product.state = "CURRENT"
    return work_product


def replay_work_product(db: Session, *, idempotency_key: str) -> AIWorkProduct:
    product = db.scalar(select(AIWorkProduct).where(AIWorkProduct.idempotency_key == idempotency_key))
    if product is None:
        raise IntelligenceContractError("AI_IDEMPOTENCY_REPLAY_INCOMPLETE")
    changed = revalidate_snapshot(db, product.context_snapshot_id)
    if changed:
        for dependency in changed:
            _invalidation_once(db, work_product=product, dependency_type=dependency.dependency_type, dependency_id=dependency.dependency_id, prior_version=dependency.dependency_version_or_hash, superseding_version=None, source_event_id=f"replay-currentness:{product.id}:{dependency.dependency_type}:{dependency.dependency_id}", reason_code=P07_CONTEXT_CHANGED)
        db.flush()
        raise IntelligenceContractError(P07_STALE_REPLAY)
    if str(product.state) != "CURRENT":
        raise IntelligenceContractError(P07_STALE_REPLAY)
    return product


@dataclass(frozen=True)
class ReservationLease:
    ledger: AIExecutionLedger
    owner_token: str
    generation: int
    maximum_cost: float


def reservation_expired(ledger: AIExecutionLedger, now: datetime | None = None) -> bool:
    expiry = ledger.reservation_lease_expires_at
    return bool(expiry and expiry <= (now or _now()))


def reclaim_expired_reservation(db: Session, *, idempotency_key: str, request_fingerprint: str, actor_user_id: str | None, lease_seconds: int = 300) -> ReservationLease:
    ledger = db.scalar(select(AIExecutionLedger).where(AIExecutionLedger.idempotency_key == idempotency_key).with_for_update())
    if ledger is None:
        raise IntelligenceContractError("AI_RESERVATION_NOT_FOUND")
    if ledger.request_fingerprint != request_fingerprint or ledger.actor_user_id != actor_user_id:
        raise IntelligenceContractError("AI_IDEMPOTENCY_CONFLICT")
    if ledger.status != "RESERVED":
        raise IntelligenceContractError("AI_RESERVATION_TERMINAL_NOT_RECLAIMABLE")
    if not reservation_expired(ledger):
        raise IntelligenceContractError("AI_RESERVATION_LEASE_NOT_EXPIRED")
    ledger.reservation_generation = int(ledger.reservation_generation or 1) + 1
    ledger.reservation_owner_token = uuid4().hex
    ledger.reserved_at = _now()
    ledger.reservation_lease_expires_at = ledger.reserved_at + timedelta(seconds=lease_seconds)
    ledger.reservation_reclaimed_at = ledger.reserved_at
    audit(db, correlation_id=ledger.correlation_id, event_type="AI_RESERVATION_RECLAIMED", entity_type="AIExecutionLedger", entity_id=ledger.id, actor_id=actor_user_id, metadata={"generation": ledger.reservation_generation})
    db.flush()
    return ReservationLease(ledger, ledger.reservation_owner_token, ledger.reservation_generation, float(ledger.reserved_cost_usd or 0))


def assert_reservation_fence(ledger: AIExecutionLedger, *, owner_token: str | None, generation: int | None) -> None:
    if ledger.reservation_owner_token and owner_token != ledger.reservation_owner_token:
        raise IntelligenceContractError(P07_RESERVATION_FENCE)
    if generation is not None and int(ledger.reservation_generation or 1) != int(generation):
        raise IntelligenceContractError(P07_RESERVATION_FENCE)


def register_policy(db: Session, *, policy_code: str, version: str, policy: Mapping[str, Any], state: str = "ACTIVE", policy_id: str | None = None) -> IntelligencePolicy:
    identity = policy_id or f"policy:{policy_code}:{version}"
    digest = stable_hash({"policy_code": policy_code, "version": version, "policy": dict(policy)})
    existing = db.get(IntelligencePolicy, identity)
    if existing is not None:
        if existing.immutable_hash != digest or existing.policy_json != dict(policy):
            raise IntelligenceContractError("AI_POLICY_IDENTITY_IMMUTABLE")
        return existing
    obj = IntelligencePolicy(id=identity, policy_code=policy_code, version=version, immutable_hash=digest, state=state, policy_json=dict(policy))
    db.add(obj)
    db.flush()
    return obj


def resolve_policy(db: Session, *, policy_id: str, version: str | None = None, immutable_hash: str | None = None) -> IntelligencePolicy:
    obj = db.get(IntelligencePolicy, policy_id)
    if obj is None or obj.state != "ACTIVE" or (version and obj.version != version) or (immutable_hash and obj.immutable_hash != immutable_hash):
        raise IntelligenceContractError("AI_POLICY_IDENTITY_NOT_ACTIVE")
    return obj


def register_eval_pack(db: Session, *, eval_pack_id: str, version: str, owning_module: str, critical_case_policy: str, acceptance_threshold_policy: str, state: str = "ACTIVE") -> IntelligenceEvalPack:
    digest = stable_hash({"eval_pack_id": eval_pack_id, "version": version, "owning_module": owning_module, "critical_case_policy": critical_case_policy, "acceptance_threshold_policy": acceptance_threshold_policy})
    identity = f"eval:{eval_pack_id}:{version}"
    existing = db.get(IntelligenceEvalPack, identity)
    if existing is not None:
        if existing.immutable_hash != digest:
            raise IntelligenceContractError("AI_EVAL_PACK_IDENTITY_IMMUTABLE")
        return existing
    obj = IntelligenceEvalPack(id=identity, eval_pack_id=eval_pack_id, version=version, immutable_hash=digest, owning_module=owning_module, critical_case_policy=critical_case_policy, acceptance_threshold_policy=acceptance_threshold_policy, state=state)
    db.add(obj)
    db.flush()
    return obj


def record_module_review_decision(db: Session, *, principal: AuthenticatedPrincipal, owning_module: str, review_subject_type: str, review_subject_id: str, decision: str, idempotency_key: str, correlation_id: str, authorizing_capability: str, precondition_version: str, candidate_assertion_id: str | None = None, work_product_id: str | None = None, context_snapshot_id: str | None = None, source_currentness_identity: Mapping[str, Any] | None = None, correction_payload: Mapping[str, Any] | None = None, reason: str | None = None) -> IntelligenceReviewDecision:
    if not principal.user_id:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_AUTHENTICATED_PRINCIPAL_REQUIRED")
    if not authorizing_capability:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_CAPABILITY_REQUIRED")
    try:
        from .backend_realignment import require_capability
        require_capability(principal.role, authorizing_capability)
    except Exception as exc:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_CAPABILITY_DENIED") from exc
    if decision not in {"ACCEPT", "CORRECT", "REJECT", "DEFER", "ESCALATE"}:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_DECISION_UNSUPPORTED")
    if work_product_id and candidate_assertion_id:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_SUBJECT_AMBIGUOUS")
    existing = db.scalar(select(IntelligenceReviewDecision).where(IntelligenceReviewDecision.idempotency_key == idempotency_key))
    from .backend_realignment import persona_for_role
    payload = {"idempotency_key": idempotency_key, "owning_module": owning_module, "review_subject_type": review_subject_type, "review_subject_id": review_subject_id, "candidate_assertion_id": candidate_assertion_id, "work_product_id": work_product_id, "context_snapshot_id": context_snapshot_id, "reviewer_user_id": principal.user_id, "reviewer_persona": persona_for_role(principal.role), "authorizing_capability": authorizing_capability, "decision": decision, "correction_payload": dict(correction_payload or {}) if correction_payload is not None else None, "reason": reason, "precondition_version": precondition_version, "correlation_id": correlation_id, "source_currentness_identity": dict(source_currentness_identity or {})}
    digest = stable_hash(payload)
    if existing is not None:
        if existing.decision_hash != digest:
            raise IntelligenceContractError("INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return existing
    obj = IntelligenceReviewDecision(**payload, decision_hash=digest)
    db.add(obj)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="AI_MODULE_REVIEW_DECISION_RECORDED", entity_type="IntelligenceReviewDecision", entity_id=obj.id, actor_id=principal.user_id, metadata={"owning_module": owning_module, "decision": decision})
    return obj


def promote_verified_assertion_from_decision(db: Session, *, principal: AuthenticatedPrincipal, decision_id: str, candidate_id: str | None = None, correction_payload: Mapping[str, Any] | None = None) -> VerifiedAssertion:
    decision = db.get(IntelligenceReviewDecision, decision_id)
    if decision is None or decision.decision not in {"ACCEPT", "CORRECT"}:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_DECISION_NOT_PROMOTABLE")
    if decision.reviewer_user_id != principal.user_id:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_ACTOR_MISMATCH")
    candidate = db.get(CandidateAssertion, candidate_id or decision.candidate_assertion_id)
    if candidate is None or candidate.field_definition_id is None or str(candidate.status) != "CURRENT":
        raise IntelligenceContractError("INTELLIGENCE_CANDIDATE_NOT_ELIGIBLE_FOR_VERIFICATION")
    if not candidate.source_document_version_id:
        raise IntelligenceContractError("INTELLIGENCE_CANDIDATE_SOURCE_REQUIRED")
    version = db.get(DocumentVersion, candidate.source_document_version_id)
    if not _document_version_current(version):
        raise IntelligenceContractError("INTELLIGENCE_SOURCE_NOT_CURRENT")
    if candidate.project_id and decision.owning_module and candidate.target_module and candidate.target_module.upper() != decision.owning_module.upper():
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_MODULE_SCOPE_MISMATCH")
    field = db.get(FieldDefinition, candidate.field_definition_id)
    if field is None or not field.active:
        raise IntelligenceContractError("INTELLIGENCE_FIELD_DEFINITION_NOT_CURRENT")
    value = dict(correction_payload or decision.correction_payload or {}) if decision.decision == "CORRECT" else dict(candidate.value_json or {})
    current = db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.scope_type == candidate.scope_type, VerifiedAssertion.scope_id == candidate.scope_id, VerifiedAssertion.subject_type == candidate.subject_type, VerifiedAssertion.subject_id == candidate.subject_id, VerifiedAssertion.field_definition_id == candidate.field_definition_id, VerifiedAssertion.status == AssertionStatus.CURRENT)).all()
    for prior in current:
        prior.status = AssertionStatus.SUPERSEDED
    result = VerifiedAssertion(scope_type=candidate.scope_type, scope_id=candidate.scope_id, project_id=candidate.project_id, subject_type=candidate.subject_type, subject_id=candidate.subject_id, field_definition_id=field.id, semantic_value_json=value, display_value=candidate.display_value or json.dumps(value, sort_keys=True), status=AssertionStatus.CURRENT, source_observation_id=candidate.source_observation_id, verification_method="HUMAN_VERIFIED", verified_by=principal.user_id, verified_by_capability=decision.authorizing_capability, verification_origin_module=decision.owning_module, review_decision_reference=decision.id, reason=decision.reason, supersedes_assertion_id=current[-1].id if current else None)
    db.add(result)
    candidate.status = "PROMOTED"
    candidate.promoted_verified_assertion_id = result.id
    db.flush()
    audit(db, correlation_id=decision.correlation_id, event_type="AI_VERIFIED_ASSERTION_HUMAN_PROMOTED", entity_type="VerifiedAssertion", entity_id=result.id, actor_id=principal.user_id, metadata={"decision_id": decision.id, "candidate_id": candidate.id})
    return result


@dataclass(frozen=True)
class ToolContract:
    tool_id: str
    version: str
    input_schema: Mapping[str, Any]
    output_schema: Mapping[str, Any]
    allowed_modules: tuple[str, ...] = ()
    allowed_skills: tuple[str, ...] = ()
    required_capability: str | None = None
    data_classification_ceiling: str = "INTERNAL"
    timeout_ms: int = 1000
    budget_units: int = 1
    read_only: bool = True

    @property
    def immutable_hash(self) -> str:
        return stable_hash({"tool_id": self.tool_id, "version": self.version, "input_schema": dict(self.input_schema), "output_schema": dict(self.output_schema), "allowed_modules": self.allowed_modules, "allowed_skills": self.allowed_skills, "required_capability": self.required_capability, "data_classification_ceiling": self.data_classification_ceiling, "timeout_ms": self.timeout_ms, "budget_units": self.budget_units, "read_only": self.read_only})


class ReadOnlyToolRuntime:
    """Server-orchestrated read-only tool runtime; model-selected loops stay disabled."""

    MODEL_SELECTED_TOOL_CALLING = False

    def __init__(self) -> None:
        self._contracts: dict[tuple[str, str], tuple[ToolContract, Callable[[Mapping[str, Any]], Mapping[str, Any]]]] = {}

    def register(self, contract: ToolContract, handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        if not contract.read_only or any(token in contract.tool_id.lower() for token in ("write", "mutate", "submit", "approve", "shell", "exec", "payment")):
            raise IntelligenceContractError("AI_TOOL_MUTATION_FORBIDDEN")
        if (contract.tool_id, contract.version) in self._contracts:
            raise IntelligenceContractError("AI_TOOL_IDENTITY_IMMUTABLE")
        self._contracts[(contract.tool_id, contract.version)] = (contract, handler)

    def invoke(self, db: Session, *, principal: AuthenticatedPrincipal, tool_id: str, version: str, request: Mapping[str, Any], owning_module: str, skill_id: str, correlation_id: str, idempotency_key: str, context_snapshot_id: str | None = None, data_classification: str = "INTERNAL") -> Mapping[str, Any]:
        if not principal.user_id:
            raise IntelligenceContractError("AI_TOOL_AUTHENTICATED_PRINCIPAL_REQUIRED")
        contract_handler = self._contracts.get((tool_id, version))
        request_hash = stable_hash(request)
        if contract_handler is None:
            raise IntelligenceContractError("AI_TOOL_NOT_REGISTERED")
        contract, handler = contract_handler
        invocation = IntelligenceToolInvocation(idempotency_key=idempotency_key, tool_id=tool_id, tool_version=version, tool_hash=contract.immutable_hash, owning_module=owning_module, skill_id=skill_id, actor_user_id=principal.user_id or "", context_snapshot_id=context_snapshot_id, request_hash=request_hash, outcome="DENIED", error_code=None, correlation_id=correlation_id)
        db.add(invocation)
        db.flush()
        if contract.allowed_modules and owning_module not in contract.allowed_modules:
            invocation.error_code = "AI_TOOL_MODULE_NOT_ALLOWED"
            audit(db, correlation_id=correlation_id, event_type="AI_TOOL_DENIED", entity_type="IntelligenceToolInvocation", entity_id=invocation.id, actor_id=principal.user_id, metadata={"tool_id": tool_id, "reason": invocation.error_code})
            db.flush()
            raise IntelligenceContractError(invocation.error_code)
        if contract.allowed_skills and skill_id not in contract.allowed_skills:
            invocation.error_code = "AI_TOOL_SKILL_NOT_ALLOWED"
            db.flush()
            raise IntelligenceContractError(invocation.error_code)
        if contract.required_capability:
            try:
                from .backend_realignment import require_capability
                require_capability(principal.role, contract.required_capability)
            except Exception as exc:
                invocation.error_code = "AI_TOOL_CAPABILITY_DENIED"
                db.flush()
                raise IntelligenceContractError(invocation.error_code) from exc
        if CLASSIFICATION_RANKS.get(str(data_classification).upper(), 40) > CLASSIFICATION_RANKS.get(contract.data_classification_ceiling.upper(), 10):
            invocation.error_code = "AI_TOOL_CLASSIFICATION_CEILING_EXCEEDED"
            db.flush()
            raise IntelligenceContractError(invocation.error_code)
        required = contract.input_schema.get("required", [])
        properties = contract.input_schema.get("properties", {})
        if any(key not in request for key in required) or (contract.input_schema.get("additionalProperties") is False and any(key not in properties for key in request)):
            invocation.error_code = "AI_TOOL_INPUT_SCHEMA_INVALID"
            db.flush()
            raise IntelligenceContractError(invocation.error_code)
        started = time.monotonic()
        try:
            output = handler(dict(request))
            if time.monotonic() - started > contract.timeout_ms / 1000:
                raise IntelligenceContractError("AI_TOOL_TIMEOUT")
            if not isinstance(output, Mapping) or not _schema_mapping_valid(output, contract.output_schema):
                raise IntelligenceContractError("AI_TOOL_OUTPUT_SCHEMA_INVALID")
            invocation.outcome = "SUCCEEDED"
            invocation.output_hash = stable_hash(output)
            audit(db, correlation_id=correlation_id, event_type="AI_TOOL_INVOCATION", entity_type="IntelligenceToolInvocation", entity_id=invocation.id, actor_id=principal.user_id, metadata={"tool_id": tool_id, "tool_version": version, "tool_hash": contract.immutable_hash, "outcome": invocation.outcome})
            db.flush()
            return dict(output)
        except IntelligenceContractError as exc:
            invocation.error_code = exc.code
            audit(db, correlation_id=correlation_id, event_type="AI_TOOL_DENIED", entity_type="IntelligenceToolInvocation", entity_id=invocation.id, actor_id=principal.user_id, metadata={"tool_id": tool_id, "reason": exc.code})
            db.flush()
            raise


def _schema_mapping_valid(value: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    """Small deterministic subset of JSON Schema for bounded tool envelopes."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if any(key not in value for key in required):
        return False
    if schema.get("additionalProperties") is False and any(key not in properties for key in value):
        return False
    for key, spec in properties.items():
        if key not in value or not isinstance(spec, Mapping) or "type" not in spec:
            continue
        expected = spec["type"]
        actual = value[key]
        if expected == "object" and not isinstance(actual, Mapping):
            return False
        if expected == "array" and not isinstance(actual, list):
            return False
        if expected == "string" and not isinstance(actual, str):
            return False
        if expected == "boolean" and not isinstance(actual, bool):
            return False
        if expected == "number" and (isinstance(actual, bool) or not isinstance(actual, (int, float))):
            return False
        if expected == "integer" and (isinstance(actual, bool) or not isinstance(actual, int)):
            return False
    return True


# Stable public names for downstream module adapters and hostile tests.
invalidate_work_products_for_dependency = invalidate_dependency
finalization_currentness_fence = finalize_current_work_product
record_review_decision = record_module_review_decision
promote_candidate_to_verified_assertion = promote_verified_assertion_from_decision
