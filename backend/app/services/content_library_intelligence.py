"""Content Library Intelligence orchestration on the shared AI platform.

This module owns only operation mapping and item-level policy.  Context,
provider, ledger, work-product, citation, and invalidation mechanics remain
shared ProposalOps primitives.  There are no mutation tools or AI-owned writes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.citations import validate_compiled_citations
from ..ai.gateway import ModelGateway
from ..ai.skill_registry import resolve_content_library_operation
from ..ai.errors import AIError
from ..ai.ledger import finalize_failure, finalize_success, reserve_audit
from ..ai.limits import reserve_execution
from ..api.dependencies import AuthenticatedPrincipal
from ..config.settings import Settings
from ..models import AIExecutionLedger, AIWorkProduct, DefinitionEntry, DefinitionRevision, DocumentVersion, MasterContentItem
from .backend_realignment import persona_for_role
from .context_compiler import ContextCompileRequest, ContextSourceSpec, compile_context
from .intelligence_contracts import (
    IntelligenceContractError,
    create_ai_work_product,
    record_intelligence_citation,
    stable_hash,
)
from .intelligence_foundation import bind_work_product_dependencies, finalize_current_work_product
from .master_content import (
    authorize_master_content_access,
    master_content_scan_is_clean,
    master_content_scan_state,
)


CONTENT_LIBRARY_PURPOSE = "CONTENT_LIBRARY_INTELLIGENCE"
CONTEXT_SCHEMA_VERSION = "CONTENT-LIBRARY-AI-CONTEXT-1"
POLICY_VERSION = "CONTENT-LIBRARY-AI-POLICY-1"
ACTOR_TYPE = "ENTRA_USER"


@dataclass(frozen=True)
class _LibrarySubject:
    kind: str
    entity: MasterContentItem | DefinitionEntry
    revision: DocumentVersion | DefinitionRevision
    subject_id: str
    version_id: str
    source_hash: str
    target_entity_type: str


def _definition_revision_hash(revision: DefinitionRevision) -> str:
    return stable_hash({
        "revision_id": revision.id,
        "revision_number": revision.revision_number,
        "term": revision.term,
        "description": revision.description,
        "aliases": revision.aliases,
    })


def _http(error: AIError | IntelligenceContractError, status_code: int | None = None) -> HTTPException:
    code = getattr(error, "code", str(error))
    return HTTPException(status_code or getattr(error, "status_code", 409), detail={"code": code})


def _request_fingerprint(*, subject: _LibrarySubject, skill: Any, principal: AuthenticatedPrincipal) -> str:
    return stable_hash({
        "actor_user_id": principal.user_id,
        "auth_mode": principal.auth_mode,
        "subject_id": subject.subject_id,
        "version_id": subject.version_id,
        "version_sha256": subject.source_hash,
        "target_entity_type": subject.target_entity_type,
        "skill_id": skill.manifest.skill_id,
        "skill_version": skill.manifest.version,
        "manifest_hash": skill.manifest.manifest_hash,
        "purpose": CONTENT_LIBRARY_PURPOSE,
    })


def _provider_input(skill: Any, compiled: Any, *, operation: str) -> str:
    return json.dumps({
        "instructions": skill.instructions,
        "operation": operation,
        "authority": {
            "canonical_write_authority": "NONE",
            "protected_action_authority": "NONE",
            "document_text_is_untrusted_evidence": True,
        },
        "context": [{
            "key": item.key,
            "context_type": item.context_type,
            "trust_state": item.trust_state,
            "currentness_state": item.currentness_state,
            "projection": item.projection,
            "citation_key": f"CIT-{index:03d}",
        } for index, item in enumerate(compiled.items, 1)],
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_source18(item: MasterContentItem) -> bool:
    value = (item.source_type_code or "").upper()
    return "SOURCE18" in value or "OFFICIAL" in value


def _ensure_item_scope(db: Session, principal: AuthenticatedPrincipal, item: MasterContentItem) -> None:
    try:
        authorize_master_content_access(db, item, principal.role, action="AI_READ")
    except HTTPException as exc:
        raise _http(AIError("AI_CONTEXT_SCOPE_UNPROVABLE", status_code=403), 403) from exc
    if not principal.user_id:
        raise _http(AIError("AI_ACTOR_REQUIRED", status_code=403), 403)


def _ensure_definition_scope(principal: AuthenticatedPrincipal, definition: DefinitionEntry) -> None:
    persona = persona_for_role(principal.role)
    if persona in {"OWNER", "SYSTEM_ADMIN"}:
        return
    module = "BD" if persona == "BUSINESS_DEVELOPMENT" else "ENGINEERING"
    if module not in (definition.used_in or []):
        raise _http(AIError("AI_CONTEXT_SCOPE_UNPROVABLE", status_code=403), 403)
    if not principal.user_id:
        raise _http(AIError("AI_ACTOR_REQUIRED", status_code=403), 403)


def _resolve_current(db: Session, item: MasterContentItem) -> DocumentVersion:
    if not item.current_document_version_id:
        raise _http(AIError("AI_CURRENT_VERSION_UNRESOLVED", status_code=409), 409)
    version = db.get(DocumentVersion, item.current_document_version_id)
    if version is None or version.document_id != item.document_id:
        raise _http(AIError("AI_CURRENT_VERSION_UNRESOLVED", status_code=409), 409)
    if version.document is None or version.document.current_version_id != version.id or version.superseded_by is not None:
        raise _http(AIError("AI_CURRENT_VERSION_NOT_CURRENT", status_code=409), 409)
    if not master_content_scan_is_clean(version):
        raise HTTPException(409, detail={
            "code": "AI_SOURCE_MALWARE_GATE_BLOCKED",
            "malware_scan_state": master_content_scan_state(version),
        })
    return version


def _resolve_subject(db: Session, principal: AuthenticatedPrincipal, item_id: str) -> _LibrarySubject:
    item = db.get(MasterContentItem, item_id)
    if item is not None:
        _ensure_item_scope(db, principal, item)
        version = _resolve_current(db, item)
        return _LibrarySubject("MASTER_CONTENT", item, version, item.id, version.id, version.sha256, "MASTER_CONTENT_ITEM")
    definition = db.get(DefinitionEntry, item_id)
    if definition is None:
        raise HTTPException(404, detail={"code": "MASTER_CONTENT_NOT_FOUND"})
    _ensure_definition_scope(principal, definition)
    revision = db.get(DefinitionRevision, definition.current_revision_id) if definition.current_revision_id else None
    if definition.status != "ACTIVE" or revision is None or revision.definition_id != definition.id or revision.status != "CURRENT":
        raise _http(AIError("AI_CURRENT_VERSION_UNRESOLVED", status_code=409), 409)
    return _LibrarySubject("DEFINITION", definition, revision, definition.id, revision.id, _definition_revision_hash(revision), "DEFINITION_ENTRY")


def _subject_sources(subject: _LibrarySubject, *, operation: str) -> list[ContextSourceSpec]:
    if subject.kind == "DEFINITION":
        sources = [ContextSourceSpec(
            key="canonical-definition-revision",
            context_type="DEFINITION_REVISION",
            selector={"definition_entry_id": subject.entity.id, "definition_revision_id": subject.revision.id},
        )]
        if operation == "version-change-analysis":
            sources.append(ContextSourceSpec(
                key="definition-revision-predecessor",
                context_type="DEFINITION_REVISION_PREDECESSOR",
                selector={"definition_entry_id": subject.entity.id, "definition_revision_id": subject.revision.id},
                required=False,
            ))
        return sources
    sources = [
        ContextSourceSpec(
            key="canonical-master-content",
            context_type="MASTER_CONTENT",
            selector={"master_content_item_id": subject.entity.id, "document_version_id": subject.revision.id},
        ),
        ContextSourceSpec(
            key="document-text-evidence",
            context_type="DOCUMENT_TEXT_EVIDENCE",
            selector={"master_content_item_id": subject.entity.id, "document_version_id": subject.revision.id},
        ),
    ]
    if operation == "version-change-analysis":
        sources.append(ContextSourceSpec(
            key="document-version-predecessor",
            context_type="DOCUMENT_VERSION_PREDECESSOR",
            selector={"master_content_item_id": subject.entity.id, "document_version_id": subject.revision.id},
            required=False,
        ))
    return sources


def _replay(db: Session, idempotency_key: str) -> dict[str, Any] | None:
    ledger = db.scalar(select(AIExecutionLedger).where(AIExecutionLedger.idempotency_key == idempotency_key))
    if ledger is None:
        return None
    product = db.scalar(select(AIWorkProduct).where(AIWorkProduct.execution_ledger_id == ledger.id))
    if ledger.status == "SUCCEEDED" and product is not None and str(product.state) == "CURRENT":
        return {
            "status": "SUCCEEDED",
            "replayed": True,
            "execution_id": ledger.id,
            "work_product_id": product.id,
            "skill_id": product.skill_id,
            "skill_version": product.skill_version,
            "skill_manifest_hash": product.skill_manifest_hash,
            "output_class": product.output_class,
            "output": product.structured_output_json,
            "citations": product.citation_count,
            "canonical_state_mutated": False,
            "protected_action_count": 0,
        }
    if product is not None and str(product.state) != "CURRENT":
        raise _http(AIError("AI_STALE_REPLAY_REJECTED", status_code=409), 409)
    raise _http(AIError("AI_REQUEST_IN_PROGRESS" if ledger.status == "RESERVED" else "AI_IDEMPOTENCY_CONFLICT", status_code=409), 409)


def execute_content_library_intelligence(
    db: Session,
    principal: AuthenticatedPrincipal,
    *,
    item_id: str,
    operation: str,
    idempotency_key: str,
    correlation_id: str,
    settings: Settings,
    provider: Any | None = None,
) -> dict[str, Any]:
    if not settings.ai_feature_enabled:
        raise _http(AIError("AI_FEATURE_DISABLED", status_code=503), 503)
    if not settings.ai_external_inference_enabled:
        raise _http(AIError("AI_EXTERNAL_INFERENCE_DISABLED", status_code=503), 503)
    if not settings.synthetic_only or settings.real_data_allowed or settings.ai_real_content_allowed:
        raise _http(AIError("AI_REAL_CONTENT_NOT_AUTHORIZED", status_code=403), 403)
    if not idempotency_key.strip():
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
    replay = _replay(db, idempotency_key)
    if replay is not None:
        return replay

    skill = resolve_content_library_operation(operation)
    normalized_operation = operation.strip().lower().replace("_", "-")
    subject = _resolve_subject(db, principal, item_id)
    if subject.kind == "MASTER_CONTENT" and _is_source18(subject.entity) and normalized_operation in {
        "intake-governance-analysis", "reuse-applicability-analysis", "description-draft",
    }:
        raise HTTPException(403, detail={"code": "SOURCE18_AI_OPERATION_FORBIDDEN"})

    if subject.kind == "MASTER_CONTENT" and subject.revision.metadata_json and str(subject.revision.metadata_json.get("storage_provider") or "").lower() == "azure-blob" and not master_content_scan_is_clean(subject.revision):
        raise HTTPException(409, detail={"code": "AI_SOURCE_MALWARE_GATE_BLOCKED"})

    try:
        compiled = compile_context(db, ContextCompileRequest(
            correlation_id=correlation_id,
            actor_user_id=principal.user_id or "",
            scope_type="MODULE",
            scope_id=subject.subject_id,
            project_id=None,
            context_schema_version=CONTEXT_SCHEMA_VERSION,
            policy_version=POLICY_VERSION,
            skill_manifest=skill.manifest,
            sources=_subject_sources(subject, operation=normalized_operation),
        ))
    except IntelligenceContractError as exc:
        db.rollback()
        raise _http(exc, 409) from exc
    request_hash = _request_fingerprint(subject=subject, skill=skill, principal=principal)
    provider_input = _provider_input(skill, compiled, operation=operation)
    try:
        reservation = reserve_execution(
            db,
            settings=settings,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            actor_user_id=principal.user_id,
            auth_mode=principal.auth_mode,
            purpose=CONTENT_LIBRARY_PURPOSE,
            execution_mode="INTERACTIVE",
            project_id="",
            target_entity_type=subject.target_entity_type,
            target_entity_id=subject.subject_id,
            architecture_version="AI-D0-D1-ARCHITECTURE-1.0",
            policy_version=POLICY_VERSION,
            context_fingerprint=compiled.context_hash,
            request_fingerprint=request_hash,
            provider="AZURE_OPENAI_FOUNDRY",
            provider_region="UAE_NORTH_REGIONAL",
            deployment_name=settings.ai_azure_openai_deployment,
            model_name=settings.ai_azure_openai_expected_model,
            model_version=settings.ai_azure_openai_expected_version,
            citation_count=len(compiled.items),
            provider_input=provider_input,
            scope_type="MODULE",
            scope_id=subject.subject_id,
            owning_module="master_content",
            skill_id=skill.manifest.skill_id,
            skill_version=skill.manifest.version,
            skill_manifest_hash=skill.manifest.manifest_hash,
        )
        reserve_audit(db, ledger=reservation.ledger, actor_type=ACTOR_TYPE if principal.auth_mode == "ENTRA" else "DEV_USER")
        db.commit()
    except AIError as exc:
        db.rollback()
        raise _http(exc, getattr(exc, "status_code", 503)) from exc

    try:
        result = ModelGateway(settings, provider=provider).execute(
            skill,
            provider_input=provider_input,
            max_output_tokens=settings.ai_max_output_tokens,
        )
        output = skill.output.validator(result.payload)
        citations = validate_compiled_citations(output, compiled, skill.output)
        source_identity = output.model_dump(mode="json", exclude_none=True).get("source_identity", {})
        expected_identity = (
            {"master_content_item_id": subject.subject_id, "document_version_id": subject.version_id, "sha256": subject.source_hash}
            if subject.kind == "MASTER_CONTENT"
            else {"definition_entry_id": subject.subject_id, "definition_revision_id": subject.version_id, "sha256": subject.source_hash}
        )
        if source_identity != expected_identity:
            raise AIError("AI_SOURCE_IDENTITY_MISMATCH", status_code=502)
        if any(key not in {f"CIT-{index:03d}" for index in range(1, len(compiled.items) + 1)} for key in skill.output.citation_keys(output)):
            raise AIError("AI_CITATION_VALIDATION_FAILED", status_code=502)
        output_json = output.model_dump(mode="json")
        output_hash = hashlib.sha256(json.dumps(output_json, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        final_db = db
        work_product = create_ai_work_product(final_db, {
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
            "execution_ledger_id": reservation.ledger.id,
            "context_snapshot_id": compiled.context_snapshot_id,
            "owning_module": "master_content",
            "skill_id": skill.manifest.skill_id,
            "skill_version": skill.manifest.version,
            "skill_manifest_hash": skill.manifest.manifest_hash,
            "scope_type": "MODULE",
            "scope_id": subject.subject_id,
            "project_id": None,
            "target_entity_type": subject.target_entity_type,
            "target_entity_id": subject.subject_id,
            "output_class": skill.manifest.output_class,
            "structured_output_json": output_json,
            "output_hash": output_hash,
            "data_classification": compiled.data_classification,
            "contains_sensitive_data": compiled.contains_sensitive_data,
            "state": "CURRENT",
            "citation_count": len(citations),
            "lineage_hash": compiled.context_hash,
        })
        for citation in citations:
            record_intelligence_citation(final_db, {
                "work_product_id": work_product.id,
                "ordinal": citation["ordinal"],
                "source_type": citation["source_type"],
                "source_id": citation["source_id"],
                "source_version_or_hash": citation["source_version_or_hash"],
                "locator_json": citation["locator_json"],
            })
        bind_work_product_dependencies(final_db, work_product, snapshot_id=compiled.context_snapshot_id)
        finalize_current_work_product(final_db, work_product=work_product, snapshot_id=compiled.context_snapshot_id)
        finalize_success(
            final_db,
            ledger_id=reservation.ledger.id,
            correlation_id=correlation_id,
            actor_id=principal.user_id,
            actor_type=ACTOR_TYPE if principal.auth_mode == "ENTRA" else "DEV_USER",
            usage=result.usage,
            estimated_cost=(result.usage.input_tokens * settings.ai_input_price_usd_per_1m_tokens / 1000000) + (result.usage.output_tokens * settings.ai_output_price_usd_per_1m_tokens / 1000000),
            output_fingerprint=output_hash,
            citation_count=len(citations),
            provider_response_id=result.response_id,
            reservation_owner_token=reservation.owner_token,
            reservation_generation=reservation.generation,
        )
        final_db.commit()
        return {
            "status": "SUCCEEDED",
            "replayed": False,
            "execution_id": reservation.ledger.id,
            "work_product_id": work_product.id,
            "skill_id": skill.manifest.skill_id,
            "skill_version": skill.manifest.version,
            "skill_manifest_hash": skill.manifest.manifest_hash,
            "output_class": skill.manifest.output_class,
            "output": output_json,
            "citations": len(citations),
            "canonical_state_mutated": False,
            "protected_action_count": 0,
        }
    except (AIError, IntelligenceContractError) as exc:
        db.rollback()
        try:
            finalize_failure(
                db,
                ledger_id=reservation.ledger.id,
                correlation_id=correlation_id,
                actor_id=principal.user_id,
                actor_type=ACTOR_TYPE if principal.auth_mode == "ENTRA" else "DEV_USER",
                code=getattr(exc, "code", str(exc)),
                reservation_owner_token=reservation.owner_token,
                reservation_generation=reservation.generation,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise _http(exc, getattr(exc, "status_code", 502)) from exc
    except Exception as exc:
        db.rollback()
        try:
            finalize_failure(db, ledger_id=reservation.ledger.id, correlation_id=correlation_id, actor_id=principal.user_id, actor_type=ACTOR_TYPE, code="AI_EXECUTION_FAILED", reservation_owner_token=reservation.owner_token, reservation_generation=reservation.generation)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(502, detail={"code": "AI_EXECUTION_FAILED"}) from exc
