"""Governed, citation-preserving preview for one explicit form-preparation action.

This is deliberately a derived read contract.  It does not create a second
retrieval store, invoke an external model, or write FormInstance state.

The target form lineage and value-evidence lineage are intentionally separate.
The target ``DocumentVersion`` is the template pin returned by this module;
it is never substituted for a ``SemanticValueAssertion`` source.  Assertion
sources are resolved by the bounded matrix below.  Unknown source types,
missing source records, cross-project records, historical document versions,
and unsupported structured snapshots fail closed and cannot produce READY.

Supported ``SemanticValueAssertion.source_type`` values (case and separator
insensitive) are:

* document-backed: ``DocumentVersion``, ``Document``, ``FieldObservation``,
  and ``VerifiedAssertion``;
* structured transactional records: ``AuthorityCase``,
  ``AuthorityCaseIdentifier``, and ``Project``.

For document-backed rows, ``source_id`` identifies the exact source record and
``source_version`` is checked when supplied (version id, numeric version
number, or revision label).  For structured rows, only a live/current
snapshot marker is accepted because these records have no version table in
the executable model.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AssertionStatus,
    AuthorityCase,
    AuthorityCaseIdentifier,
    Document,
    DocumentApprovalState,
    DocumentVersion,
    FieldObservation,
    FormAutomationProfile,
    FormMappingRelease,
    FormMappingRule,
    MasterContentGovernanceProfile,
    MasterContentItem,
    SemanticKeyDefinition,
    SemanticValueAssertion,
    Project,
    VerifiedAssertion,
)
from .dashboard_v2_governance import evaluate_automated_readiness, validate_release
from .governed_retrieval import RetrievalQuery, access_context_for_role, governed_retrieve
from .forms_governance import evaluate_readiness


MODEL_ADAPTER = "SYNTHETIC_DETERMINISTIC_ASSIST"


def _stable_id(payload: dict[str, Any]) -> str:
    return "prefill-" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _value_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _source_kind(source_type: str | None) -> str:
    return "".join(character for character in (source_type or "").upper() if character.isalnum())


def _source_version_matches(version: DocumentVersion, source_version: str | None) -> bool:
    if not source_version:
        return True
    candidate = str(source_version)
    return candidate in {version.id, str(version.version_number), version.revision_label or ""}


def _document_citation(
    assertion: SemanticValueAssertion,
    version: DocumentVersion,
    *,
    locator_type: str,
    locator: str,
    verification_state: str,
    supporting_entity_type: str,
    supporting_entity_id: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document = version.document
    citation = {
        "canonical_domain": "TRANSACTIONAL_EVIDENCE",
        "canonical_entity_type": supporting_entity_type,
        "canonical_entity_id": supporting_entity_id,
        "document_id": document.id,
        "document_version_id": version.id,
        "locator_type": locator_type,
        "locator": locator,
        "source_hash": version.sha256,
        "source_type": assertion.source_type,
        "source_id": assertion.source_id,
        "source_version": assertion.source_version or version.id,
        "verification_state": verification_state,
        "evidence_identity": assertion.id,
    }
    if extra:
        citation.update(extra)
    return citation


def _structured_citation(
    assertion: SemanticValueAssertion,
    *,
    source_type: str,
    source_id: str,
    verification_state: str,
) -> dict[str, Any]:
    return {
        "canonical_domain": "TRANSACTIONAL_EVIDENCE",
        "canonical_entity_type": source_type,
        "canonical_entity_id": source_id,
        "document_id": None,
        "document_version_id": None,
        "locator_type": "STRUCTURED_RECORD",
        "locator": f"{source_type}:{source_id}",
        "source_hash": None,
        "source_type": assertion.source_type,
        "source_id": assertion.source_id,
        "source_version": assertion.source_version or "CURRENT",
        "verification_state": verification_state,
        "evidence_identity": assertion.id,
        "snapshot_or_as_of": assertion.source_version or "CURRENT",
    }


def _resolve_assertion_source(
    db: Session,
    assertion: SemanticValueAssertion,
    *,
    project_id: str,
    case_id: str,
) -> dict[str, Any]:
    """Resolve one assertion to its actual supporting source, never the form.

    The returned ``citation`` is absent for an unresolvable row.  This helper
    reads source metadata only; it does not read source content or broaden
    the governed retrieval boundary.
    """
    kind = _source_kind(assertion.source_type)
    source_id = assertion.source_id
    if not source_id:
        return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}

    verification_state = "VERIFIED" if assertion.verification_status == "VERIFIED" else "UNVERIFIED"
    document_kinds = {"DOCUMENTVERSION", "DOCUMENT", "FIELDOBSERVATION", "VERIFIEDASSERTION"}
    if kind in document_kinds:
        observation: FieldObservation | None = None
        verified_assertion: VerifiedAssertion | None = None
        if kind == "DOCUMENTVERSION":
            version = db.get(DocumentVersion, source_id)
            supporting_type = "DocumentVersion"
            supporting_id = source_id
            locator_type = "DOCUMENT_VERSION"
            locator = f"DocumentVersion:{source_id}"
        elif kind == "DOCUMENT":
            document = db.get(Document, source_id)
            version = db.get(DocumentVersion, document.current_version_id) if document and document.current_version_id else None
            supporting_type = "DocumentVersion"
            supporting_id = version.id if version else source_id
            locator_type = "DOCUMENT_VERSION"
            locator = f"Document:{source_id}:current"
        elif kind == "FIELDOBSERVATION":
            observation = db.get(FieldObservation, source_id)
            version = db.get(DocumentVersion, observation.document_version_id) if observation else None
            supporting_type = "FieldObservation"
            supporting_id = source_id
            locator_type = "FIELD_OBSERVATION"
            locator = f"FieldObservation:{source_id}"
        else:
            verified_assertion = db.get(VerifiedAssertion, source_id)
            observation = db.get(FieldObservation, verified_assertion.source_observation_id) if verified_assertion and verified_assertion.source_observation_id else None
            version = db.get(DocumentVersion, observation.document_version_id) if observation else None
            supporting_type = "FieldObservation"
            supporting_id = observation.id if observation else source_id
            locator_type = "FIELD_OBSERVATION"
            locator = f"VerifiedAssertion:{source_id}:observation:{observation.id}" if observation else f"VerifiedAssertion:{source_id}"

        document = db.get(Document, version.document_id) if version else None
        if not version or not document:
            return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
        if document.project_id != project_id or document.current_version_id != version.id:
            return {"resolved": False, "reason": "STALE_OR_CROSS_PROJECT_PROVENANCE"}
        if version.approval_state in {DocumentApprovalState.WORKING, DocumentApprovalState.SUPERSEDED} or not version.sha256:
            return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
        if not _source_version_matches(version, assertion.source_version):
            return {"resolved": False, "reason": "SOURCE_VERSION_MISMATCH"}
        if observation and observation.project_id != project_id:
            return {"resolved": False, "reason": "CROSS_PROJECT_PROVENANCE"}
        if verified_assertion and (verified_assertion.project_id != project_id or verified_assertion.status != AssertionStatus.CURRENT):
            return {"resolved": False, "reason": "STALE_OR_CROSS_PROJECT_PROVENANCE"}
        extra: dict[str, Any] = {}
        if observation:
            extra["page_number"] = observation.page_number
            extra["bounding_box"] = observation.bounding_box_json
            extra["source_region"] = observation.source_region_text
        if verified_assertion:
            extra["verified_assertion_id"] = verified_assertion.id
        return {
            "resolved": True,
            "citation": _document_citation(
                assertion,
                version,
                locator_type=locator_type,
                locator=locator,
                verification_state=verification_state,
                supporting_entity_type=supporting_type,
                supporting_entity_id=supporting_id,
                extra=extra,
            ),
        }

    structured_kinds = {
        "AUTHORITYCASE": (AuthorityCase, "AuthorityCase"),
        "AUTHORITYCASEIDENTIFIER": (AuthorityCaseIdentifier, "AuthorityCaseIdentifier"),
        "PROJECT": (Project, "Project"),
    }
    if kind in structured_kinds:
        model, entity_type = structured_kinds[kind]
        record = db.get(model, source_id)
        if not record:
            return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}
        if kind == "AUTHORITYCASE" and record.id != case_id:
            return {"resolved": False, "reason": "CROSS_CONTEXT_PROVENANCE"}
        if kind == "AUTHORITYCASEIDENTIFIER" and (record.authority_case_id != case_id or not record.active):
            return {"resolved": False, "reason": "CROSS_CONTEXT_PROVENANCE"}
        if kind == "PROJECT" and record.id != project_id:
            return {"resolved": False, "reason": "CROSS_PROJECT_PROVENANCE"}
        if assertion.source_version and str(assertion.source_version).upper() not in {"CURRENT", "LIVE"}:
            return {"resolved": False, "reason": "UNSUPPORTED_STRUCTURED_SNAPSHOT"}
        return {
            "resolved": True,
            "citation": _structured_citation(
                assertion,
                source_type=entity_type,
                source_id=record.id,
                verification_state=verification_state,
            ),
        }
    return {"resolved": False, "reason": "UNSUPPORTED_PROVENANCE"}


def _field(
    db: Session,
    rule: FormMappingRule,
    key: SemanticKeyDefinition | None,
    assertions: list[SemanticValueAssertion],
    *,
    project_id: str,
    case_id: str,
) -> dict[str, Any]:
    verified = [row for row in assertions if row.verification_status == "VERIFIED"]
    unverified = [row for row in assertions if row.verification_status != "VERIFIED"]
    distinct = {_value_key(row.value_json) for row in verified}
    resolved = {row.id: _resolve_assertion_source(db, row, project_id=project_id, case_id=case_id) for row in assertions}
    sources = [result["citation"] for row in assertions if (result := resolved[row.id]).get("resolved")]
    unresolved_verified = [row for row in verified if not resolved[row.id].get("resolved")]
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
    if unresolved_verified:
        base.update(
            proposal_status="REVIEW_REQUIRED",
            authority_state="UNSUPPORTED_PROVENANCE",
            proposed_value=None,
            provenance=[],
            warning="A verified candidate has no resolvable, current, project-scoped supporting source.",
        )
    elif len(distinct) > 1:
        base.update(proposal_status="CONFLICT", authority_state="CONFLICT", warning="Conflicting verified candidates require human selection.")
    elif verified:
        chosen = verified[0]
        provenance = [resolved[row.id]["citation"] for row in verified]
        base.update(proposed_value=chosen.value_json, proposal_status="READY", authority_state="VERIFIED", provenance=provenance)
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
        fields.append(
            _field(
                db,
                rule,
                keys.get(rule.logical_field_key),
                assertions,
                project_id=project_id,
                case_id=case_id,
            )
        )
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
