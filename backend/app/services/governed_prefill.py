"""Governed, citation-preserving preview for explicit form preparation.

This is a derived read contract. It never writes FormInstance state and keeps
the template DocumentVersion pin separate from value-evidence provenance.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (AssertionStatus, AuthorityCase, AuthorityCaseIdentifier,
    DefinitionRevision, Document, DocumentApprovalState, DocumentVersion,
    FieldObservation, FormAutomationProfile, FormMappingRelease, FormMappingRule,
    MasterContentGovernanceProfile, MasterContentItem, Project,
    SemanticKeyDefinition, SemanticValueAssertion, VerifiedAssertion, Role)
from .dashboard_v2_governance import evaluate_automated_readiness, validate_release
from .forms_governance import evaluate_readiness
from .governed_retrieval import RetrievalQuery, access_context_for_role, governed_retrieve

MODEL_ADAPTER = "SYNTHETIC_DETERMINISTIC_ASSIST"

def _stable_id(payload):
    return "prefill-" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]

def _value_key(value):
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))

def _source_kind(source_type):
    return "".join(c for c in (source_type or "").upper() if c.isalnum())

def _source_version_matches(version, source_version):
    return not source_version or str(source_version) in {version.id, str(version.version_number), version.revision_label or ""}

def _document_citation(assertion, version, *, locator_type, locator, verification_state, supporting_entity_type, supporting_entity_id, extra=None):
    citation = {"canonical_domain": "TRANSACTIONAL_EVIDENCE", "canonical_entity_type": supporting_entity_type, "canonical_entity_id": supporting_entity_id, "document_id": version.document.id, "document_version_id": version.id, "locator_type": locator_type, "locator": locator, "source_hash": version.sha256, "source_type": assertion.source_type, "source_id": assertion.source_id, "source_version": assertion.source_version or version.id, "verification_state": verification_state, "evidence_identity": assertion.id}
    if extra: citation.update(extra)
    return citation

def _structured_citation(assertion, *, source_type, source_id, verification_state):
    return {"canonical_domain": "TRANSACTIONAL_EVIDENCE", "canonical_entity_type": source_type, "canonical_entity_id": source_id, "document_id": None, "document_version_id": None, "locator_type": "STRUCTURED_RECORD", "locator": f"{source_type}:{source_id}", "source_hash": None, "source_type": assertion.source_type, "source_id": assertion.source_id, "source_version": assertion.source_version or "CURRENT", "verification_state": verification_state, "evidence_identity": assertion.id, "snapshot_or_as_of": assertion.source_version or "CURRENT"}

def _resolve_assertion_source(db: Session, assertion: SemanticValueAssertion, *, project_id, case_id):
    kind, source_id = _source_kind(assertion.source_type), assertion.source_id
    if not source_id: return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
    state = "VERIFIED" if assertion.verification_status == "VERIFIED" else "UNVERIFIED"
    if kind in {"DOCUMENTVERSION", "DOCUMENT", "FIELDOBSERVATION", "VERIFIEDASSERTION"}:
        observation = verified = None
        if kind == "DOCUMENTVERSION": version, supporting_type, supporting_id, locator_type, locator = db.get(DocumentVersion, source_id), "DocumentVersion", source_id, "DOCUMENT_VERSION", f"DocumentVersion:{source_id}"
        elif kind == "DOCUMENT":
            document = db.get(Document, source_id); version = db.get(DocumentVersion, document.current_version_id) if document and document.current_version_id else None; supporting_type, supporting_id, locator_type, locator = "DocumentVersion", version.id if version else source_id, "DOCUMENT_VERSION", f"Document:{source_id}:current"
        elif kind == "FIELDOBSERVATION":
            observation = db.get(FieldObservation, source_id); version = db.get(DocumentVersion, observation.document_version_id) if observation else None; supporting_type, supporting_id, locator_type, locator = "FieldObservation", source_id, "FIELD_OBSERVATION", f"FieldObservation:{source_id}"
        else:
            verified = db.get(VerifiedAssertion, source_id); observation = db.get(FieldObservation, verified.source_observation_id) if verified and verified.source_observation_id else None; version = db.get(DocumentVersion, observation.document_version_id) if observation else None; supporting_type, supporting_id, locator_type, locator = "FieldObservation", observation.id if observation else source_id, "FIELD_OBSERVATION", f"VerifiedAssertion:{source_id}:observation:{observation.id}" if observation else f"VerifiedAssertion:{source_id}"
        document = db.get(Document, version.document_id) if version else None
        if not version or not document: return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
        if document.project_id != project_id or document.current_version_id != version.id: return {"resolved": False, "reason": "STALE_OR_CROSS_PROJECT_PROVENANCE"}
        if version.approval_state in {DocumentApprovalState.WORKING, DocumentApprovalState.SUPERSEDED} or not version.sha256: return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
        if not _source_version_matches(version, assertion.source_version): return {"resolved": False, "reason": "SOURCE_VERSION_MISMATCH"}
        if observation and observation.project_id != project_id: return {"resolved": False, "reason": "CROSS_PROJECT_PROVENANCE"}
        if verified and (verified.project_id != project_id or verified.status != AssertionStatus.CURRENT): return {"resolved": False, "reason": "STALE_OR_CROSS_PROJECT_PROVENANCE"}
        extra = {"page_number": observation.page_number, "bounding_box": observation.bounding_box_json, "source_region": observation.source_region_text} if observation else {}
        if verified: extra["verified_assertion_id"] = verified.id
        return {"resolved": True, "citation": _document_citation(assertion, version, locator_type=locator_type, locator=locator, verification_state=state, supporting_entity_type=supporting_type, supporting_entity_id=supporting_id, extra=extra)}
    structured = {"AUTHORITYCASE": (AuthorityCase, "AuthorityCase"), "AUTHORITYCASEIDENTIFIER": (AuthorityCaseIdentifier, "AuthorityCaseIdentifier"), "PROJECT": (Project, "Project")}
    if kind in structured:
        model, entity_type = structured[kind]; record = db.get(model, source_id)
        if not record: return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
        if kind == "AUTHORITYCASE" and record.id != case_id: return {"resolved": False, "reason": "CROSS_CONTEXT_PROVENANCE"}
        if kind == "AUTHORITYCASEIDENTIFIER" and (record.authority_case_id != case_id or not record.active): return {"resolved": False, "reason": "CROSS_CONTEXT_PROVENANCE"}
        if kind == "PROJECT" and record.id != project_id: return {"resolved": False, "reason": "CROSS_PROJECT_PROVENANCE"}
        if assertion.source_version and str(assertion.source_version).upper() not in {"CURRENT", "LIVE"}: return {"resolved": False, "reason": "UNSUPPORTED_STRUCTURED_SNAPSHOT"}
        return {"resolved": True, "citation": _structured_citation(assertion, source_type=entity_type, source_id=record.id, verification_state=state)}
    return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}

def _field(db, rule, key, assertions, *, project_id, case_id):
    verified = [row for row in assertions if row.verification_status == "VERIFIED"]; unverified = [row for row in assertions if row.verification_status != "VERIFIED"]
    distinct = {_value_key(row.value_json) for row in verified}; resolved = {row.id: _resolve_assertion_source(db, row, project_id=project_id, case_id=case_id) for row in assertions}
    sources = [resolved[row.id]["citation"] for row in assertions if resolved[row.id].get("resolved")]; unresolved = [row for row in verified if not resolved[row.id].get("resolved")]
    base = {"target_field": rule.target_key, "logical_field_key": rule.logical_field_key, "mapping_rule_id": rule.id, "display_label": key.description if key and key.description else rule.target_key, "value_type": key.value_type if key else None, "proposed_value": None, "proposal_status": "MISSING", "authority_state": "MISSING", "provenance": [], "citations": sources, "warning": None}
    if unresolved: base.update(proposal_status="REVIEW_REQUIRED", authority_state="UNSUPPORTED_PROVENANCE", warning="A verified candidate has no resolvable, current, project-scoped supporting source.")
    elif len(distinct) > 1: base.update(proposal_status="CONFLICT", authority_state="CONFLICT", warning="Conflicting verified candidates require human selection.")
    elif verified: base.update(proposed_value=verified[0].value_json, proposal_status="READY", authority_state="VERIFIED", provenance=[resolved[row.id]["citation"] for row in verified])
    elif unverified: base.update(proposal_status="REVIEW_REQUIRED", authority_state="UNVERIFIED", warning="A source value exists but is not verified; it cannot be prefilled.")
    return base

def preview_prefill(db: Session, *, role, caller_id, project_id, case_id, master_content_id, purpose, expected_document_version_id=None, expected_mapping_release_id=None):
    if str(getattr(role, "value", role)) not in {Role.OWNER_SPONSOR.value, Role.SYSTEM_ADMIN.value, Role.PERMIT_PREPARER.value} or purpose.strip().upper() != "FORM_PREPARATION":
        raise ValueError("PREFILL_PURPOSE_NOT_ALLOWED")
    item = db.get(MasterContentItem, master_content_id)
    if not item or item.content_type != "FORM": raise ValueError("PREFILL_MASTER_FORM_NOT_FOUND")
    current_version_id = item.current_document_version_id; profile = db.scalar(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item.id)); release = db.scalar(select(FormMappingRelease).where(FormMappingRelease.profile_id == profile.id, FormMappingRelease.status == "RELEASED").order_by(FormMappingRelease.released_at.desc())) if profile else None
    pin = {"case_id": case_id, "project_id": project_id, "master_content_id": item.id, "document_version_id": current_version_id, "mapping_release_id": release.id if release else None, "purpose": purpose}; preview_id = _stable_id(pin)
    stale = (expected_document_version_id and expected_document_version_id != current_version_id) or (expected_mapping_release_id and (not release or expected_mapping_release_id != release.id))
    if stale: return {"preview_id": preview_id, "preview_status": "STALE", "staleness_state": "STALE", "context_entity_type": "AuthorityCase", "context_entity_id": case_id, "master_content_id": item.id, "master_content_ref": item.ref, "document_version_id": current_version_id, "mapping_release_id": release.id if release else None, "automation_profile_id": profile.id if profile else None, "purpose": purpose, "fields": [], "warnings": ["The source or mapping pin changed; review a fresh preview."], "model_adapter": MODEL_ADAPTER, "model_can_expand_authority": False, "canonical_write_count": 0, "protected_human_action_count": 0, "retrieval_evidence": [], "source_prompt_injection_authority_gain": False, "draft_apply": "DEFERRED_EXISTING_SAFE_COMMAND_ABSENT", "master_content_version_pin": {"master_content_id": item.id, "document_version_id": current_version_id}, "mapping_release_pin": release.id if release else None, "transaction_context_boundary": {"entity_type": "AuthorityCase", "entity_id": case_id, "project_id": project_id, "purpose": purpose}}
    if not current_version_id or not profile or not release: raise ValueError("PREFILL_FORM_MAPPING_NOT_ELIGIBLE")
    if item.status != "ACTIVE" or item.needs_review: raise ValueError("PREFILL_MASTER_NOT_CURRENT_OR_NEEDS_REVIEW")
    governance = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
    if governance and governance.restricted_reference_sample: raise ValueError("PREFILL_RESTRICTED_REFERENCE_SAMPLE")
    if evaluate_readiness(db, item, persist=False)["state"] != "MANUAL_USE_READY": raise ValueError("PREFILL_MASTER_GOVERNANCE_BLOCKED")
    if evaluate_automated_readiness(db, profile, actor=caller_id, persist=False)["state"] != "AUTOMATED_USE_READY": raise ValueError("PREFILL_AUTOMATION_NOT_READY")
    validation = validate_release(db, release)
    if not validation["valid"] or release.mapping_checksum != validation["mapping_checksum"]: raise ValueError("PREFILL_MAPPING_INVALID")
    retrieval = governed_retrieve(db, RetrievalQuery(master_content_id=item.id, document_version_id=current_version_id, limit=1), access_context_for_role(role, caller_id=caller_id, project_ids=(project_id,), purpose=purpose))
    if not retrieval: raise ValueError("PREFILL_RETRIEVAL_NOT_AUTHORIZED")
    evidence = [{"canonical_entity_id": row.envelope.canonical_entity_id, "document_version_id": row.envelope.document_version_id, "citation": row.envelope.citation.model_dump()} for row in retrieval]
    rules = list(db.scalars(select(FormMappingRule).where(FormMappingRule.mapping_release_id == release.id).order_by(FormMappingRule.id)).all()); keys = {row.semantic_key: row for row in db.scalars(select(SemanticKeyDefinition).where(SemanticKeyDefinition.semantic_key.in_([r.logical_field_key for r in rules]))).all()}; fields = []
    for rule in rules:
        key = keys.get(rule.logical_field_key); assertions = list(db.scalars(select(SemanticValueAssertion).where(SemanticValueAssertion.semantic_key_id == key.id, SemanticValueAssertion.context_type == "AuthorityCase", SemanticValueAssertion.context_id == case_id).order_by(SemanticValueAssertion.created_at)).all()) if key else []
        fields.append(_field(db, rule, key, assertions, project_id=project_id, case_id=case_id))
    status = "READY" if fields and all(field["proposal_status"] == "READY" for field in fields) else "REVIEW_REQUIRED"
    return {"preview_id": preview_id, "preview_status": status, "staleness_state": "CURRENT", "context_entity_type": "AuthorityCase", "context_entity_id": case_id, "master_content_id": item.id, "master_content_ref": item.ref, "document_version_id": current_version_id, "mapping_release_id": release.id, "automation_profile_id": profile.id, "purpose": purpose, "fields": fields, "warnings": [], "model_adapter": MODEL_ADAPTER, "model_can_expand_authority": False, "canonical_write_count": 0, "protected_human_action_count": 0, "retrieval_evidence": evidence, "source_prompt_injection_authority_gain": False, "draft_apply": "DEFERRED_EXISTING_SAFE_COMMAND_ABSENT", "master_content_version_pin": {"master_content_id": item.id, "document_version_id": current_version_id}, "mapping_release_pin": release.id, "transaction_context_boundary": {"entity_type": "AuthorityCase", "entity_id": case_id, "project_id": project_id, "purpose": purpose}, "field_level_provenance": {f["target_field"]: f["provenance"] for f in fields}, "field_level_citations": {f["target_field"]: f["citations"] for f in fields}}
