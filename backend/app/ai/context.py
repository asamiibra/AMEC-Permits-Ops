"""Deterministic provider-safe context construction for AI-D1."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal
from ..config.settings import Settings, get_settings
from ..services.governed_retrieval import (
    RETRIEVAL_CONTRACT_VERSION,
    GovernedRetrievalResult,
    RetrievalQuery,
    access_context_for_role,
    governed_retrieve,
)
from .contracts import (
    AIContextItem,
    AIContextManifest,
    AIContextScope,
    AIExecutionMode,
    AIPurpose,
    MAX_CONTEXT_ITEMS,
    MAX_CONTEXT_UTF8_BYTES,
    MAX_ITEM_UTF8_BYTES,
)
from .policy import (
    AIAuthorizationContext,
    AIPurposePolicy,
    ResolvedAITarget,
    ai_error,
    authorize_ai_request,
)


SAFE_RELATIONSHIP_FIELDS = frozenset(
    {
        "project_id",
        "current_version_id",
        "observation_ids",
        "verified_assertion_ids",
        "classification_ids",
        "verified_assertion_facts",
        "used_in",
        "bindings",
        "aliases",
        "conflict_state",
        "conflicting_assertion_ids",
        "conflicting_result_ids",
        "ambiguity_state",
        "ambiguous_result_ids",
    }
)


def _safe_relationship_context(value: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key in sorted(SAFE_RELATIONSHIP_FIELDS):
        if key not in value:
            continue
        raw = value[key]
        if key == "verified_assertion_facts":
            safe[key] = tuple(
                {
                    field: fact[field]
                    for field in ("field_definition_id", "assertion_id", "display_value")
                    if field in fact
                }
                for fact in (raw or ())
                if isinstance(fact, dict)
            )
        elif key in {
            "observation_ids",
            "verified_assertion_ids",
            "classification_ids",
            "conflicting_assertion_ids",
            "conflicting_result_ids",
            "ambiguous_result_ids",
        }:
            safe[key] = tuple(str(item) for item in (raw or ()))
        elif key in {"used_in", "bindings", "aliases"}:
            safe[key] = tuple(str(item) for item in (raw or ()))
        elif key in {
            "project_id",
            "current_version_id",
            "conflict_state",
            "ambiguity_state",
        }:
            safe[key] = str(raw) if raw is not None else None
    return safe


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _item_from_result(result: GovernedRetrievalResult) -> AIContextItem:
    envelope = result.envelope
    return AIContextItem(
        canonical_domain=envelope.canonical_domain,
        canonical_entity_type=envelope.canonical_entity_type,
        canonical_entity_id=envelope.canonical_entity_id,
        master_content_id=envelope.master_content_id,
        transactional_entity_id=envelope.transactional_entity_id,
        document_id=envelope.document_id,
        document_version_id=envelope.document_version_id,
        definition_entry_id=envelope.definition_entry_id,
        definition_revision_id=envelope.definition_revision_id,
        source_artifact_id=envelope.source_artifact_id,
        source_intake_id=envelope.source_intake_id,
        source_currentness_state=envelope.source_currentness_state,
        verification_state=envelope.verification_state,
        authority_source_class=envelope.authority_source_class,
        superseded=envelope.superseded,
        sensitivity_class=envelope.sensitivity_class,
        relationship_context=_safe_relationship_context(envelope.relationship_context),
        content=envelope.content,
        citation=envelope.citation,
    )


def _validate_result(item: AIContextItem, policy: AIPurposePolicy) -> None:
    if item.canonical_domain == "MASTER_CONTENT":
        allowed = item.definition_entry_id is not None or item.master_content_id is not None
        if not allowed or not policy.allow_master_content:
            raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")
    elif item.canonical_domain == "TRANSACTIONAL_EVIDENCE":
        if not policy.allow_transactional_evidence:
            raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")
    else:
        raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")

    if item.sensitivity_class not in policy.allowed_sensitivity_classes:
        raise ai_error(403, "AI_CONTEXT_SENSITIVITY_DENIED")
    if item.superseded and not policy.allow_superseded:
        raise ai_error(403, "AI_CONTEXT_SUPERSEDED_DENIED")
    if (
        item.canonical_domain == "TRANSACTIONAL_EVIDENCE"
        and item.source_currentness_state == "HISTORICAL"
        and not policy.allow_historical
    ):
        raise ai_error(403, "AI_CONTEXT_HISTORICAL_DENIED")

    relationship = item.relationship_context
    if relationship.get("conflict_state") in {"CONFLICTING", "CONFLICT"}:
        raise ai_error(409, "AI_CONTEXT_CONFLICT")
    if relationship.get("ambiguity_state") == "AMBIGUOUS":
        raise ai_error(409, "AI_CONTEXT_CONFLICT")


def _fingerprint_payload(manifest: AIContextManifest) -> dict[str, Any]:
    payload = manifest.model_dump(mode="json")
    payload.pop("manifest_fingerprint", None)
    return payload


def _fingerprint(manifest: AIContextManifest) -> str:
    return hashlib.sha256(_canonical_json(_fingerprint_payload(manifest))).hexdigest()


def _build_manifest(
    *,
    authorization: AIAuthorizationContext,
    target: ResolvedAITarget,
    policy: AIPurposePolicy,
    execution_mode: AIExecutionMode,
    results: tuple[GovernedRetrievalResult, ...],
) -> AIContextManifest:
    if len(results) > MAX_CONTEXT_ITEMS:
        raise ai_error(413, "AI_CONTEXT_BUDGET_EXCEEDED")

    items = tuple(
        sorted(
            (_item_from_result(result) for result in results),
            key=lambda item: (
                item.canonical_domain,
                item.canonical_entity_type,
                item.canonical_entity_id,
                item.document_version_id or "",
                item.definition_revision_id or "",
                item.citation.locator_type,
                item.citation.locator,
            ),
        )
    )
    total_bytes = 0
    for item in items:
        item_bytes = len(item.content.encode("utf-8"))
        if item_bytes > MAX_ITEM_UTF8_BYTES:
            raise ai_error(413, "AI_CONTEXT_BUDGET_EXCEEDED")
        total_bytes += item_bytes
        _validate_result(item, policy)
    if total_bytes > MAX_CONTEXT_UTF8_BYTES:
        raise ai_error(413, "AI_CONTEXT_BUDGET_EXCEEDED")

    manifest = AIContextManifest(
        purpose=authorization.requested_purpose,
        execution_mode=execution_mode,
        scope=AIContextScope(
            project_id=target.project_id,
            target_entity_type=target.target_entity_type,
            target_entity_id=target.target_entity_id,
        ),
        policy={
            "purpose_id": policy.purpose_id,
            "required_capabilities": policy.required_capabilities,
        },
        retrieval_contract_version=RETRIEVAL_CONTRACT_VERSION,
        items=items,
        manifest_fingerprint="pending",
    )
    return manifest.model_copy(update={"manifest_fingerprint": _fingerprint(manifest)})


def build_context_manifest(
    db: Session,
    principal: AuthenticatedPrincipal,
    *,
    purpose: str,
    execution_mode: str,
    target_entity_type: str,
    target_entity_id: str,
    query: RetrievalQuery,
    settings: Settings | None = None,
) -> AIContextManifest:
    settings = settings or get_settings()
    authorization, target, policy = authorize_ai_request(
        db,
        principal,
        purpose_value=purpose,
        execution_mode_value=execution_mode,
        target_entity_type_value=target_entity_type,
        target_entity_id=target_entity_id,
        synthetic_only=settings.synthetic_only,
        real_data_allowed=settings.real_data_allowed,
    )
    if query.project_id is not None and query.project_id != target.project_id:
        raise ai_error(403, "AI_CONTEXT_SCOPE_MISMATCH")
    if query.limit > MAX_CONTEXT_ITEMS:
        raise ai_error(413, "AI_CONTEXT_BUDGET_EXCEEDED")

    bound_query = query.model_copy(update={"project_id": target.project_id})
    access = access_context_for_role(
        principal.role,
        caller_id=principal.user_id or "synthetic-principal",
        project_ids=(target.project_id,),
        purpose="READ",
    )
    results = tuple(governed_retrieve(db, bound_query, access))
    return _build_manifest(
        authorization=authorization,
        target=target,
        policy=policy,
        execution_mode=authorization.execution_mode,
        results=results,
    )


def fingerprint_for(manifest: AIContextManifest) -> str:
    """Expose the deterministic calculation for executable contract tests."""
    return _fingerprint(manifest)
