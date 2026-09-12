"""Transactional controls for the Proposal commercial lifecycle.

These commands persist the protected boundary around Proposal release and
Contract handoff. They consume the existing Opportunity, Party, DocumentVersion,
Content Library and Contract models; they do not create competing domain truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Opportunity,
    ProposalAcceptedRevision,
    ProposalAcceptanceVerification,
    ProposalClientResponse,
    ProposalCommercialRelease,
    ProposalContractHandoff,
    ProposalDistributionEvent,
    ProposalEngineeringContribution,
    ProposalLpoReconciliation,
    ProposalScopeConfirmation,
    ProposalServiceEligibility,
    ProposalSourceEvidence,
    ProposalStalenessEvent,
    ProposalTechnicalAssessment,
)
from .proposal_workspace import stable_hash


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _proposal(db: Session, proposal_id: str) -> Opportunity:
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise ValueError("PROPOSAL_NOT_FOUND")
    return proposal


def latest_accepted(db: Session, proposal_id: str) -> ProposalAcceptedRevision:
    row = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal_id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    if not row:
        raise ValueError("ACCEPTED_REVISION_REQUIRED")
    return row


def current_scope(db: Session, proposal_id: str) -> ProposalScopeConfirmation | None:
    return db.scalar(select(ProposalScopeConfirmation).where(ProposalScopeConfirmation.proposal_id == proposal_id, ProposalScopeConfirmation.status == "CURRENT").order_by(ProposalScopeConfirmation.confirmed_at.desc()))


def _projection(row: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "value"):
            value = value.value
        result[column.name] = value
    return result


def record_technical_assessment(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str) -> ProposalTechnicalAssessment:
    _proposal(db, proposal_id)
    result = str(payload.get("status") or "").upper()
    if result not in {"PASS", "CONDITIONAL", "BLOCKED", "INCOMPLETE"}:
        raise ValueError("TECHNICAL_ASSESSMENT_STATUS_INVALID")
    findings = payload.get("findings") or []
    if not isinstance(findings, list):
        raise ValueError("TECHNICAL_ASSESSMENT_FINDINGS_INVALID")
    evidence_ids = payload.get("evidence_document_version_ids") or []
    if not isinstance(evidence_ids, list):
        raise ValueError("TECHNICAL_ASSESSMENT_EVIDENCE_INVALID")
    assessment_hash = str(payload.get("assessment_hash") or stable_hash({"proposal_id": proposal_id, "assessment_type": payload.get("assessment_type") or "SITE_TECHNICAL", "status": result, "findings": findings, "assumptions": payload.get("assumptions") or [], "evidence_document_version_ids": evidence_ids}))
    prior = db.scalar(select(ProposalTechnicalAssessment).where(ProposalTechnicalAssessment.proposal_id == proposal_id).order_by(ProposalTechnicalAssessment.assessed_at.desc()))
    if prior and prior.assessment_hash == assessment_hash:
        return prior
    if prior:
        prior.status = "SUPERSEDED"
    row = ProposalTechnicalAssessment(proposal_id=proposal_id, site_context_id=payload.get("site_context_id"), assessment_type=str(payload.get("assessment_type") or "SITE_TECHNICAL"), status=result, findings=findings, assumptions=payload.get("assumptions") or [], evidence_document_version_ids=[str(item) for item in evidence_ids], source_lineage=payload.get("source_lineage") or {"proposal_id": proposal_id, "source_evidence": [item.id for item in db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal_id, ProposalSourceEvidence.status == "CURRENT")).all()]}, assessment_hash=assessment_hash, assessed_by=actor, assessed_at=_now(), supersedes_id=prior.id if prior else None)
    db.add(row)
    db.flush()
    return row


def confirm_scope(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, capability: str, correlation_id: str) -> ProposalScopeConfirmation:
    proposal = _proposal(db, proposal_id)
    statement = str(payload.get("scope_statement") or "").strip()
    if not statement:
        raise ValueError("SCOPE_STATEMENT_REQUIRED")
    fields = payload.get("service_offering_codes") or []
    if not isinstance(fields, list) or any(not str(item).strip() for item in fields):
        raise ValueError("SERVICE_OFFERING_CODES_INVALID")
    assessment = db.scalar(select(ProposalTechnicalAssessment).where(ProposalTechnicalAssessment.proposal_id == proposal.id, ProposalTechnicalAssessment.status.in_(("PASS", "CONDITIONAL"))).order_by(ProposalTechnicalAssessment.assessed_at.desc()))
    if not assessment:
        raise ValueError("TECHNICAL_ASSESSMENT_REQUIRED")
    requested_assessments = [str(item) for item in payload.get("technical_assessment_ids") or []]
    if requested_assessments and assessment.id not in requested_assessments:
        raise ValueError("TECHNICAL_ASSESSMENT_NOT_CURRENT")
    requested_assessments = requested_assessments or [assessment.id]
    scope_hash = str(payload.get("scope_revision_hash") or stable_hash({"proposal_id": proposal.id, "statement": statement, "service_offering_codes": fields, "technical_assessment_ids": payload.get("technical_assessment_ids") or []}))
    previous = current_scope(db, proposal.id)
    if previous and previous.scope_revision_hash == scope_hash:
        return previous
    if previous:
        previous.status = "SUPERSEDED"
    row = ProposalScopeConfirmation(proposal_id=proposal.id, scope_revision_hash=scope_hash, scope_statement=statement, service_offering_codes=[str(item) for item in fields], technical_assessment_ids=requested_assessments, source_lineage=payload.get("source_lineage") or {"proposal_id": proposal.id, "source_evidence": [item.id for item in db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.status == "CURRENT")).all()], "engineering_contributions": [item.id for item in db.scalars(select(ProposalEngineeringContribution).where(ProposalEngineeringContribution.proposal_id == proposal.id)).all()], "technical_assessment_id": assessment.id}, confirmed_by=actor, confirming_capability=capability, confirmed_at=_now(), audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row


def record_eligibility(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str) -> ProposalServiceEligibility:
    _proposal(db, proposal_id)
    code = str(payload.get("service_offering_code") or "").strip()
    result = str(payload.get("result") or "").upper()
    if not code:
        raise ValueError("SERVICE_OFFERING_CODE_REQUIRED")
    if result not in {"ELIGIBLE", "NOT_ELIGIBLE", "UNRESOLVED"}:
        raise ValueError("SERVICE_ELIGIBILITY_RESULT_INVALID")
    row = db.scalar(select(ProposalServiceEligibility).where(ProposalServiceEligibility.proposal_id == proposal_id, ProposalServiceEligibility.service_offering_code == code))
    if not row:
        row = ProposalServiceEligibility(proposal_id=proposal_id, service_offering_code=code, result=result, professional_party_id=payload.get("professional_party_id"), capability_reference=payload.get("capability_reference"), policy_reference=payload.get("policy_reference"), evidence_document_version_id=payload.get("evidence_document_version_id"), decision_note=payload.get("decision_note"), decided_by=actor, decided_at=_now())
        db.add(row)
    else:
        row.result, row.professional_party_id, row.capability_reference, row.policy_reference, row.evidence_document_version_id, row.decision_note, row.decided_by, row.decided_at, row.status = result, payload.get("professional_party_id"), payload.get("capability_reference"), payload.get("policy_reference"), payload.get("evidence_document_version_id"), payload.get("decision_note"), actor, _now(), "CURRENT"
    db.flush()
    return row


def authorize_release(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, capability: str, correlation_id: str) -> tuple[ProposalCommercialRelease, bool]:
    proposal = _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal.id)
    requested_revision = payload.get("accepted_revision_id")
    if requested_revision and requested_revision != revision.id:
        raise ValueError("STALE_REVISION_RELEASE_FORBIDDEN")
    scope = current_scope(db, proposal.id)
    if not scope:
        raise ValueError("SCOPE_CONFIRMATION_REQUIRED")
    active_staleness = db.scalar(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id == proposal.id, ProposalStalenessEvent.status == "ACTIVE"))
    if active_staleness:
        raise ValueError("STALE_PROPOSAL_REVIEW_REQUIRED")
    eligibility = list(db.scalars(select(ProposalServiceEligibility).where(ProposalServiceEligibility.proposal_id == proposal.id, ProposalServiceEligibility.status == "CURRENT")).all())
    by_code = {row.service_offering_code: row for row in eligibility}
    for code in scope.service_offering_codes:
        if by_code.get(code) is None:
            raise ValueError("SERVICE_ELIGIBILITY_REQUIRED")
        if by_code[code].result != "ELIGIBLE":
            raise ValueError("SERVICE_NOT_ELIGIBLE")
    key = str(payload.get("idempotency_key") or f"release:{proposal.id}:{revision.id}")
    existing = db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.idempotency_key == key))
    if existing:
        if existing.proposal_id != proposal.id or existing.accepted_revision_id != revision.id:
            raise ValueError("IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        return existing, True
    row = ProposalCommercialRelease(proposal_id=proposal.id, accepted_revision_id=revision.id, content_hash=revision.content_hash, scope_confirmation_id=scope.id, eligibility_snapshot=[_projection(item) for item in eligibility], authorized_by=actor, authorizing_capability=capability, authorized_at=_now(), idempotency_key=key, audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False


def record_distribution(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalDistributionEvent, bool]:
    _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal_id)
    release = db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.proposal_id == proposal_id, ProposalCommercialRelease.accepted_revision_id == revision.id, ProposalCommercialRelease.status == "AUTHORIZED"))
    if not release:
        raise ValueError("COMMERCIAL_RELEASE_REQUIRED")
    evidence = str(payload.get("evidence_reference") or "").strip()
    if not evidence:
        raise ValueError("DISTRIBUTION_EVIDENCE_REQUIRED")
    key = str(payload.get("idempotency_key") or f"distribution:{proposal_id}:{revision.id}:{payload.get('channel') or 'UNSPECIFIED'}:{evidence}")
    existing = db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.idempotency_key == key))
    if existing:
        if existing.proposal_id != proposal_id:
            raise ValueError("IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        return existing, True
    row = ProposalDistributionEvent(proposal_id=proposal_id, accepted_revision_id=revision.id, commercial_release_id=release.id, channel=str(payload.get("channel") or "CLIENT_PORTAL"), recipient_party_id=payload.get("recipient_party_id"), recipient_contact_reference=payload.get("recipient_contact_reference"), evidence_document_version_id=payload.get("evidence_document_version_id"), evidence_reference=evidence, sent_at=_now(), sent_by=actor, audit_correlation_id=correlation_id, idempotency_key=key)
    db.add(row)
    db.flush()
    return row, False


def verify_acceptance(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalAcceptanceVerification, bool]:
    _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal_id)
    response = db.get(ProposalClientResponse, payload.get("client_response_id"))
    if not response or response.proposal_id != proposal_id or response.accepted_revision_id != revision.id:
        raise ValueError("CLIENT_ACCEPTANCE_RESPONSE_REVISION_MISMATCH")
    if response.response_type != "ACCEPTED":
        raise ValueError("CLIENT_ACCEPTANCE_RESPONSE_REQUIRED")
    evidence = str(payload.get("evidence_reference") or response.evidence_reference or "").strip()
    if not evidence:
        raise ValueError("CLIENT_ACCEPTANCE_EVIDENCE_REQUIRED")
    existing = db.scalar(select(ProposalAcceptanceVerification).where(ProposalAcceptanceVerification.client_response_id == response.id))
    if existing:
        return existing, True
    row = ProposalAcceptanceVerification(proposal_id=proposal_id, accepted_revision_id=revision.id, client_response_id=response.id, evidence_reference=evidence, evidence_document_version_id=payload.get("evidence_document_version_id"), verified_by=actor, verification_note=payload.get("verification_note"), verified_at=_now(), audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False


def reconcile_lpo(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalLpoReconciliation, bool]:
    _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal_id)
    key = str(payload.get("idempotency_key") or f"lpo:{proposal_id}:{revision.id}")
    existing = db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.idempotency_key == key))
    if existing:
        return existing, True
    applies = bool(payload.get("applies", True))
    variances = payload.get("variances") or []
    if not isinstance(variances, list):
        raise ValueError("LPO_VARIANCES_INVALID")
    if applies and not payload.get("client_artifact_reference") and not payload.get("client_document_version_id"):
        raise ValueError("LPO_EVIDENCE_REQUIRED")
    result = "NOT_APPLICABLE" if not applies else "MISMATCH" if variances else "PASS"
    row = ProposalLpoReconciliation(proposal_id=proposal_id, accepted_revision_id=revision.id, client_document_version_id=payload.get("client_document_version_id"), client_artifact_reference=payload.get("client_artifact_reference"), applies=applies, fields_compared=payload.get("fields_compared") or [], variances=variances, result=result, adjudication_note=payload.get("adjudication_note"), adjudicated_by=actor if payload.get("adjudication_note") else None, adjudicated_at=_now() if payload.get("adjudication_note") else None, compared_by=actor, compared_at=_now(), idempotency_key=key, audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False


def create_handoff(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalContractHandoff, bool]:
    proposal = _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal.id)
    release = db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.proposal_id == proposal.id, ProposalCommercialRelease.accepted_revision_id == revision.id, ProposalCommercialRelease.status == "AUTHORIZED"))
    if not release:
        raise ValueError("COMMERCIAL_RELEASE_REQUIRED")
    distribution = db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.proposal_id == proposal.id, ProposalDistributionEvent.accepted_revision_id == revision.id))
    if not distribution:
        raise ValueError("DISTRIBUTION_REQUIRED")
    acceptance = db.scalar(select(ProposalAcceptanceVerification).where(ProposalAcceptanceVerification.proposal_id == proposal.id, ProposalAcceptanceVerification.accepted_revision_id == revision.id, ProposalAcceptanceVerification.status == "VERIFIED"))
    if not acceptance:
        raise ValueError("CLIENT_ACCEPTANCE_VERIFICATION_REQUIRED")
    lpo = db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.proposal_id == proposal.id, ProposalLpoReconciliation.accepted_revision_id == revision.id))
    if not lpo:
        raise ValueError("LPO_RECONCILIATION_REQUIRED")
    if lpo.result not in {"PASS", "NOT_APPLICABLE"}:
        raise ValueError("LPO_RECONCILIATION_REQUIRED")
    key = str(payload.get("idempotency_key") or f"contract-handoff:{proposal.id}:{revision.id}")
    existing = db.scalar(select(ProposalContractHandoff).where(ProposalContractHandoff.idempotency_key == key))
    if existing:
        return existing, True
    snapshot = revision.snapshot or {}
    row = ProposalContractHandoff(proposal_id=proposal.id, accepted_revision_id=revision.id, acceptance_verification_id=acceptance.id, reconciliation_id=lpo.id, handoff_payload={"proposal_id": proposal.id, "proposal_reference": proposal.opportunity_reference, "client_account_id": proposal.client_account_id, "accepted_scope": snapshot.get("fields", {}).get("scope_of_work") or snapshot.get("fields", {}).get("sow"), "accepted_commercial_basis": snapshot.get("fields", {}), "source_ids": snapshot.get("source_ids", []), "content_lineage": {"content_hash": revision.content_hash, "template_version_id": revision.template_version_id, "checklist_version_id": revision.checklist_version_id}, "acceptance_verification_id": acceptance.id, "lpo_reconciliation_id": lpo.id}, handed_off_by=actor, handed_off_at=_now(), idempotency_key=key, audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False
