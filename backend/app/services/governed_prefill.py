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
number, or revision label).  For structured rows, the exact source record is
required.  An opaque source-version/snapshot marker is retained when
supplied; the resolver does not pretend that the executable model can prove
freshness for that marker because these records have no version table.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AssertionStatus,
    AuthorityCase,
    AuthorityCaseIdentifier,
    Document,
    DocumentApprovalState,
    DocumentVersion,
    FormInstance,
    FormInstanceApply,
    FieldObservation,
    FormAutomationProfile,
    FormMappingRelease,
    FormMappingRule,
    MasterContentGovernanceProfile,
    MasterContentItem,
    SemanticKeyDefinition,
    SemanticValueAssertion,
    Project,
    RegulatoryJourney,
    VerifiedAssertion,
)
from .dashboard_v2_governance import evaluate_automated_readiness, validate_release
from .governed_retrieval import RetrievalQuery, access_context_for_role, governed_retrieve
from .forms_governance import evaluate_readiness


MODEL_ADAPTER = "SYNTHETIC_DETERMINISTIC_ASSIST"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stable_id(payload: dict[str, Any]) -> str:
    return "prefill-" + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]


def _value_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_value_key(payload).encode()).hexdigest()


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
    snapshot = assertion.source_version or "CURRENT"
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
        "source_version": snapshot,
        "verification_state": verification_state,
        "evidence_identity": assertion.id,
        "snapshot_or_as_of": snapshot,
        "structured_currentness_state": "CURRENT_MARKER" if snapshot.upper() in {"CURRENT", "LIVE"} else "NOT_REPRESENTED",
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
    form_instance_id: str | None = None,
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

    draft = db.get(FormInstance, form_instance_id) if form_instance_id else None
    if form_instance_id and (
        not draft
        or draft.context_type != "AuthorityCase"
        or draft.context_id != case_id
        or draft.master_content_item_id != item.id
        or draft.source_document_version_id != current_version_id
        or draft.profile_id != profile.id
        or draft.mapping_release_id != release.id
        or draft.status != "DRAFT"
    ):
        raise ValueError("PREFILL_DRAFT_NOT_EDITABLE_OR_PIN_MISMATCH")

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
    material_fields = [
        {
            "target_field": field["target_field"],
            "logical_field_key": field["logical_field_key"],
            "mapping_rule_id": field["mapping_rule_id"],
            "proposed_value": field["proposed_value"],
            "proposal_status": field["proposal_status"],
            "authority_state": field["authority_state"],
            "provenance": field["provenance"],
            "citations": field["citations"],
        }
        for field in fields
    ]
    preview_fingerprint = _fingerprint(
        {
            "contract": "governed-prefill-preview-v4",
            "form_instance_id": form_instance_id,
            "draft_revision": draft.draft_revision if draft else None,
            "master_content_id": item.id,
            "target_document_version_id": current_version_id,
            "mapping_release_id": release.id,
            "mapping_release_version": release.version,
            "mapping_checksum": release.mapping_checksum,
            "project_id": project_id,
            "case_id": case_id,
            "purpose": purpose,
            "fields": material_fields,
        }
    )
    return {
        "preview_id": preview_id, "preview_status": status, "staleness_state": "CURRENT", "context_entity_type": "AuthorityCase", "context_entity_id": case_id,
        "master_content_id": item.id, "master_content_ref": item.ref, "document_version_id": current_version_id, "mapping_release_id": release.id, "automation_profile_id": profile.id,
        "form_instance_id": form_instance_id, "draft_revision": draft.draft_revision if draft else None, "preview_fingerprint": preview_fingerprint,
        "purpose": purpose, "fields": fields, "warnings": [], "model_adapter": MODEL_ADAPTER, "model_can_expand_authority": False,
        "canonical_write_count": 0, "protected_human_action_count": 0, "retrieval_evidence": retrieval_evidence, "source_prompt_injection_authority_gain": False,
        "draft_apply": "DEFERRED_EXISTING_SAFE_COMMAND_ABSENT", "master_content_version_pin": {"master_content_id": item.id, "document_version_id": current_version_id}, "mapping_release_pin": release.id, "mapping_release_version": release.version, "mapping_checksum": release.mapping_checksum,
        "transaction_context_boundary": {"entity_type": "AuthorityCase", "entity_id": case_id, "project_id": project_id, "purpose": purpose},
        "field_level_provenance": {field["target_field"]: field["provenance"] for field in fields}, "field_level_citations": {field["target_field"]: field["citations"] for field in fields},
    }


def _draft_projection(instance: FormInstance) -> dict[str, Any]:
    return {
        "id": instance.id,
        "master_content_item_id": instance.master_content_item_id,
        "source_document_version_id": instance.source_document_version_id,
        "profile_id": instance.profile_id,
        "mapping_release_id": instance.mapping_release_id,
        "context_type": instance.context_type,
        "context_id": instance.context_id,
        "resolved_values": instance.resolved_values or {},
        "resolved_assertion_ids": instance.resolved_assertion_ids or [],
        "field_provenance_json": instance.field_provenance_json or {},
        "field_citations_json": instance.field_citations_json or {},
        "field_write_metadata_json": instance.field_write_metadata_json or {},
        "draft_revision": instance.draft_revision,
        "status": instance.status,
        "last_applied_preview_fingerprint": instance.last_applied_preview_fingerprint,
        "last_applied_by": instance.last_applied_by,
        "last_applied_at": instance.last_applied_at.isoformat() if instance.last_applied_at else None,
    }


def _apply_request_fingerprint(
    *,
    actor_id: str,
    form_instance_id: str,
    project_id: str,
    case_id: str,
    purpose: str,
    preview_fingerprint: str,
    expected_draft_revision: int,
    selected_field_keys: list[str] | None,
) -> str:
    return _fingerprint(
        {
            "contract": "governed-prefill-apply-request-v1",
            "actor_id": actor_id,
            "form_instance_id": form_instance_id,
            "project_id": project_id,
            "case_id": case_id,
            "purpose": purpose,
            "preview_fingerprint": preview_fingerprint,
            "expected_draft_revision": expected_draft_revision,
            "selected_field_keys": sorted(selected_field_keys) if selected_field_keys is not None else None,
        }
    )


def apply_governed_prefill_to_draft(
    db: Session,
    *,
    role: Any,
    actor_id: str,
    project_id: str,
    case_id: str,
    purpose: str,
    form_instance_id: str,
    preview_fingerprint: str,
    expected_draft_revision: int,
    idempotency_key: str,
    selected_field_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Apply one exact, revalidated assist preview to an existing DRAFT.

    The request contains only pins and intent.  Values, citations, and
    authority are rebuilt from current canonical state before any FormInstance
    mutation.  All selected fields are validated before the first assignment.
    """
    if not idempotency_key.strip():
        raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
    context_case = db.scalar(
        select(AuthorityCase)
        .join(RegulatoryJourney, RegulatoryJourney.id == AuthorityCase.regulatory_journey_id)
        .where(AuthorityCase.id == case_id, RegulatoryJourney.project_id == project_id)
    )
    if not context_case:
        raise ValueError("PROJECT_CASE_CONTEXT_MISMATCH")

    # PostgreSQL takes a row lock; SQLite serializes the actual write and the
    # expected revision check remains the optimistic concurrency boundary.
    instance = db.scalar(select(FormInstance).where(FormInstance.id == form_instance_id).with_for_update())
    if not instance:
        raise ValueError("FORM_INSTANCE_NOT_FOUND")
    if instance.context_type != "AuthorityCase" or instance.context_id != case_id:
        raise ValueError("PROJECT_CASE_CONTEXT_MISMATCH")
    request_fingerprint = _apply_request_fingerprint(
        actor_id=actor_id,
        form_instance_id=form_instance_id,
        project_id=project_id,
        case_id=case_id,
        purpose=purpose,
        preview_fingerprint=preview_fingerprint,
        expected_draft_revision=expected_draft_revision,
        selected_field_keys=selected_field_keys,
    )
    existing = db.scalar(select(FormInstanceApply).where(FormInstanceApply.idempotency_key == idempotency_key))
    if existing:
        if existing.request_fingerprint != request_fingerprint:
            raise ValueError("IDEMPOTENCY_CONFLICT")
        return {**(existing.result_json or {}), "idempotent_replay": True}

    if instance.status != "DRAFT":
        raise ValueError("DRAFT_NOT_EDITABLE")
    if instance.draft_revision != expected_draft_revision:
        raise ValueError("CONCURRENT_MODIFICATION")
    item = db.get(MasterContentItem, instance.master_content_item_id)
    profile = db.get(FormAutomationProfile, instance.profile_id)
    release = db.get(FormMappingRelease, instance.mapping_release_id) if instance.mapping_release_id else None
    if not item or item.current_document_version_id != instance.source_document_version_id:
        raise ValueError("TARGET_FORM_CHANGED")
    if not profile or profile.source_document_version_id != instance.source_document_version_id:
        raise ValueError("TARGET_FORM_CHANGED")
    if (
        not release
        or release.status != "RELEASED"
        or release.profile_id != profile.id
        or release.master_content_item_id != item.id
        or release.source_document_version_id != instance.source_document_version_id
    ):
        raise ValueError("MAPPING_RELEASE_CHANGED")

    current_preview = preview_prefill(
        db,
        role=role,
        caller_id=actor_id,
        project_id=project_id,
        case_id=case_id,
        master_content_id=instance.master_content_item_id,
        purpose=purpose,
        form_instance_id=instance.id,
    )
    if current_preview.get("preview_fingerprint") != preview_fingerprint:
        raise ValueError("STALE_PREVIEW")
    if current_preview.get("preview_status") != "READY" and selected_field_keys is None:
        raise ValueError("PREFILL_PREVIEW_NOT_READY")

    fields_by_key = {field["logical_field_key"]: field for field in current_preview["fields"]}
    if selected_field_keys is not None:
        if len(selected_field_keys) != len(set(selected_field_keys)) or not selected_field_keys:
            raise ValueError("INVALID_FIELD_SELECTION")
        selected = sorted(selected_field_keys)
    else:
        selected = sorted(fields_by_key)
    if not set(selected).issubset(fields_by_key):
        raise ValueError("INVALID_FIELD_SELECTION")
    selected_fields = [fields_by_key[key] for key in selected]
    if any(field["proposal_status"] != "READY" or field["authority_state"] != "VERIFIED" or field["proposed_value"] is None or not field["provenance"] for field in selected_fields):
        raise ValueError("INVALID_FIELD_SELECTION")

    values = dict(instance.resolved_values or {})
    write_metadata = dict(instance.field_write_metadata_json or {})
    provenance = dict(instance.field_provenance_json or {})
    citations = dict(instance.field_citations_json or {})
    conflicts: list[str] = []
    changed: list[str] = []
    for field in selected_fields:
        logical_key = field["logical_field_key"]
        proposed = field["proposed_value"]
        current = values.get(logical_key)
        has_existing = logical_key in values and current not in (None, "")
        if has_existing and _value_key(current) != _value_key(proposed):
            conflicts.append(logical_key)
        elif not has_existing:
            values[logical_key] = proposed
            write_metadata[logical_key] = {
                "mode": "GOVERNED_AUTO",
                "value_identity": _fingerprint({"value": proposed}),
                "preview_fingerprint": preview_fingerprint,
                "actor_id": actor_id,
                "applied_at": _now().isoformat(),
            }
            provenance[logical_key] = {
                "logical_field_key": logical_key,
                "applied_value_identity": _fingerprint({"value": proposed}),
                "target_form": {
                    "master_content_item_id": current_preview["master_content_id"],
                    "document_version_id": current_preview["master_content_version_pin"]["document_version_id"],
                },
                "mapping": {
                    "mapping_release_id": current_preview["mapping_release_pin"],
                    "mapping_release_version": current_preview["mapping_release_version"],
                    "mapping_checksum": current_preview["mapping_checksum"],
                    "mapping_rule_id": field["mapping_rule_id"],
                },
                "value_evidence": {
                    "assertion_ids": [citation.get("evidence_identity") for citation in field["provenance"] if citation.get("evidence_identity")],
                    "citations": field["provenance"],
                },
                "preview_fingerprint": preview_fingerprint,
                "idempotency_key": idempotency_key,
                "actor_id": actor_id,
                "applied_at": _now().isoformat(),
            }
            citations[logical_key] = field["citations"]
            changed.append(logical_key)
    if conflicts:
        raise ValueError(f"HUMAN_EDIT_CONFLICT:{','.join(conflicts)}")

    if changed:
        instance.resolved_values = values
        instance.field_write_metadata_json = write_metadata
        instance.field_provenance_json = provenance
        instance.field_citations_json = citations
        prior_assertions = list(instance.resolved_assertion_ids or [])
        new_assertions = [
            citation.get("evidence_identity")
            for field in selected_fields
            for citation in field["provenance"]
            if citation.get("evidence_identity")
        ]
        instance.resolved_assertion_ids = list(dict.fromkeys(prior_assertions + new_assertions))
        instance.draft_revision += 1
        instance.last_applied_preview_fingerprint = preview_fingerprint
        instance.last_applied_by = actor_id
        instance.last_applied_at = _now()
    result = {
        "apply_status": "APPLIED",
        "idempotent_replay": False,
        "form_instance": _draft_projection(instance),
        "form_instance_id": instance.id,
        "applied_field_keys": selected,
        "changed_field_keys": changed,
        "preview_fingerprint": preview_fingerprint,
        "idempotency_key": idempotency_key,
        "canonical_write_count": 0,
        "source_evidence_write_count": 0,
        "protected_human_action_count": 0,
        "generated_artifact_count": 0,
        "draft_apply": "APPLIED_TO_EXISTING_FORMINSTANCE_DRAFT",
    }
    ledger = FormInstanceApply(
        form_instance_id=instance.id,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        preview_fingerprint=preview_fingerprint,
        project_id=project_id,
        context_type=instance.context_type,
        context_id=instance.context_id,
        expected_draft_revision=expected_draft_revision,
        resulting_draft_revision=instance.draft_revision,
        selected_field_keys=selected,
        applied_field_keys=changed,
        actor_id=actor_id,
        result_json=result,
    )
    db.add(ledger)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        prior = db.scalar(select(FormInstanceApply).where(FormInstanceApply.idempotency_key == idempotency_key))
        if prior and prior.request_fingerprint == request_fingerprint:
            return {**(prior.result_json or {}), "idempotent_replay": True}
        raise ValueError("CONCURRENT_MODIFICATION") from exc
    result["apply_id"] = ledger.id
    ledger.result_json = result
    audit(
        db,
        correlation_id=f"governed-prefill-apply:{ledger.id}",
        event_type="GOVERNED_PREFILL_APPLIED",
        entity_type="FormInstance",
        entity_id=instance.id,
        actor_id=actor_id,
        after={
            "apply_id": ledger.id,
            "draft_revision": instance.draft_revision,
            "applied_field_keys": changed,
            "preview_fingerprint": preview_fingerprint,
            "target_document_version_id": current_preview["master_content_version_pin"]["document_version_id"],
            "mapping_release_id": current_preview["mapping_release_pin"],
        },
        metadata={
            "idempotency_key": idempotency_key,
            "source_assertion_ids": instance.resolved_assertion_ids,
            "protected_actions_triggered": False,
        },
    )
    db.flush()
    result["form_instance"] = _draft_projection(instance)
    ledger.result_json = result
    db.flush()
    return result
