"""Shared P05 skill execution runtime.

This is the only generalized execution path: the caller supplies an exact
registered skill identity and P04 source specifications; the runtime owns
authorization, context binding, reservation, gateway execution, validation,
and atomic work-product finalization.  It never owns a module review decision.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal
from ..config.settings import Settings, get_settings
from ..db import SessionLocal
from ..models import AIExecutionLedger, AIWorkProduct, ContextDependency, ContextSnapshot, IntelligenceCitation
from ..services.context_compiler import ContextSourceSpec, compile_context
from ..services.intelligence_contracts import (
    IntelligenceContractError,
    create_ai_work_product,
    record_intelligence_citation,
    stable_hash,
)
from .citations import validate_compiled_citations
from .contracts import AI_ARCHITECTURE
from .errors import AIError
from .gateway import ModelGateway
from .ledger import finalize_failure, finalize_success, reserve_audit
from .limits import reserve_execution
from ..services.intelligence_foundation import P07_CONTEXT_CHANGED, P07_STALE_REPLAY, bind_work_product_dependencies, finalize_current_work_product
from ..audit.service import audit
from .skill_registry import SKILL_REGISTRY, SkillDefinition, SkillRegistry


class SkillExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    idempotency_key: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=100)
    skill_id: str = Field(min_length=1, max_length=160)
    skill_version: str = Field(min_length=1, max_length=80)
    skill_manifest_hash: str = Field(min_length=64, max_length=64)
    purpose: str = Field(min_length=1, max_length=100)
    execution_mode: str = Field(min_length=1, max_length=30)
    scope_type: str = Field(min_length=1, max_length=50)
    scope_id: str = Field(min_length=1, max_length=160)
    project_id: str | None = Field(default=None, max_length=36)
    target_entity_type: str = Field(min_length=1, max_length=80)
    target_entity_id: str = Field(min_length=1, max_length=160)
    context_schema_version: str = Field(min_length=1, max_length=80)
    policy_version: str = Field(min_length=1, max_length=80)
    sources: tuple[ContextSourceSpec, ...] = ()


@dataclass(frozen=True)
class RuntimeDependencies:
    session_factory: Callable[[], Session] = SessionLocal


def _provider_input(skill: SkillDefinition, compiled: Any) -> str:
    """Serialize only P04's bounded, safe projections for provider input."""

    def projection_for_text(item: Any) -> dict[str, Any]:
        projection = dict(item.projection)
        media = projection.get("source_media")
        if isinstance(media, dict) and "image_data_url" in media:
            projection["source_media"] = {key: value for key, value in media.items() if key != "image_data_url"}
        return projection

    payload = {
        "instructions": skill.instructions,
        "skill": {
            "skill_id": skill.manifest.skill_id,
            "version": skill.manifest.version,
            "output_schema": skill.output.schema_name,
        },
        "context": [
            {
                "key": item.key,
                "context_type": item.context_type,
                "trust_state": item.trust_state,
                "currentness_state": item.currentness_state,
                "projection": projection_for_text(item),
                "citation_key": f"CIT-{index:03d}",
            }
            for index, item in enumerate(compiled.items, 1)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return encoded


def _provider_input_content(provider_input: str, compiled: Any) -> list[dict[str, Any]] | None:
    """Build Responses API multimodal parts without changing text providers."""
    content: list[dict[str, Any]] = [{"type": "input_text", "text": provider_input}]
    for item in compiled.items:
        media = item.projection.get("source_media") if isinstance(item.projection, dict) else None
        if not isinstance(media, dict):
            continue
        image_data_url = media.get("image_data_url")
        if isinstance(image_data_url, str) and image_data_url.startswith("data:image/"):
            content.append({
                "type": "input_text",
                "text": f"Image evidence for {item.key}; source filename {item.projection.get('source_filename')}; SHA-256 {media.get('sha256')}.",
            })
            content.append({"type": "input_image", "image_url": image_data_url, "detail": "low"})
    return [{"role": "user", "content": content}] if len(content) > 1 else None


def _request_fingerprint(
    request: SkillExecutionRequest,
    skill: SkillDefinition,
    compiled: Any,
    principal: AuthenticatedPrincipal,
) -> str:
    return stable_hash(
        {
            "actor_user_id": compiled.actor_user_id,
            "auth_mode": principal.auth_mode,
            "purpose": request.purpose,
            "execution_mode": request.execution_mode,
            "scope_type": request.scope_type.upper(),
            "scope_id": request.scope_id,
            "project_id": request.project_id,
            "target_entity_type": request.target_entity_type,
            "target_entity_id": request.target_entity_id,
            "skill_id": skill.manifest.skill_id,
            "skill_version": skill.manifest.version,
            "skill_manifest_hash": skill.manifest.manifest_hash,
            "context_snapshot_id": compiled.context_snapshot_id,
            "context_hash": compiled.context_hash,
            "policy_version": request.policy_version,
        }
    )


def _verify_snapshot(db: Session, request: SkillExecutionRequest, skill: SkillDefinition, compiled: Any) -> None:
    snapshot = db.get(ContextSnapshot, compiled.context_snapshot_id)
    if snapshot is None:
        raise AIError("AI_CONTEXT_SNAPSHOT_NOT_FOUND", status_code=409)
    expected = {
        "owning_module": skill.manifest.owning_module,
        "scope_type": request.scope_type.upper(),
        "scope_id": request.scope_id,
        "project_id": request.project_id,
        "skill_id": skill.manifest.skill_id,
        "skill_version": skill.manifest.version,
        "skill_manifest_hash": skill.manifest.manifest_hash,
        "context_schema_version": request.context_schema_version,
        "policy_version": request.policy_version,
        "context_hash": compiled.context_hash,
        "authorization_context_hash": compiled.authorization_context_hash,
    }
    if any(getattr(snapshot, key) != value for key, value in expected.items()):
        raise AIError("AI_CONTEXT_SNAPSHOT_BINDING_MISMATCH", status_code=409)
    dependencies = db.scalars(
        select(ContextDependency).where(ContextDependency.context_snapshot_id == snapshot.id)
    ).all()
    by_identity = {
        (dep.dependency_type, dep.dependency_id, dep.dependency_version_or_hash): dep
        for dep in dependencies
    }
    for item in compiled.items:
        dependency = by_identity.get((item.dependency_type, item.dependency_id, item.dependency_version_or_hash))
        if dependency is None:
            raise AIError("AI_CONTEXT_DEPENDENCY_SET_MISMATCH", status_code=409)
        if dependency.trust_state != item.trust_state or dependency.currentness_state_at_capture != item.currentness_state:
            raise AIError("AI_CONTEXT_DEPENDENCY_IDENTITY_MISMATCH", status_code=409)
        if dependency.currentness_state_at_capture != "CURRENT":
            raise AIError("AI_CONTEXT_DEPENDENCY_NOT_CURRENT", status_code=409)
    if not any(dep.dependency_type == "SKILL_MANIFEST" and dep.dependency_version_or_hash == skill.manifest.manifest_hash for dep in dependencies):
        raise AIError("AI_CONTEXT_GOVERNANCE_DEPENDENCY_MISSING", status_code=409)
    if not any(dep.dependency_type == "POLICY_VERSION" and dep.dependency_version_or_hash for dep in dependencies):
        raise AIError("AI_CONTEXT_GOVERNANCE_DEPENDENCY_MISSING", status_code=409)
    for dependency in dependencies:
        if dependency.currentness_state_at_capture != "CURRENT":
            raise AIError("AI_CONTEXT_DEPENDENCY_NOT_CURRENT", status_code=409)


def _replay_if_possible(
    db: Session,
    request: SkillExecutionRequest,
    fingerprint: str,
    actor_user_id: str,
) -> dict[str, Any] | None:
    existing = db.scalar(
        select(AIExecutionLedger).where(AIExecutionLedger.idempotency_key == request.idempotency_key)
    )
    if existing is None:
        return None
    if existing.request_fingerprint != fingerprint or existing.actor_user_id != actor_user_id:
        raise AIError("AI_IDEMPOTENCY_CONFLICT", status_code=409)
    if existing.status == "RESERVED":
        raise AIError("AI_REQUEST_IN_PROGRESS", status_code=409)
    if existing.status == "FAILED":
        raise AIError("AI_REQUEST_RETRY_REQUIRES_NEW_KEY", status_code=409)
    if existing.status != "SUCCEEDED":
        raise AIError("AI_IDEMPOTENCY_CONFLICT", status_code=409)
    work_product = db.scalar(
        select(AIWorkProduct).where(AIWorkProduct.execution_ledger_id == existing.id)
    )
    if work_product is None:
        raise AIError("AI_IDEMPOTENCY_REPLAY_INCOMPLETE", status_code=500)
    if str(work_product.state) != "CURRENT":
        raise AIError(P07_STALE_REPLAY, status_code=409)
    citations = db.scalars(select(IntelligenceCitation).where(
        IntelligenceCitation.work_product_id == work_product.id,
    ).order_by(IntelligenceCitation.ordinal)).all()
    citation_payload = [{
        "ordinal": citation.ordinal,
        "source_type": citation.source_type,
        "source_id": citation.source_id,
        "source_version_or_hash": citation.source_version_or_hash,
        "locator_json": citation.locator_json,
    } for citation in citations]
    return {
        "execution_id": existing.id,
        "work_product_id": work_product.id,
        "status": "SUCCEEDED",
        "replayed": True,
        "skill_id": work_product.skill_id,
        "skill_version": work_product.skill_version,
        "skill_manifest_hash": work_product.skill_manifest_hash,
        "context_snapshot_id": work_product.context_snapshot_id,
        "output_class": work_product.output_class,
        "output": work_product.structured_output_json,
        "output_hash": work_product.output_hash,
        "citations": citation_payload,
        "citation_count": work_product.citation_count,
        "draft_only": work_product.output_class == "DRAFT",
        "human_review_required": True,
        "canonical_state_mutated": False,
        "protected_action_count": 0,
    }


class SkillRuntime:
    def __init__(
        self,
        *,
        registry: SkillRegistry = SKILL_REGISTRY,
        gateway_factory: Callable[..., ModelGateway] = ModelGateway,
        dependencies: RuntimeDependencies | None = None,
    ):
        self.registry = registry
        self.gateway_factory = gateway_factory
        self.dependencies = dependencies or RuntimeDependencies()
        self._inflight_lock = threading.Lock()
        self._inflight_keys: set[str] = set()

    def execute(
        self,
        db: Session,
        principal: AuthenticatedPrincipal,
        request: SkillExecutionRequest,
        *,
        settings: Settings | None = None,
        provider: Any | None = None,
    ) -> dict[str, Any]:
        # A same-process caller racing the same idempotency key must observe
        # the in-progress boundary, even if SQLite scheduling lets it arrive
        # after the first worker has committed its result. Cross-process
        # callers remain protected by the durable execution ledger below.
        with self._inflight_lock:
            if request.idempotency_key in self._inflight_keys:
                raise AIError("AI_REQUEST_IN_PROGRESS", status_code=409)
            self._inflight_keys.add(request.idempotency_key)
        try:
            return self._execute(db, principal, request, settings=settings, provider=provider)
        finally:
            with self._inflight_lock:
                self._inflight_keys.discard(request.idempotency_key)

    def _execute(
        self,
        db: Session,
        principal: AuthenticatedPrincipal,
        request: SkillExecutionRequest,
        *,
        settings: Settings | None = None,
        provider: Any | None = None,
    ) -> dict[str, Any]:
        settings = settings or get_settings()
        if not principal.user_id:
            raise AIError("AI_ACTOR_REQUIRED", status_code=403)
        skill = self.registry.resolve(request.skill_id, request.skill_version, request.skill_manifest_hash)
        if request.scope_type.upper() not in {value.upper() for value in skill.manifest.allowed_scope_types}:
            raise AIError("AI_SKILL_SCOPE_NOT_ALLOWED", status_code=403)
        if request.target_entity_type.upper() != request.scope_type.upper() and request.scope_type.upper() == "PROJECT":
            raise AIError("AI_SCOPE_TARGET_MISMATCH", status_code=403)

        from .policy import authorize_ai_request

        try:
            authorize_ai_request(
                db,
                principal,
                purpose_value=request.purpose,
                execution_mode_value=request.execution_mode,
                target_entity_type_value=request.target_entity_type,
                target_entity_id=request.target_entity_id,
                synthetic_only=settings.synthetic_only,
                real_data_allowed=settings.real_data_allowed or settings.ai_real_content_allowed,
                require_environment_synthetic=False,
            )
            compiled = compile_context(
                db,
                {
                    "correlation_id": request.correlation_id,
                    "actor_user_id": principal.user_id,
                    "scope_type": request.scope_type,
                    "scope_id": request.scope_id,
                    "project_id": request.project_id,
                    "context_schema_version": request.context_schema_version,
                    "policy_version": request.policy_version,
                    "synthetic_provider": provider is not None,
                    "skill_manifest": skill.manifest,
                    "sources": list(request.sources),
                },
            )
            if not compiled.items:
                raise AIError("AI_CONTEXT_EMPTY", status_code=422)
            proposal_real_content = (
                settings.ai_proposal_real_content_allowed
                and skill.manifest.owning_module == "BD_PROPOSAL"
            )
            if compiled.contains_sensitive_data or (not compiled.synthetic_only and not proposal_real_content):
                raise AIError("AI_REAL_CONTENT_NOT_AUTHORIZED", status_code=403)
            _verify_snapshot(db, request, skill, compiled)
            provider_input = _provider_input(skill, compiled)
            # The deterministic acceptance provider consumes the canonical
            # JSON string and must not be charged/budgeted for vision parts.
            # Hosted Azure execution receives the transient multimodal parts.
            provider_input_content = _provider_input_content(provider_input, compiled) if provider is None else None
            request_fingerprint = _request_fingerprint(request, skill, compiled, principal)
            db.commit()
        except AIError:
            db.rollback()
            raise
        except IntelligenceContractError as exc:
            db.rollback()
            raise AIError(exc.code, status_code=403) from exc
        except HTTPException as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            raise AIError(str(detail.get("code", "AI_CONTEXT_AUTHORIZATION_FAILED")), status_code=exc.status_code) from exc
        except Exception as exc:
            db.rollback()
            raise AIError("AI_CONTEXT_COMPILATION_FAILED", status_code=409) from exc

        reservation_db = self.dependencies.session_factory()
        reservation = None
        try:
            replay = _replay_if_possible(reservation_db, request, request_fingerprint, principal.user_id)
            if replay is not None:
                reservation_db.rollback()
                return replay
            reservation = reserve_execution(
                reservation_db,
                settings=settings,
                idempotency_key=request.idempotency_key,
                correlation_id=request.correlation_id,
                actor_user_id=principal.user_id,
                auth_mode=principal.auth_mode,
                purpose=request.purpose,
                execution_mode=request.execution_mode,
                project_id=compiled.project_id or request.project_id or request.scope_id,
                target_entity_type=request.target_entity_type,
                target_entity_id=request.target_entity_id,
                architecture_version=AI_ARCHITECTURE.architecture_version,
                policy_version=request.policy_version,
                context_fingerprint=compiled.context_hash,
                request_fingerprint=request_fingerprint,
                provider="AZURE_OPENAI_RESPONSES",
                provider_region=settings.ai_azure_openai_region,
                deployment_name=settings.ai_azure_openai_deployment,
                model_name=settings.ai_azure_openai_expected_model,
                model_version=settings.ai_azure_openai_expected_version,
                citation_count=0,
                provider_input=provider_input,
                scope_type=request.scope_type.upper(),
                scope_id=request.scope_id,
                owning_module=skill.manifest.owning_module,
                skill_id=skill.manifest.skill_id,
                skill_version=skill.manifest.version,
                skill_manifest_hash=skill.manifest.manifest_hash,
                synthetic_only=compiled.synthetic_only,
                provider_input_content=provider_input_content,
            )
            reserve_audit(
                reservation_db,
                ledger=reservation.ledger,
                actor_type="ENTRA_USER" if principal.auth_mode == "ENTRA" else "DEV_USER",
            )
            reservation_db.commit()
        except AIError:
            reservation_db.rollback()
            raise
        except Exception as exc:
            reservation_db.rollback()
            if isinstance(exc, OperationalError) and "database is locked" in str(exc).lower():
                raise AIError("AI_REQUEST_IN_PROGRESS", status_code=409) from exc
            raise AIError("AI_LEDGER_RESERVATION_FAILED", status_code=503) from exc
        finally:
            reservation_db.close()

        try:
            gateway = self.gateway_factory(settings, provider=provider)
            result = gateway.execute(
                skill,
                provider_input=provider_input,
                max_output_tokens=settings.ai_max_output_tokens,
                context_synthetic_proven=compiled.synthetic_only,
                context_contains_sensitive_data=compiled.contains_sensitive_data,
                real_content_authorized=proposal_real_content,
                provider_input_content=provider_input_content,
            )
            output = skill.output.validator(result.payload)
            citations = validate_compiled_citations(output, compiled, skill.output)
            output_json = output.model_dump(mode="json")
            if len(json.dumps(output_json, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) > 64 * 1024:
                raise AIError("AI_STRUCTURED_OUTPUT_VALIDATION_FAILED", status_code=502)
            output_hash = stable_hash(output_json)
            estimated_cost = (
                result.usage.input_tokens * settings.ai_input_price_usd_per_1m_tokens / 1_000_000
                + result.usage.output_tokens * settings.ai_output_price_usd_per_1m_tokens / 1_000_000
            )
        except AIError as exc:
            self._finalize_failure(reservation.ledger.id, request, principal, exc.code, reservation.owner_token, reservation.generation)
            raise
        except Exception as exc:
            self._finalize_failure(reservation.ledger.id, request, principal, "AI_PROVIDER_RESPONSE_INVALID", reservation.owner_token, reservation.generation)
            raise AIError("AI_PROVIDER_RESPONSE_INVALID") from exc

        final_db = self.dependencies.session_factory()
        try:
            ledger = final_db.get(AIExecutionLedger, reservation.ledger.id)
            if ledger is None or ledger.status != "RESERVED":
                raise AIError("AI_LEDGER_FINALIZATION_FAILED", status_code=500)
            work_product = create_ai_work_product(
                final_db,
                {
                    "idempotency_key": f"work-product:{request.idempotency_key}",
                    "correlation_id": request.correlation_id,
                    "execution_ledger_id": ledger.id,
                    "context_snapshot_id": compiled.context_snapshot_id,
                    "owning_module": skill.manifest.owning_module,
                    "skill_id": skill.manifest.skill_id,
                    "skill_version": skill.manifest.version,
                    "skill_manifest_hash": skill.manifest.manifest_hash,
                    "scope_type": request.scope_type.upper(),
                    "scope_id": request.scope_id,
                    "project_id": compiled.project_id,
                    "target_entity_type": request.target_entity_type,
                    "target_entity_id": request.target_entity_id,
                    "output_class": skill.manifest.output_class,
                    "structured_output_json": output_json,
                    "output_hash": output_hash,
                    "data_classification": compiled.data_classification,
                    "contains_sensitive_data": compiled.contains_sensitive_data,
                    "state": "CURRENT",
                    "citation_count": len(citations),
                },
            )
            bind_work_product_dependencies(final_db, work_product)
            for citation in citations:
                citation_payload = dict(citation)
                citation_payload["work_product_id"] = work_product.id
                citation_payload["citation_hash"] = stable_hash(citation_payload)
                record_intelligence_citation(final_db, citation_payload)
            try:
                finalize_current_work_product(final_db, work_product=work_product)
            except IntelligenceContractError as exc:
                # Preserve the valid provider response as historical evidence,
                # but never expose it as a current result.
                work_product.state = "STALE"
                ledger.error_code = exc.code
                audit(final_db, correlation_id=request.correlation_id, event_type="AI_CONTEXT_CHANGED_DURING_EXECUTION", entity_type="AIWorkProduct", entity_id=work_product.id, actor_id=principal.user_id, metadata={"ledger_id": ledger.id, "provider_response_valid": True, "currentness_lost": True})
                finalize_success(
                    final_db,
                    ledger_id=ledger.id,
                    correlation_id=request.correlation_id,
                    actor_id=principal.user_id,
                    actor_type="ENTRA_USER" if principal.auth_mode == "ENTRA" else "DEV_USER",
                    usage=result.usage,
                    estimated_cost=estimated_cost,
                    output_fingerprint=output_hash,
                    citation_count=len(citations),
                    provider_response_id=result.response_id,
                    reservation_owner_token=reservation.owner_token,
                    reservation_generation=reservation.generation,
                )
                final_db.commit()
                raise AIError(P07_CONTEXT_CHANGED, status_code=409) from exc
            finalize_success(
                final_db,
                ledger_id=ledger.id,
                correlation_id=request.correlation_id,
                actor_id=principal.user_id,
                actor_type="ENTRA_USER" if principal.auth_mode == "ENTRA" else "DEV_USER",
                usage=result.usage,
                estimated_cost=estimated_cost,
                output_fingerprint=output_hash,
                citation_count=len(citations),
                provider_response_id=result.response_id,
                reservation_owner_token=reservation.owner_token,
                reservation_generation=reservation.generation,
            )
            final_db.commit()
        except IntelligenceContractError as exc:
            final_db.rollback()
            self._finalize_failure(reservation.ledger.id, request, principal, exc.code, reservation.owner_token, reservation.generation)
            raise AIError(exc.code, status_code=500) from exc
        except AIError as exc:
            final_db.rollback()
            if getattr(exc, "code", None) == P07_CONTEXT_CHANGED:
                raise
            self._finalize_failure(reservation.ledger.id, request, principal, "AI_LEDGER_FINALIZATION_FAILED", reservation.owner_token, reservation.generation)
            raise
        except Exception as exc:
            final_db.rollback()
            self._finalize_failure(reservation.ledger.id, request, principal, "AI_LEDGER_FINALIZATION_FAILED", reservation.owner_token, reservation.generation)
            raise AIError("AI_LEDGER_FINALIZATION_FAILED", status_code=500) from exc
        finally:
            final_db.close()

        return {
            "execution_id": reservation.ledger.id,
            "work_product_id": work_product.id,
            "status": "SUCCEEDED",
            "replayed": False,
            "skill_id": skill.manifest.skill_id,
            "skill_version": skill.manifest.version,
            "skill_manifest_hash": skill.manifest.manifest_hash,
            "context_snapshot_id": compiled.context_snapshot_id,
            "output_class": skill.manifest.output_class,
            "output": output_json,
            "output_hash": output_hash,
            "citations": list(citations),
            "citation_count": len(citations),
            "draft_only": skill.manifest.output_class == "DRAFT",
            "human_review_required": True,
            "canonical_state_mutated": False,
            "protected_action_count": 0,
        }

    def _finalize_failure(
        self,
        ledger_id: str,
        request: SkillExecutionRequest,
        principal: AuthenticatedPrincipal,
        code: str,
        owner_token: str,
        generation: int,
    ) -> None:
        final_db = self.dependencies.session_factory()
        try:
            finalize_failure(
                final_db,
                ledger_id=ledger_id,
                correlation_id=request.correlation_id,
                actor_id=principal.user_id,
                actor_type="ENTRA_USER" if principal.auth_mode == "ENTRA" else "DEV_USER",
                code=code,
                reservation_owner_token=owner_token,
                reservation_generation=generation,
            )
            final_db.commit()
        except Exception as exc:
            final_db.rollback()
            raise AIError("AI_LEDGER_FINALIZATION_FAILED", status_code=500) from exc
        finally:
            final_db.close()


def execute_skill(
    db: Session,
    principal: AuthenticatedPrincipal,
    request: SkillExecutionRequest,
    *,
    settings: Settings | None = None,
    provider: Any | None = None,
) -> dict[str, Any]:
    return SkillRuntime().execute(db, principal, request, settings=settings, provider=provider)
