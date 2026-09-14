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
    ClientAccount,
    ClientContact,
    DocumentVersion,
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
    ProposalOutputArtifact,
)
from .proposal_production_boundary import production_mode, require_canonical_active_client, require_current_professional_party, require_exact_document_version, require_proposal_scoped_evidence, reject_synthetic_value
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
    if production_mode():
        if result == "PASS" and not evidence_ids:
            raise ValueError("TECHNICAL_ASSESSMENT_EVIDENCE_REQUIRED")
        for version_id in evidence_ids:
            require_proposal_scoped_evidence(db, proposal_id=proposal_id, version_id=str(version_id), source_roles=("TECHNICAL_ASSESSMENT", "TENDER_DOCUMENT", "CLIENT_DATA"), code="TECHNICAL_ASSESSMENT_EVIDENCE_REQUIRED")
        reject_synthetic_value(payload.get("source_lineage"), code="TECHNICAL_ASSESSMENT_EVIDENCE_REQUIRED")
    assessment_hash = stable_hash({"proposal_id": proposal_id, "assessment_type": payload.get("assessment_type") or "SITE_TECHNICAL", "status": result, "findings": findings, "assumptions": payload.get("assumptions") or [], "evidence_document_version_ids": [str(item) for item in evidence_ids]})
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
    proposal = _proposal(db, proposal_id)
    code = str(payload.get("service_offering_code") or "").strip()
    result = str(payload.get("result") or "").upper()
    if not code:
        raise ValueError("SERVICE_OFFERING_CODE_REQUIRED")
    if result not in {"ELIGIBLE", "NOT_ELIGIBLE", "UNRESOLVED"}:
        raise ValueError("SERVICE_ELIGIBILITY_RESULT_INVALID")
    if production_mode():
        if result == "ELIGIBLE":
            require_canonical_active_client(db, proposal.client_account_id)
            scope = current_scope(db, proposal_id)
            if not scope or payload.get("scope_confirmation_id") != scope.id or payload.get("scope_revision_hash") != scope.scope_revision_hash:
                raise ValueError("ELIGIBILITY_SCOPE_CONFIRMATION_REQUIRED")
            discipline = payload.get("discipline")
            require_current_professional_party(db, payload.get("professional_party_id"), office_id=proposal.office_id, service_code=code, discipline=discipline)
            evidence_version = require_proposal_scoped_evidence(db, proposal_id=proposal_id, version_id=payload.get("evidence_document_version_id"), source_roles=("SERVICE_ELIGIBILITY", "TECHNICAL_ASSESSMENT"), code="ELIGIBILITY_EVIDENCE_REQUIRED", client_account_id=proposal.client_account_id)
            for field in ("capability_reference", "policy_reference"):
                if not str(payload.get(field) or "").strip():
                    raise ValueError(f"ELIGIBILITY_{field.upper()}_REQUIRED")
            if not str(payload.get("policy_version") or "").strip():
                raise ValueError("ELIGIBILITY_POLICY_VERSION_REQUIRED")
            reject_synthetic_value({key: payload.get(key) for key in ("capability_reference", "policy_reference", "decision_note")}, code="ELIGIBILITY_EVIDENCE_REQUIRED")
        else:
            evidence_version = None
    row = db.scalar(select(ProposalServiceEligibility).where(ProposalServiceEligibility.proposal_id == proposal_id, ProposalServiceEligibility.service_offering_code == code))
    if not row:
        row = ProposalServiceEligibility(proposal_id=proposal_id, service_offering_code=code, result=result, professional_party_id=payload.get("professional_party_id"), capability_reference=payload.get("capability_reference"), policy_reference=payload.get("policy_reference"), evidence_document_version_id=payload.get("evidence_document_version_id"), evidence_sha256=evidence_version.sha256 if production_mode() and result == "ELIGIBLE" else None, scope_confirmation_id=payload.get("scope_confirmation_id"), scope_revision_hash=payload.get("scope_revision_hash"), authority_snapshot={"professional_party_id": payload.get("professional_party_id"), "discipline": payload.get("discipline"), "capability_reference": payload.get("capability_reference"), "policy_reference": payload.get("policy_reference")}, policy_version=payload.get("policy_version"), as_of=_now(), decision_note=payload.get("decision_note"), decided_by=actor, decided_at=_now())
        db.add(row)
    else:
        row.result, row.professional_party_id, row.capability_reference, row.policy_reference, row.evidence_document_version_id, row.evidence_sha256, row.scope_confirmation_id, row.scope_revision_hash, row.authority_snapshot, row.policy_version, row.as_of, row.decision_note, row.decided_by, row.decided_at, row.status = result, payload.get("professional_party_id"), payload.get("capability_reference"), payload.get("policy_reference"), payload.get("evidence_document_version_id"), evidence_version.sha256 if production_mode() and result == "ELIGIBLE" else None, payload.get("scope_confirmation_id"), payload.get("scope_revision_hash"), {"professional_party_id": payload.get("professional_party_id"), "discipline": payload.get("discipline"), "capability_reference": payload.get("capability_reference"), "policy_reference": payload.get("policy_reference")}, payload.get("policy_version"), _now(), payload.get("decision_note"), actor, _now(), "CURRENT"
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
    outputs = db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal.id, ProposalOutputArtifact.revision_id == revision.id)).all()
    if production_mode() and {item.artifact_type for item in outputs} != {"PROPOSAL", "CHECKLIST"}:
        raise ValueError("PRODUCTION_ARTIFACTS_REQUIRED")
    if production_mode() and any(item.synthetic_only or not item.document_version_id or not item.storage_reference.startswith("storage://") for item in outputs):
        raise ValueError("PRODUCTION_ARTIFACTS_REQUIRED")
    if production_mode():
        for artifact in outputs:
            version = require_exact_document_version(db, artifact.document_version_id, code="PRODUCTION_ARTIFACTS_REQUIRED")
            if version.sha256 != artifact.content_hash or version.file_size != artifact.file_size:
                raise ValueError("PRODUCTION_ARTIFACTS_REQUIRED")
    eligibility = list(db.scalars(select(ProposalServiceEligibility).where(ProposalServiceEligibility.proposal_id == proposal.id, ProposalServiceEligibility.status == "CURRENT")).all())
    by_code = {row.service_offering_code: row for row in eligibility}
    for code in scope.service_offering_codes:
        if by_code.get(code) is None:
            raise ValueError("SERVICE_ELIGIBILITY_REQUIRED")
        if by_code[code].result != "ELIGIBLE":
            raise ValueError("SERVICE_NOT_ELIGIBLE")
        if production_mode():
            row = by_code[code]
            authority = row.authority_snapshot or {}
            require_current_professional_party(db, row.professional_party_id, office_id=proposal.office_id, service_code=code, discipline=authority.get("discipline"))
            require_proposal_scoped_evidence(db, proposal_id=proposal.id, version_id=row.evidence_document_version_id, source_roles=("SERVICE_ELIGIBILITY", "TECHNICAL_ASSESSMENT"), code="SERVICE_ELIGIBILITY_SCOPE_OR_EVIDENCE_STALE", client_account_id=proposal.client_account_id)
            if row.scope_revision_hash != scope.scope_revision_hash or row.evidence_sha256 != db.get(DocumentVersion, row.evidence_document_version_id).sha256:
                raise ValueError("SERVICE_ELIGIBILITY_SCOPE_OR_EVIDENCE_STALE")
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


def handoff_predicate(db: Session, proposal_id: str) -> dict[str, Any]:
    """Single server-owned Proposal → Contract eligibility predicate."""
    blockers: list[str] = []
    proposal = db.get(Opportunity, proposal_id)
    revision = None
    if not proposal:
        return {"eligible": False, "blockers": ["PROPOSAL_NOT_FOUND"]}
    try:
        revision = latest_accepted(db, proposal_id)
    except ValueError:
        blockers.append("ACCEPTED_REVISION_REQUIRED")
    scope = current_scope(db, proposal_id)
    release = db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.proposal_id == proposal_id, ProposalCommercialRelease.accepted_revision_id == (revision.id if revision else ""), ProposalCommercialRelease.status == "AUTHORIZED")) if revision else None
    if not release:
        blockers.append("COMMERCIAL_RELEASE_REQUIRED")
    if not scope and release:
        blockers.append("SCOPE_CONFIRMATION_REQUIRED")
    active = db.scalar(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id == proposal_id, ProposalStalenessEvent.status == "ACTIVE"))
    if active:
        blockers.append("STALE_PROPOSAL_REVIEW_REQUIRED")
    outputs = list(db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal_id, ProposalOutputArtifact.revision_id == (revision.id if revision else ""))).all()) if revision else []
    if production_mode() and ({item.artifact_type for item in outputs} != {"PROPOSAL", "CHECKLIST"} or any(item.synthetic_only or not item.document_version_id or not item.storage_reference.startswith("storage://") or not item.content_hash or item.file_size <= 0 for item in outputs)):
        blockers.append("PRODUCTION_ARTIFACTS_REQUIRED")
    eligibilities = {item.service_offering_code: item for item in db.scalars(select(ProposalServiceEligibility).where(ProposalServiceEligibility.proposal_id == proposal_id, ProposalServiceEligibility.status == "CURRENT")).all()}
    if scope:
        for code in scope.service_offering_codes:
            row = eligibilities.get(code)
            if not row or row.result != "ELIGIBLE":
                blockers.append("SERVICE_ELIGIBILITY_REQUIRED" if not row else "SERVICE_NOT_ELIGIBLE")
            elif production_mode() and (row.scope_revision_hash and row.scope_revision_hash != scope.scope_revision_hash or not row.evidence_document_version_id or not row.evidence_sha256 or not row.authority_snapshot):
                blockers.append("SERVICE_ELIGIBILITY_SCOPE_OR_EVIDENCE_STALE")
    distribution = db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.proposal_id == proposal_id, ProposalDistributionEvent.accepted_revision_id == (revision.id if revision else "")).order_by(ProposalDistributionEvent.sent_at.desc())) if revision else None
    if not distribution:
        blockers.append("DISTRIBUTION_REQUIRED")
    elif production_mode() and (distribution.delivery_status != "DELIVERED" or not distribution.evidence_document_version_id or not distribution.output_artifact_id or not distribution.output_artifact_hash):
        blockers.append("DISTRIBUTION_EVIDENCE_REQUIRED")
    acceptance = db.scalar(select(ProposalAcceptanceVerification).where(ProposalAcceptanceVerification.proposal_id == proposal_id, ProposalAcceptanceVerification.accepted_revision_id == (revision.id if revision else ""), ProposalAcceptanceVerification.status == "VERIFIED")) if revision else None
    if not acceptance:
        blockers.append("CLIENT_ACCEPTANCE_VERIFICATION_REQUIRED")
    elif production_mode() and (not acceptance.evidence_document_version_id or not acceptance.evidence_sha256):
        blockers.append("CLIENT_ACCEPTANCE_EVIDENCE_REQUIRED")
    lpo = db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.proposal_id == proposal_id, ProposalLpoReconciliation.accepted_revision_id == (revision.id if revision else ""))) if revision else None
    if not lpo or lpo.result not in {"PASS", "NOT_APPLICABLE"}:
        blockers.append("LPO_RECONCILIATION_REQUIRED")
    elif production_mode() and lpo.result == "PASS" and (not lpo.client_document_version_id or not lpo.source_sha256 or not lpo.mapping_version or not lpo.mapper_identity or lpo.accepted_revision_hash != revision.content_hash):
        blockers.append("LPO_PROVENANCE_REQUIRED")
    return {"eligible": not blockers, "blockers": list(dict.fromkeys(blockers)), "accepted_revision_id": revision.id if revision else None, "revision_number": revision.revision_number if revision else None, "content_hash": revision.content_hash if revision else None}


def record_distribution(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalDistributionEvent, bool]:
    proposal = _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal_id)
    release = db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.proposal_id == proposal_id, ProposalCommercialRelease.accepted_revision_id == revision.id, ProposalCommercialRelease.status == "AUTHORIZED"))
    if not release:
        raise ValueError("COMMERCIAL_RELEASE_REQUIRED")
    evidence = str(payload.get("evidence_reference") or "").strip()
    if not evidence:
        raise ValueError("DISTRIBUTION_EVIDENCE_REQUIRED")
    if production_mode():
        reject_synthetic_value(evidence, code="DISTRIBUTION_EVIDENCE_REQUIRED")
        evidence_version = require_proposal_scoped_evidence(db, proposal_id=proposal_id, version_id=payload.get("evidence_document_version_id"), source_roles=("DISTRIBUTION_EVIDENCE", "CLIENT_RESPONSE", "TENDER_DOCUMENT"), code="DISTRIBUTION_EVIDENCE_REQUIRED", client_account_id=proposal.client_account_id)
        artifact = db.get(ProposalOutputArtifact, payload.get("output_artifact_id"))
        if not artifact or artifact.proposal_id != proposal_id or artifact.revision_id != revision.id or artifact.synthetic_only or artifact.content_hash != payload.get("output_artifact_hash"):
            raise ValueError("DISTRIBUTION_OUTPUT_ARTIFACT_REQUIRED")
        output_version = require_exact_document_version(db, artifact.document_version_id, code="DISTRIBUTION_OUTPUT_ARTIFACT_REQUIRED")
        if output_version.sha256 != artifact.content_hash or output_version.file_size != artifact.file_size:
            raise ValueError("DISTRIBUTION_OUTPUT_ARTIFACT_REQUIRED")
        delivery_status = str(payload.get("delivery_status") or "EXTERNAL_EVIDENCE_RECORDED").upper()
        if delivery_status not in {"DELIVERED", "EXTERNAL_EVIDENCE_RECORDED", "FAILED"}:
            raise ValueError("DISTRIBUTION_STATUS_INVALID")
        if delivery_status == "DELIVERED" and not str(payload.get("receipt_reference") or "").strip():
            raise ValueError("DISTRIBUTION_RECEIPT_REQUIRED")
    else:
        delivery_status = str(payload.get("delivery_status") or "EXTERNAL_EVIDENCE_RECORDED").upper()
        evidence_version = None
        artifact = None
    key = str(payload.get("idempotency_key") or f"distribution:{proposal_id}:{revision.id}:{payload.get('channel') or 'UNSPECIFIED'}:{evidence}")
    existing = db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.idempotency_key == key))
    if existing:
        if existing.proposal_id != proposal_id or existing.accepted_revision_id != revision.id:
            raise ValueError("IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        if production_mode() and (payload.get("evidence_document_version_id") or None) != existing.evidence_document_version_id:
            raise ValueError("IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        return existing, True
    row = ProposalDistributionEvent(proposal_id=proposal_id, accepted_revision_id=revision.id, commercial_release_id=release.id, channel=str(payload.get("channel") or "CLIENT_PORTAL"), recipient_party_id=payload.get("recipient_party_id"), recipient_contact_reference=payload.get("recipient_contact_reference"), evidence_document_version_id=evidence_version.id if evidence_version else payload.get("evidence_document_version_id"), evidence_reference=evidence, delivery_status=delivery_status, receipt_reference=payload.get("receipt_reference"), output_artifact_id=artifact.id if artifact else payload.get("output_artifact_id"), output_artifact_hash=artifact.content_hash if artifact else payload.get("output_artifact_hash"), evidence_sha256=evidence_version.sha256 if evidence_version else None, sent_at=_now(), sent_by=actor, audit_correlation_id=correlation_id, idempotency_key=key)
    db.add(row)
    db.flush()
    return row, False


def verify_acceptance(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalAcceptanceVerification, bool]:
    proposal = _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal_id)
    if payload.get("accepted_revision_id") and payload.get("accepted_revision_id") != revision.id:
        raise ValueError("CLIENT_ACCEPTANCE_RESPONSE_REVISION_MISMATCH")
    response = db.get(ProposalClientResponse, payload.get("client_response_id"))
    if not response or response.proposal_id != proposal_id or response.accepted_revision_id != revision.id:
        raise ValueError("CLIENT_ACCEPTANCE_RESPONSE_REVISION_MISMATCH")
    if response.response_type != "ACCEPTED":
        raise ValueError("CLIENT_ACCEPTANCE_RESPONSE_REQUIRED")
    evidence = str(payload.get("evidence_reference") or response.evidence_reference or "").strip()
    if not evidence:
        raise ValueError("CLIENT_ACCEPTANCE_EVIDENCE_REQUIRED")
    evidence_version_id = payload.get("evidence_document_version_id") or response.evidence_document_version_id
    if production_mode():
        require_canonical_active_client(db, proposal.client_account_id)
        evidence_version = require_exact_document_version(db, evidence_version_id, code="CLIENT_ACCEPTANCE_DOCUMENT_VERSION_REQUIRED")
        require_proposal_scoped_evidence(db, proposal_id=proposal_id, version_id=evidence_version.id, source_roles=("CLIENT_ACCEPTANCE", "CLIENT_RESPONSE"), code="CLIENT_ACCEPTANCE_DOCUMENT_VERSION_REQUIRED", client_account_id=proposal.client_account_id)
        if response.evidence_document_version_id and response.evidence_document_version_id != evidence_version.id:
            raise ValueError("CLIENT_ACCEPTANCE_DOCUMENT_VERSION_MISMATCH")
        reject_synthetic_value(evidence, code="CLIENT_ACCEPTANCE_EVIDENCE_REQUIRED")
        evidence_hash = evidence_version.sha256
    else:
        evidence_hash = None
    existing = db.scalar(select(ProposalAcceptanceVerification).where(ProposalAcceptanceVerification.client_response_id == response.id))
    if existing:
        return existing, True
    row = ProposalAcceptanceVerification(proposal_id=proposal_id, accepted_revision_id=revision.id, client_response_id=response.id, evidence_reference=evidence, evidence_document_version_id=evidence_version_id, evidence_sha256=evidence_hash, verified_by=actor, verification_note=payload.get("verification_note"), verified_at=_now(), audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False


def reconcile_lpo(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalLpoReconciliation, bool]:
    _proposal(db, proposal_id)
    revision = latest_accepted(db, proposal_id)
    key = str(payload.get("idempotency_key") or f"lpo:{proposal_id}:{revision.id}")
    existing = db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.idempotency_key == key))
    if existing:
        if existing.proposal_id != proposal_id or existing.accepted_revision_id != revision.id:
            raise ValueError("IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        if production_mode() and payload.get("client_document_version_id") != existing.client_document_version_id:
            raise ValueError("IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        return existing, True
    applies = bool(payload.get("applies", True))
    source_sha256 = None
    mapping_version = None
    mapped_fields: dict[str, Any] = {}
    mapper_identity = None
    mapped_at = None
    if production_mode() and applies:
        version = require_proposal_scoped_evidence(db, proposal_id=proposal_id, version_id=payload.get("client_document_version_id"), source_roles=("LPO_EVIDENCE", "CLIENT_PO"), code="LPO_EVIDENCE_REQUIRED", client_account_id=_proposal(db, proposal_id).client_account_id)
        mapping = (version.metadata_json or {}).get("lpo_mapping")
        if not isinstance(mapping, dict) or mapping.get("source_sha256") != version.sha256 or not mapping.get("mapping_version") or not mapping.get("verified_by") or not isinstance(mapping.get("fields"), dict):
            raise ValueError("LPO_GOVERNED_MAPPING_REQUIRED")
        lpo_fields = mapping["fields"]
        source_sha256 = version.sha256
        mapping_version = str(mapping["mapping_version"])
        mapped_fields = dict(lpo_fields)
        mapper_identity = str(mapping["verified_by"])
        mapped_at = datetime.fromisoformat(str(mapping["mapped_at"]).replace("Z", "+00:00")) if mapping.get("mapped_at") else _now()
        proposal_fields = revision.snapshot.get("fields", {})
        compared = {"amount": proposal_fields.get("price"), "currency": proposal_fields.get("currency"), "scope": proposal_fields.get("scope_of_work") or proposal_fields.get("sow")}
        fields_compared = [field for field in compared if field in lpo_fields]
        if set(fields_compared) != set(compared):
            raise ValueError("LPO_SOURCE_FIELDS_UNRESOLVED")
        variances = [{"field": field, "proposal": compared[field], "lpo": lpo_fields[field]} for field in fields_compared if str(compared[field]).strip() != str(lpo_fields[field]).strip()]
        result = "MISMATCH" if variances else "PASS"
    else:
        variances = payload.get("variances") or []
        if not isinstance(variances, list):
            raise ValueError("LPO_VARIANCES_INVALID")
        if applies and not payload.get("client_artifact_reference") and not payload.get("client_document_version_id"):
            raise ValueError("LPO_EVIDENCE_REQUIRED")
        result = "NOT_APPLICABLE" if not applies else "MISMATCH" if variances else "PASS"
        fields_compared = payload.get("fields_compared") or []
    row = ProposalLpoReconciliation(proposal_id=proposal_id, accepted_revision_id=revision.id, client_document_version_id=payload.get("client_document_version_id"), client_artifact_reference=payload.get("client_artifact_reference"), applies=applies, fields_compared=fields_compared, variances=variances, result=result, comparator_version="SERVER_LPO_COMPARATOR_V1" if production_mode() else "TEST_PAYLOAD_COMPARATOR", source_sha256=source_sha256, mapping_version=mapping_version, mapped_fields=mapped_fields, mapper_identity=mapper_identity, mapped_at=mapped_at, accepted_revision_hash=revision.content_hash, adjudication_note=payload.get("adjudication_note"), adjudicated_by=actor if payload.get("adjudication_note") else None, adjudicated_at=_now() if payload.get("adjudication_note") else None, compared_by=actor, compared_at=_now(), idempotency_key=key, audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False


def create_handoff(db: Session, proposal_id: str, payload: dict[str, Any], *, actor: str, correlation_id: str) -> tuple[ProposalContractHandoff, bool]:
    proposal = _proposal(db, proposal_id)
    predicate = handoff_predicate(db, proposal_id)
    if not predicate["eligible"]:
        raise ValueError(predicate["blockers"][0])
    revision = latest_accepted(db, proposal.id)
    release = db.scalar(select(ProposalCommercialRelease).where(ProposalCommercialRelease.proposal_id == proposal.id, ProposalCommercialRelease.accepted_revision_id == revision.id, ProposalCommercialRelease.status == "AUTHORIZED"))
    if not release:
        raise ValueError("COMMERCIAL_RELEASE_REQUIRED")
    distribution = db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.proposal_id == proposal.id, ProposalDistributionEvent.accepted_revision_id == revision.id))
    if not distribution:
        raise ValueError("DISTRIBUTION_REQUIRED")
    if production_mode() and distribution.delivery_status != "DELIVERED":
        raise ValueError("DISTRIBUTION_DELIVERY_REQUIRED")
    acceptance = db.scalar(select(ProposalAcceptanceVerification).where(ProposalAcceptanceVerification.proposal_id == proposal.id, ProposalAcceptanceVerification.accepted_revision_id == revision.id, ProposalAcceptanceVerification.status == "VERIFIED"))
    if not acceptance:
        raise ValueError("CLIENT_ACCEPTANCE_VERIFICATION_REQUIRED")
    lpo = db.scalar(select(ProposalLpoReconciliation).where(ProposalLpoReconciliation.proposal_id == proposal.id, ProposalLpoReconciliation.accepted_revision_id == revision.id))
    if not lpo:
        raise ValueError("LPO_RECONCILIATION_REQUIRED")
    if lpo.result not in {"PASS", "NOT_APPLICABLE"}:
        raise ValueError("LPO_RECONCILIATION_REQUIRED")
    if production_mode() and lpo.result == "PASS" and not lpo.client_document_version_id:
        raise ValueError("LPO_EVIDENCE_REQUIRED")
    key = str(payload.get("idempotency_key") or f"contract-handoff:{proposal.id}:{revision.id}")
    existing = db.scalar(select(ProposalContractHandoff).where(ProposalContractHandoff.idempotency_key == key))
    if existing:
        return existing, True
    snapshot = revision.snapshot or {}
    row = ProposalContractHandoff(proposal_id=proposal.id, accepted_revision_id=revision.id, acceptance_verification_id=acceptance.id, reconciliation_id=lpo.id, handoff_payload={"proposal_id": proposal.id, "proposal_reference": proposal.opportunity_reference, "client_account_id": proposal.client_account_id, "accepted_scope": snapshot.get("fields", {}).get("scope_of_work") or snapshot.get("fields", {}).get("sow"), "accepted_commercial_basis": snapshot.get("fields", {}), "source_ids": snapshot.get("source_ids", []), "content_lineage": {"content_hash": revision.content_hash, "template_version_id": revision.template_version_id, "checklist_version_id": revision.checklist_version_id}, "acceptance_verification_id": acceptance.id, "lpo_reconciliation_id": lpo.id}, handed_off_by=actor, handed_off_at=_now(), idempotency_key=key, audit_correlation_id=correlation_id)
    db.add(row)
    db.flush()
    return row, False
