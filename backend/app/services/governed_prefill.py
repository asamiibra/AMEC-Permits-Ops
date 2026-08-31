"""Governed, citation-preserving preview for one explicit form-preparation action.

This is deliberately a derived read contract.  It does not create a second
retrieval store, invoke an external model, or write FormInstance state.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    FormAutomationProfile,
    FormMappingRelease,
    FormMappingRule,
    MasterContentGovernanceProfile,
    MasterContentItem,
    SemanticKeyDefinition,
    SemanticValueAssertion,
)
from .dashboard_v2_governance import evaluate_automated_readiness, validate_release
from .governed_retrieval import RetrievalQuery, access_context_for_role, governed_retrieve
from .forms_governance import evaluate_readiness


MODEL_ADAPTER = "SYNTHETIC_DETERMINISTIC_ASSIST"


def _stable_id(payload: dict[str, Any]) -> str:
    return "prefill-" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _value_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _citation(assertion: SemanticValueAssertion, *, version_id: str, source_hash: str | None) -> dict[str, Any]:
    return {
        "canonical_domain": "FORM_PREPARATION",
        "canonical_entity_type": "SemanticValueAssertion",
        "canonical_entity_id": assertion.id,
        "document_version_id": version_id,
        "locator_type": "SEMANTIC_ASSERTION",
        "locator": f"SemanticValueAssertion:{assertion.id}",
        "source_hash": source_hash,
        "source_type": assertion.source_type,
        "source_id": assertion.source_id,
    }


def _field(rule: FormMappingRule, key: SemanticKeyDefinition | None, assertions: list[SemanticValueAssertion], *, version_id: str, source_hash: str | None) -> dict[str, Any]:
    verified = [row for row in assertions if row.verification_status == "VERIFIED"]
    unverified = [row for row in assertions if row.verification_status != "VERIFIED"]
    distinct = {_value_key(row.value_json) for row in verified}
    sources = [_citation(row, version_id=version_id, source_hash=source_hash) for row in assertions]
    base = {
        "target_field": rule.target_key,
        "logical_field_key": rule.logical_field_key,
        "mapping_rule_id": rule.id,
        "display_label": key.description if key and key.description else rule.target_key,
        "value_type": key.value_type if key else None,
        "proposed_value": None,
        "proposal_status": "MISSING",
        "authority_state": "MISSING",
        "provenance": [],
        "citations": sources,
        "warning": None,
    }
    if len(distinct) > 1:
        base.update(proposal_status="CONFLICT", authority_state="CONFLICT", warning="Conflicting verified candidates require human selection.")
    elif verified:
        chosen = verified[0]
        base.update(proposed_value=chosen.value_json, proposal_status="READY", authority_state="VERIFIED", provenance=[_citation(chosen, version_id=version_id, source_hash=source_hash)])
    elif unverified:
        base.update(proposal_status="REVIEW_REQUIRED", authority_state="UNVERIFIED", warning="A source value exists but is not verified; it cannot be prefilled.")
    return base


def preview_prefill(
    db: Session,
    *,
    role: Any,
    caller_id: str,
    project_id: str,
    case_id: str,
    master_content_id: str,
    purpose: str,
    expected_document_version_id: str | None = None,
    expected_mapping_release_id: str | None = None,
) -> dict[str, Any]:
    """Build a bounded preview after the caller has already passed case access."""
    item = db.get(MasterContentItem, master_content_id)
    if not item or item.content_type != "FORM":
        raise ValueError("PREFILL_MASTER_FORM_NOT_FOUND")
    current_version_id = item.current_document_version_id
    profile = db.scalar(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item.id))
    release = None
    if profile:
        release = db.scalar(select(FormMappingRelease).where(FormMappingRelease.profile_id == profile.id, FormMappingRelease.status == "RELEASED").order_by(FormMappingRelease.released_at.desc()))
    pin_payload = {"case_id": case_id, "project_id": project_id, "master_content_id": item.id, "document_version_id": current_version_id, "mapping_release_id": release.id if release else None, "purpose": purpose}
    preview_id = _stable_id(pin_payload)

    stale = bool(
        (expected_document_version_id and expected_document_version_id != current_version_id)
        or (expected_mapping_release_id and (not release or expected_mapping_release_id != release.id))
    )
    if stale:
        return {
            "preview_id": preview_id, "preview_status": "STALE", "staleness_state": "STALE", "context_entity_type": "AuthorityCase", "context_entity_id": case_id,
            "master_content_id": item.id, "master_content_ref": item.ref, "document_version_id": current_version_id, "mapping_release_id": release.id if release else None,
            "automation_profile_id": profile.id if profile else None, "purpose": purpose, "fields": [], "warnings": ["The source or mapping pin changed; review a fresh preview."],
            "model_adapter": MODEL_ADAPTER, "model_can_expand_authority": False, "canonical_write_count": 0, "protected_human_action_count": 0,
            "retrieval_evidence": [], "source_prompt_injection_authority_gain": False, "draft_apply": "DEFERRED_EXISTING_SAFE_COMMAND_ABSENT",
            "master_content_version_pin": {"master_content_id": item.id, "document_version_id": current_version_id}, "mapping_release_pin": release.id if release else None,
            "transaction_context_boundary": {"entity_type": "AuthorityCase", "entity_id": case_id, "project_id": project_id, "purpose": purpose},
        }

    if not current_version_id or not profile or not release or release.status != "RELEASED":
        raise ValueError("PREFILL_FORM_MAPPING_NOT_ELIGIBLE")
    if item.status != "ACTIVE" or item.needs_review:
        raise ValueError("PREFILL_MASTER_NOT_CURRENT_OR_NEEDS_REVIEW")
    governance = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
    if governance and governance.restricted_reference_sample:
        raise ValueError("PREFILL_RESTRICTED_REFERENCE_SAMPLE")
    wave_a = evaluate_readiness(db, item, persist=False)
    if wave_a["state"] != "MANUAL_USE_READY" or wave_a["blocking_reasons"]:
        raise ValueError("PREFILL_MASTER_GOVERNANCE_BLOCKED")
    automation = evaluate_automated_readiness(db, profile, actor=caller_id, persist=False)
    if automation["state"] != "AUTOMATED_USE_READY":
        raise ValueError("PREFILL_AUTOMATION_NOT_READY")
    validation = validate_release(db, release)
    if not validation["valid"] or release.mapping_checksum != validation["mapping_checksum"]:
        raise ValueError("PREFILL_MAPPING_INVALID")

    # Authorization and purpose are already bound to the AuthorityCase.  The
    # shared retrieval boundary is still invoked for the exact canonical form;
    # its source content is reduced to IDs/citations below and never sent to a
    # model or returned as an untyped answer.
    retrieval = governed_retrieve(
        db,
        RetrievalQuery(master_content_id=item.id, document_version_id=current_version_id, limit=1),
        access_context_for_role(role, caller_id=caller_id, project_ids=(project_id,), purpose=purpose),
    )
    if not retrieval:
        raise ValueError("PREFILL_RETRIEVAL_NOT_AUTHORIZED")
    retrieval_evidence = [{"canonical_entity_id": row.envelope.canonical_entity_id, "document_version_id": row.envelope.document_version_id, "citation": row.envelope.citation.model_dump()} for row in retrieval]
    rules = list(db.scalars(select(FormMappingRule).where(FormMappingRule.mapping_release_id == release.id).order_by(FormMappingRule.id)).all())
    key_rows = list(db.scalars(select(SemanticKeyDefinition).where(SemanticKeyDefinition.semantic_key.in_([row.logical_field_key for row in rules]))).all())
    keys = {row.semantic_key: row for row in key_rows}
    fields = []
    for rule in rules:
        assertions = list(db.scalars(select(SemanticValueAssertion).where(SemanticValueAssertion.semantic_key_id == keys[rule.logical_field_key].id, SemanticValueAssertion.context_type == "AuthorityCase", SemanticValueAssertion.context_id == case_id).order_by(SemanticValueAssertion.created_at)).all()) if rule.logical_field_key in keys else []
        fields.append(_field(rule, keys.get(rule.logical_field_key), assertions, version_id=current_version_id, source_hash=retrieval[0].envelope.citation.source_hash))
    status = "READY" if fields and all(row["proposal_status"] == "READY" for row in fields) else "REVIEW_REQUIRED"
    return {
        "preview_id": preview_id, "preview_status": status, "staleness_state": "CURRENT", "context_entity_type": "AuthorityCase", "context_entity_id": case_id,
        "master_content_id": item.id, "master_content_ref": item.ref, "document_version_id": current_version_id, "mapping_release_id": release.id, "automation_profile_id": profile.id,
        "purpose": purpose, "fields": fields, "warnings": [], "model_adapter": MODEL_ADAPTER, "model_can_expand_authority": False,
        "canonical_write_count": 0, "protected_human_action_count": 0, "retrieval_evidence": retrieval_evidence, "source_prompt_injection_authority_gain": False,
        "draft_apply": "DEFERRED_EXISTING_SAFE_COMMAND_ABSENT", "master_content_version_pin": {"master_content_id": item.id, "document_version_id": current_version_id}, "mapping_release_pin": release.id,
        "transaction_context_boundary": {"entity_type": "AuthorityCase", "entity_id": case_id, "project_id": project_id, "purpose": purpose},
        "field_level_provenance": {field["target_field"]: field["provenance"] for field in fields}, "field_level_citations": {field["target_field"]: field["citations"] for field in fields},
    }
