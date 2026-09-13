"""Governed, deterministic context compilation for ProposalOps Intelligence v1.

This service resolves only explicitly registered ProposalOps sources.  It
returns minimized in-memory projections and records immutable dependency
identity through the P02 ContextSnapshot/ContextDependency contracts.  It
does not retrieve raw files, call a model, review evidence, write business
truth, or execute protected actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    AssertionStatus,
    CandidateAssertion,
    ContextDependency,
    ContextSnapshot,
    DefinitionEntry,
    DefinitionRevision,
    DocumentApprovalState,
    DocumentVersion,
    FieldDefinition,
    FieldObservation,
    MasterContentGovernanceProfile,
    MasterContentItem,
    Phase4DocumentEvidenceEnvelope,
    Project,
    Role,
    User,
    VerifiedAssertion,
)
from backend.app.services.backend_realignment import CAPABILITY_MATRIX, persona_for_role, require_capability
from backend.app.services.intelligence_contracts import (
    IntelligenceContractError,
    SkillManifest,
    create_context_snapshot,
    manifest_hash_for,
    record_context_dependency,
    stable_hash,
)
from backend.app.services.master_content import (
    canonical_master_content_candidates,
    exact_master_content_binding_check,
    resolve_master_content_purpose,
)


TRUST_RANKS = {
    "CANDIDATE": 10,
    "GOVERNED_EVIDENCE": 20,
    "VERIFIED": 30,
    "CANONICAL": 40,
}

CLASSIFICATION_RANKS = {
    "SYNTHETIC": 0,
    "INTERNAL": 10,
    "CONFIDENTIAL": 20,
    "RESTRICTED": 30,
}

_CONTEXT_TYPE_ALIASES = {
    "CANDIDATEASSERTION": "CANDIDATE_ASSERTION",
    "DOCUMENTVERSION": "DOCUMENT_VERSION",
    "PHASE4DOCUMENTEVIDENCEENVELOPE": "PHASE4_DOCUMENT_EVIDENCE_ENVELOPE",
    "VERIFIEDASSERTION": "VERIFIED_ASSERTION",
    "MASTERCONTENT": "MASTER_CONTENT",
    "DEFINITIONREVISION": "DEFINITION_REVISION",
    "DOMAINENTITYREVISION": "DOMAIN_ENTITY_REVISION",
    "POLICYVERSION": "POLICY_VERSION",
}

_FORBIDDEN_SELECTOR_KEYS = {
    "sql", "query", "table", "model", "orm", "python_import", "import_path",
    "raw_sql", "payload", "context_payload", "projection", "content", "text",
    "bytes", "prompt", "token", "secret", "authorization", "jwt",
}
_FORBIDDEN_PROJECTION_KEYS = _FORBIDDEN_SELECTOR_KEYS | {"output", "source_text", "source_bytes", "raw_text", "raw_value"}


class ContextSourceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(min_length=1, max_length=160)
    context_type: str = Field(min_length=1, max_length=100)
    selector: dict[str, Any] = Field(default_factory=dict)
    required: bool = True

    @field_validator("key")
    @classmethod
    def _normalize_key(cls, value: str) -> str:
        return value.strip()

    @field_validator("context_type")
    @classmethod
    def _normalize_context_type(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def _reject_selector_escape_hatches(self) -> "ContextSourceSpec":
        if not isinstance(self.selector, dict):
            raise ValueError("CONTEXT_SELECTOR_MUST_BE_OBJECT")
        if any(str(key).lower() in _FORBIDDEN_SELECTOR_KEYS for key in self.selector):
            raise ValueError("CONTEXT_SELECTOR_ARBITRARY_PAYLOAD_FORBIDDEN")
        return self


class ContextCompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correlation_id: str = Field(min_length=1, max_length=160)
    actor_user_id: str = Field(min_length=1, max_length=36)
    scope_type: str = Field(min_length=1, max_length=50)
    scope_id: str = Field(min_length=1, max_length=160)
    project_id: str | None = Field(default=None, max_length=36)
    context_schema_version: str = Field(min_length=1, max_length=80)
    policy_version: str = Field(min_length=1, max_length=80)
    skill_manifest: SkillManifest
    sources: list[ContextSourceSpec] = Field(default_factory=list)

    @field_validator("scope_type")
    @classmethod
    def _normalize_scope(cls, value: str) -> str:
        return value.strip().upper()


class ContextOmission(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    context_type: str
    reason: str


class CompiledContextItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    context_type: str
    dependency_type: str
    dependency_id: str
    dependency_version_or_hash: str
    trust_state: str
    currentness_state: str
    data_classification: str
    contains_sensitive_data: bool
    projection: dict[str, Any]


class CompiledContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_snapshot_id: str
    context_hash: str
    authorization_context_hash: str
    owning_module: str
    scope_type: str
    scope_id: str
    project_id: str | None
    actor_user_id: str
    actor_persona: str
    skill_id: str
    skill_version: str
    skill_manifest_hash: str
    context_schema_version: str
    policy_version: str
    items: list[CompiledContextItem]
    omissions: list[ContextOmission]
    synthetic_only: bool
    data_classification: str
    contains_sensitive_data: bool


@dataclass(frozen=True)
class _ResolvedSource:
    context_type: str
    dependency_type: str
    dependency_id: str
    dependency_version_or_hash: str
    trust_state: str
    currentness_state: str
    data_classification: str
    contains_sensitive_data: bool
    synthetic: bool
    projection: dict[str, Any]
    metadata: dict[str, Any]


class ContextResolver:
    """Controlled resolver interface used by the static registry."""

    context_type: str

    def resolve(self, compiler: "GovernedContextCompiler", request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        raise NotImplementedError


class _MethodResolver(ContextResolver):
    def __init__(self, context_type: str, method_name: str):
        self.context_type = context_type
        self.method_name = method_name

    def resolve(self, compiler: "GovernedContextCompiler", request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        return getattr(compiler, self.method_name)(request, source, capabilities)


class GovernedContextCompiler:
    """Compile authorized current context without adding an authority lane."""

    RESOLVER_REGISTRY = {
        "CANDIDATE_ASSERTION": _MethodResolver("CANDIDATE_ASSERTION", "_resolve_candidate"),
        "DOCUMENT_VERSION": _MethodResolver("DOCUMENT_VERSION", "_resolve_document_version"),
        "PHASE4_DOCUMENT_EVIDENCE_ENVELOPE": _MethodResolver("PHASE4_DOCUMENT_EVIDENCE_ENVELOPE", "_resolve_evidence_envelope"),
        "VERIFIED_ASSERTION": _MethodResolver("VERIFIED_ASSERTION", "_resolve_verified_assertion"),
        "MASTER_CONTENT": _MethodResolver("MASTER_CONTENT", "_resolve_master_content"),
        "DEFINITION_REVISION": _MethodResolver("DEFINITION_REVISION", "_resolve_definition_revision"),
        "DOMAIN_ENTITY_REVISION": _MethodResolver("DOMAIN_ENTITY_REVISION", "_resolve_domain_entity_revision"),
        "POLICY_VERSION": _MethodResolver("POLICY_VERSION", "_resolve_policy_version"),
    }

    def __init__(self, db: Session):
        self.db = db
        self._request: ContextCompileRequest | None = None
        self._actor_role: str | None = None

    @staticmethod
    def _canonical_context_type(value: str) -> str:
        normalized = value.strip().upper()
        return _CONTEXT_TYPE_ALIASES.get(normalized, normalized)

    def compile(self, request: ContextCompileRequest | dict[str, Any]) -> CompiledContext:
        if not isinstance(request, ContextCompileRequest):
            try:
                request = ContextCompileRequest.model_validate(request)
            except Exception as exc:
                raise IntelligenceContractError("CONTEXT_REQUEST_INVALID", f"CONTEXT_REQUEST_INVALID: {exc}") from exc
        self._request = request
        manifest = request.skill_manifest
        self._validate_manifest(manifest)
        user = self.db.get(User, request.actor_user_id)
        if user is None:
            raise IntelligenceContractError("CONTEXT_ACTOR_NOT_FOUND")
        if not user.active:
            raise IntelligenceContractError("CONTEXT_ACTOR_INACTIVE")
        role = user.role.value if isinstance(user.role, Role) else str(user.role)
        self._actor_role = role
        persona = persona_for_role(role)
        capabilities = set(CAPABILITY_MATRIX.get(persona, set()))
        scope_type, project_id = self._validate_scope(request, manifest)
        authorization_context_hash = stable_hash({
            "actor_user_id": user.id,
            "stored_role": role,
            "derived_persona": persona,
            "effective_capabilities": sorted(capabilities),
            "scope_type": scope_type,
            "scope_id": request.scope_id,
            "owning_module": manifest.owning_module,
            "policy_version": request.policy_version,
        })

        seen_keys: set[str] = set()
        resolved: list[tuple[ContextSourceSpec, _ResolvedSource]] = []
        omissions: list[ContextOmission] = []
        for source in request.sources:
            key = source.key.strip()
            if key in seen_keys:
                raise IntelligenceContractError("CONTEXT_SOURCE_KEY_DUPLICATE")
            seen_keys.add(key)
            context_type = self._canonical_context_type(source.context_type)
            allowed_context_types = {self._canonical_context_type(value) for value in manifest.allowed_context_types}
            if context_type not in allowed_context_types:
                raise IntelligenceContractError("CONTEXT_TYPE_NOT_ALLOWED")
            resolver = self.RESOLVER_REGISTRY.get(context_type)
            if resolver is None:
                raise IntelligenceContractError("CONTEXT_TYPE_UNSUPPORTED")
            result = resolver.resolve(self, request, source.model_copy(update={"context_type": context_type}), capabilities)
            if result is None:
                if source.required:
                    raise IntelligenceContractError("CONTEXT_REQUIRED_SOURCE_MISSING")
                omissions.append(ContextOmission(key=key, context_type=context_type, reason="ABSENT"))
                continue
            if TRUST_RANKS[result.trust_state] < TRUST_RANKS[manifest.input_trust_floor.strip().upper()]:
                raise IntelligenceContractError("CONTEXT_TRUST_FLOOR_NOT_MET")
            resolved.append((source, result))

        resolved.sort(key=lambda pair: (pair[0].key, pair[1].context_type, pair[1].dependency_type, pair[1].dependency_id))
        items = [CompiledContextItem(
            key=source.key,
            context_type=result.context_type,
            dependency_type=result.dependency_type,
            dependency_id=result.dependency_id,
            dependency_version_or_hash=result.dependency_version_or_hash,
            trust_state=result.trust_state,
            currentness_state=result.currentness_state,
            data_classification=result.data_classification,
            contains_sensitive_data=result.contains_sensitive_data,
            projection=result.projection,
        ) for source, result in resolved]
        omission_values = [item.model_dump() for item in sorted(omissions, key=lambda value: (value.key, value.context_type, value.reason))]
        hash_payload = {
            "owning_module": manifest.owning_module,
            "skill_id": manifest.skill_id,
            "skill_version": manifest.version,
            "skill_manifest_hash": manifest_hash_for(manifest),
            "scope_type": scope_type,
            "scope_id": request.scope_id,
            "project_id": project_id,
            "authorization_context_hash": authorization_context_hash,
            "context_schema_version": request.context_schema_version,
            "policy_version": request.policy_version,
            "items": [{
                "key": item.key,
                "context_type": item.context_type,
                "dependency_type": item.dependency_type,
                "dependency_id": item.dependency_id,
                "dependency_version_or_hash": item.dependency_version_or_hash,
                "trust_state": item.trust_state,
                "currentness_state": item.currentness_state,
                "projection_hash": stable_hash(item.projection),
                "data_classification": item.data_classification,
                "contains_sensitive_data": item.contains_sensitive_data,
            } for item in items],
            "omissions": omission_values,
        }
        context_hash = stable_hash(hash_payload)
        synthetic_only = bool(items) and all(result.synthetic for _, result in resolved)
        data_classification = self._highest_classification(item.data_classification for item in items)
        contains_sensitive_data = any(item.contains_sensitive_data for item in items)

        snapshot_values = {
            "idempotency_key": f"context:{context_hash}",
            "correlation_id": request.correlation_id,
            "owning_module": manifest.owning_module,
            "scope_type": scope_type,
            "scope_id": request.scope_id,
            "project_id": project_id,
            "actor_user_id": user.id,
            "actor_persona": persona,
            "skill_id": manifest.skill_id,
            "skill_version": manifest.version,
            "skill_manifest_hash": manifest_hash_for(manifest),
            "context_schema_version": request.context_schema_version,
            "policy_version": request.policy_version,
            "authorization_context_hash": authorization_context_hash,
            "context_hash": context_hash,
            "synthetic_only": synthetic_only,
        }
        dependency_values = [(source, result) for source, result in resolved]
        with self.db.begin_nested():
            existing = self.db.scalar(select(ContextSnapshot).where(ContextSnapshot.idempotency_key == snapshot_values["idempotency_key"]))
            if existing is not None:
                snapshot_values["correlation_id"] = existing.correlation_id
            snapshot = create_context_snapshot(self.db, snapshot_values)
            for source, result in dependency_values:
                record_context_dependency(self.db, {
                    "context_snapshot_id": snapshot.id,
                    "dependency_type": result.dependency_type,
                    "dependency_id": result.dependency_id,
                    "dependency_version_or_hash": result.dependency_version_or_hash,
                    "required": source.required,
                    "trust_state": result.trust_state,
                    "currentness_state_at_capture": result.currentness_state,
                    "metadata_json": {
                        "source_key": source.key,
                        "context_type": result.context_type,
                        "data_classification": result.data_classification,
                        "contains_sensitive_data": result.contains_sensitive_data,
                        **result.metadata,
                    },
                })
        return CompiledContext(
            context_snapshot_id=snapshot.id,
            context_hash=context_hash,
            authorization_context_hash=authorization_context_hash,
            owning_module=manifest.owning_module,
            scope_type=scope_type,
            scope_id=request.scope_id,
            project_id=project_id,
            actor_user_id=user.id,
            actor_persona=persona,
            skill_id=manifest.skill_id,
            skill_version=manifest.version,
            skill_manifest_hash=manifest_hash_for(manifest),
            context_schema_version=request.context_schema_version,
            policy_version=request.policy_version,
            items=items,
            omissions=sorted(omissions, key=lambda value: (value.key, value.context_type, value.reason)),
            synthetic_only=synthetic_only,
            data_classification=data_classification,
            contains_sensitive_data=contains_sensitive_data,
        )

    def _validate_manifest(self, manifest: SkillManifest) -> None:
        floor = manifest.input_trust_floor.strip().upper()
        if floor not in TRUST_RANKS:
            raise IntelligenceContractError("CONTEXT_TRUST_FLOOR_UNSUPPORTED")
        if any(str(getattr(manifest, field)).upper() != "NONE" for field in ("canonical_write_authority", "protected_action_authority", "canonical_or_protected_authority")):
            raise IntelligenceContractError("CONTEXT_AUTHORITY_MUST_BE_NONE")
        if not manifest.owning_module.strip():
            raise IntelligenceContractError("CONTEXT_OWNING_MODULE_REQUIRED")

    def _validate_scope(self, request: ContextCompileRequest, manifest: SkillManifest) -> tuple[str, str | None]:
        scope_type = request.scope_type.strip().upper()
        allowed = {value.strip().upper() for value in manifest.allowed_scope_types}
        if scope_type not in allowed:
            raise IntelligenceContractError("CONTEXT_SCOPE_TYPE_NOT_ALLOWED")
        if scope_type == "PROJECT":
            if not request.project_id or request.project_id != request.scope_id:
                raise IntelligenceContractError("CONTEXT_PROJECT_SCOPE_MISMATCH")
            if self.db.get(Project, request.project_id) is None:
                raise IntelligenceContractError("CONTEXT_PROJECT_NOT_FOUND")
            return scope_type, request.project_id
        if request.project_id is not None:
            raise IntelligenceContractError("CONTEXT_NON_PROJECT_HAS_PROJECT_ID")
        return scope_type, None

    @staticmethod
    def _validate_selector(source: ContextSourceSpec, allowed: set[str]) -> dict[str, Any]:
        selector = dict(source.selector)
        unknown = set(selector) - allowed
        if unknown:
            raise IntelligenceContractError("CONTEXT_SELECTOR_FIELD_UNSUPPORTED")
        return selector

    @staticmethod
    def _id_selector(source: ContextSourceSpec, *names: str) -> str:
        selector = dict(source.selector)
        values = [selector.get(name) for name in names if selector.get(name)]
        if len(set(values)) > 1:
            raise IntelligenceContractError("CONTEXT_SELECTOR_ID_CONFLICT")
        if not values:
            raise IntelligenceContractError("CONTEXT_SELECTOR_ID_REQUIRED")
        return str(values[0])

    def _request_scope(self, request: ContextCompileRequest) -> tuple[str, str | None]:
        return request.scope_type.strip().upper(), request.project_id

    def _check_project(self, project_id: str | None, request: ContextCompileRequest) -> None:
        scope_type, request_project_id = self._request_scope(request)
        if scope_type == "PROJECT" and project_id != request_project_id:
            raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
        if project_id is not None and scope_type != "PROJECT":
            raise IntelligenceContractError("CONTEXT_NON_PROJECT_SOURCE_SCOPE")

    def _require_capability(self, capabilities: set[str], capability: str) -> None:
        if capability not in capabilities:
            raise IntelligenceContractError("CONTEXT_SOURCE_CAPABILITY_DENIED")
        try:
            require_capability(self._actor_role or "", capability)
        except HTTPException as exc:
            raise IntelligenceContractError("CONTEXT_SOURCE_CAPABILITY_DENIED") from exc

    @staticmethod
    def _safe_projection(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise IntelligenceContractError("CONTEXT_PROJECTION_OBJECT_REQUIRED")

        def walk(node: Any) -> Any:
            if isinstance(node, dict):
                for key in node:
                    if str(key).lower() in _FORBIDDEN_PROJECTION_KEYS:
                        raise IntelligenceContractError("CONTEXT_RAW_SOURCE_FORBIDDEN")
                return {str(key): walk(child) for key, child in node.items()}
            if isinstance(node, list):
                return [walk(child) for child in node]
            if isinstance(node, (str, int, float, bool)) or node is None:
                return node
            raise IntelligenceContractError("CONTEXT_PROJECTION_VALUE_UNSUPPORTED")

        return walk(value)

    @staticmethod
    def _highest_classification(values: Any) -> str:
        classifications = [str(value).upper() for value in values]
        return max(classifications, key=lambda value: CLASSIFICATION_RANKS.get(value, 30), default="INTERNAL")

    @staticmethod
    def _synthetic_version(version: DocumentVersion) -> bool:
        metadata = version.metadata_json or {}
        return bool(metadata.get("synthetic_non_business_fixture") or metadata.get("synthetic_only") or str(version.source_path_or_reference).startswith("synthetic-"))

    def _current_document_version(self, version: DocumentVersion | None) -> None:
        if version is None or version.document is None:
            raise IntelligenceContractError("CONTEXT_CURRENTNESS_UNRESOLVED")
        if version.document.current_version_id != version.id or version.superseded_by is not None:
            raise IntelligenceContractError("CONTEXT_CURRENTNESS_NOT_CURRENT")
        if version.approval_state == DocumentApprovalState.SUPERSEDED:
            raise IntelligenceContractError("CONTEXT_CURRENTNESS_NOT_CURRENT")

    def _resolve_candidate(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        selector = self._validate_selector(source, {"id", "candidate_assertion_id"})
        candidate_id = self._id_selector(source, "id", "candidate_assertion_id")
        candidate = self.db.get(CandidateAssertion, candidate_id)
        if candidate is None:
            return None
        candidate_status = candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)
        if candidate_status != "CURRENT":
            raise IntelligenceContractError("CONTEXT_CANDIDATE_NOT_CURRENT")
        scope_type, project_id = self._request_scope(request)
        if candidate.scope_type.upper() == "PROJECT" and (scope_type != "PROJECT" or candidate.scope_id != request.scope_id):
            raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
        if candidate.subject_type.upper() == "PROJECT" and candidate.subject_id != request.scope_id:
            raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
        self._check_project(candidate.project_id, request)
        if candidate.target_module and candidate.target_module.upper() != request.skill_manifest.owning_module.upper():
            raise IntelligenceContractError("CONTEXT_CANDIDATE_MODULE_MISMATCH")
        if candidate.contains_sensitive_data:
            self._require_capability(capabilities, "PHASE4_VIEW_RESTRICTED_EVIDENCE")
        projection = self._safe_projection({
            "candidate_assertion_id": candidate.id,
            "assertion_code": candidate.assertion_code,
            "subject_type": candidate.subject_type,
            "subject_id": candidate.subject_id,
            "value": candidate.value_json,
            "confidence": candidate.confidence,
            "producer_kind": candidate.producer_kind,
        })
        version_hash = stable_hash({
            "candidate_id": candidate.id,
            "value_hash": candidate.value_hash,
            "producer_version": candidate.producer_version,
            "producer_hash": candidate.producer_hash,
            "source_document_version_id": candidate.source_document_version_id,
            "source_observation_id": candidate.source_observation_id,
            "evidence_envelope_id": candidate.evidence_envelope_id,
        })
        return _ResolvedSource(
            "CANDIDATE_ASSERTION", "CANDIDATE_ASSERTION", candidate.id, version_hash,
            "CANDIDATE", "CURRENT", candidate.data_classification.upper(), candidate.contains_sensitive_data,
            candidate.data_classification.upper() == "SYNTHETIC", projection,
            {"candidate_value_hash": candidate.value_hash, "producer_hash": candidate.producer_hash},
        )

    def _resolve_document_version(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        self._validate_selector(source, {"id", "document_version_id"})
        version = self.db.get(DocumentVersion, self._id_selector(source, "id", "document_version_id"))
        if version is None:
            return None
        self._current_document_version(version)
        self._check_project(version.document.project_id, request)
        synthetic = self._synthetic_version(version)
        return _ResolvedSource(
            "DOCUMENT_VERSION", "DOCUMENT_VERSION", version.id, version.sha256,
            "GOVERNED_EVIDENCE", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", False, synthetic,
            self._safe_projection({
                "document_version_id": version.id,
                "document_id": version.document_id,
                "version_number": version.version_number,
                "sha256": version.sha256,
                "mime_type": version.mime_type,
                "approval_state": version.approval_state.value if hasattr(version.approval_state, "value") else str(version.approval_state),
                "revision_label": version.revision_label,
                "document_date": version.document_date.isoformat() if version.document_date else None,
            }),
            {"document_id": version.document_id},
        )

    def _resolve_evidence_envelope(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        self._validate_selector(source, {"id", "evidence_envelope_id"})
        envelope = self.db.get(Phase4DocumentEvidenceEnvelope, self._id_selector(source, "id", "evidence_envelope_id"))
        if envelope is None:
            return None
        if not envelope.source_version_id:
            raise IntelligenceContractError("CONTEXT_CURRENTNESS_UNRESOLVED")
        version = self.db.get(DocumentVersion, envelope.source_version_id)
        self._current_document_version(version)
        self._check_project(version.document.project_id, request)
        if "RESTRICTED" in envelope.content_retention_class.upper():
            self._require_capability(capabilities, "PHASE4_VIEW_RESTRICTED_EVIDENCE")
        synthetic = "SYNTHETIC" in envelope.source_surface.upper() or any("SYNTHETIC" in str(value).upper() for value in (envelope.warnings_json or []))
        return _ResolvedSource(
            "PHASE4_DOCUMENT_EVIDENCE_ENVELOPE", "EVIDENCE_ENVELOPE", envelope.id, envelope.evidence_envelope_sha256,
            "GOVERNED_EVIDENCE", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", "RESTRICTED" in envelope.content_retention_class.upper(), synthetic,
            self._safe_projection({
                "evidence_envelope_id": envelope.id,
                "source_artifact_id": envelope.source_artifact_id,
                "source_version_id": envelope.source_version_id,
                "source_surface": envelope.source_surface,
                "evidence_envelope_sha256": envelope.evidence_envelope_sha256,
                "runtime_version": envelope.document_intelligence_runtime_version,
                "runtime_sha256": envelope.runtime_sha256,
                "content_retention_class": envelope.content_retention_class,
            }),
            {"source_document_version_id": envelope.source_version_id, "envelope_sha256": envelope.evidence_envelope_sha256},
        )

    def _resolve_verified_assertion(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        self._validate_selector(source, {"id", "verified_assertion_id"})
        assertion = self.db.get(VerifiedAssertion, self._id_selector(source, "id", "verified_assertion_id"))
        if assertion is None:
            return None
        assertion_status = assertion.status.value if hasattr(assertion.status, "value") else str(assertion.status)
        if assertion_status != AssertionStatus.CURRENT.value:
            raise IntelligenceContractError("CONTEXT_VERIFIED_ASSERTION_NOT_CURRENT")
        if assertion.scope_type.upper() == "PROJECT" and (request.scope_type.upper() != "PROJECT" or assertion.scope_id != request.scope_id):
            raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
        self._check_project(assertion.project_id, request)
        observation = self.db.get(FieldObservation, assertion.source_observation_id) if assertion.source_observation_id else None
        if observation is None:
            raise IntelligenceContractError("CONTEXT_CURRENTNESS_UNRESOLVED")
        version = self.db.get(DocumentVersion, observation.document_version_id)
        self._current_document_version(version)
        if observation.project_id != assertion.project_id:
            raise IntelligenceContractError("CONTEXT_SOURCE_LINEAGE_MISMATCH")
        self._check_project(version.document.project_id, request)
        definition = self.db.get(FieldDefinition, assertion.field_definition_id)
        if definition is None or not definition.active:
            raise IntelligenceContractError("CONTEXT_VERIFIED_ASSERTION_FIELD_UNRESOLVED")
        sensitive = any(token in definition.field_code.upper() for token in ("QID", "PASSPORT", "PHONE", "EMAIL", "PII"))
        if sensitive:
            self._require_capability(capabilities, "VIEW_RAW_REGULATORY_PII")
        synthetic = self._synthetic_version(version)
        projection = self._safe_projection({
            "verified_assertion_id": assertion.id,
            "assertion_code": definition.field_code,
            "subject_type": assertion.subject_type,
            "subject_id": assertion.subject_id,
            "semantic_value": assertion.semantic_value_json,
            "display_value": assertion.display_value,
            "verification_method": assertion.verification_method.value if hasattr(assertion.verification_method, "value") else str(assertion.verification_method),
        })
        version_hash = stable_hash({"assertion_id": assertion.id, "verified_at": assertion.verified_at.isoformat(), "source_observation_id": observation.id, "source_version_id": version.id, "semantic_value": assertion.semantic_value_json})
        return _ResolvedSource(
            "VERIFIED_ASSERTION", "VERIFIED_ASSERTION", assertion.id, version_hash,
            "VERIFIED", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", sensitive, synthetic, projection,
            {"source_observation_id": observation.id, "source_document_version_id": version.id},
        )

    def _resolve_master_content(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        selector = self._validate_selector(source, {"master_content_item_id", "document_version_id", "content_type", "module", "usage_type"})
        if selector.get("master_content_item_id") or selector.get("document_version_id"):
            if not selector.get("master_content_item_id") or not selector.get("document_version_id"):
                raise IntelligenceContractError("CONTEXT_MASTER_CONTENT_EXACT_BINDING_REQUIRED")
            binding = exact_master_content_binding_check(self.db, master_content_item_id=str(selector["master_content_item_id"]), document_version_id=str(selector["document_version_id"]), content_type=selector.get("content_type"))
            if not binding["valid"]:
                reason = binding["reasons"][0] if binding["reasons"] else "INVALID"
                raise IntelligenceContractError(f"CONTEXT_MASTER_CONTENT_{reason}")
            item = binding["item"]
            version = binding["version"]
        else:
            if not selector.get("module") or not selector.get("usage_type"):
                raise IntelligenceContractError("CONTEXT_MASTER_CONTENT_SELECTOR_REQUIRED")
            resolution = resolve_master_content_purpose(self.db, module=str(selector["module"]), usage_type=str(selector["usage_type"]))
            if resolution["status"] != "RESOLVED":
                raise IntelligenceContractError(f"CONTEXT_MASTER_CONTENT_{resolution['status']}")
            item = self.db.get(MasterContentItem, resolution["item"]["id"])
            version = self.db.get(DocumentVersion, item.current_document_version_id) if item and item.current_document_version_id else None
            if item is None or version is None:
                raise IntelligenceContractError("CONTEXT_MASTER_CONTENT_UNRESOLVED")
        self._current_document_version(version)
        if item.document_id != version.document_id:
            raise IntelligenceContractError("CONTEXT_MASTER_CONTENT_SOURCE_MISMATCH")
        profile = self.db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
        sensitive = bool(profile and (profile.sensitivity_class.upper() not in {"", "NONE"} or profile.contains_pii or profile.contains_signature or profile.contains_stamp or profile.contains_financial_data or profile.contains_project_specific_data))
        if sensitive:
            self._require_capability(capabilities, "MASTER_RESTRICTED_SAMPLE_VIEW")
        synthetic = self._synthetic_version(version) or str(version.source_system).upper().startswith("SYNTHETIC")
        projection = self._safe_projection({
            "master_content_item_id": item.id,
            "master_content_ref": item.ref,
            "content_type": item.content_type,
            "title": item.title,
            "document_version_id": version.id,
            "version_number": version.version_number,
            "sha256": version.sha256,
            "source_type": item.source_type_code,
        })
        return _ResolvedSource(
            "MASTER_CONTENT", "MASTER_CONTENT_VERSION", version.id, version.sha256,
            "CANONICAL", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", sensitive, synthetic, projection,
            {"master_content_item_id": item.id, "master_content_ref": item.ref},
        )

    def _resolve_definition_revision(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        self._validate_selector(source, {"id", "definition_revision_id"})
        revision = self.db.get(DefinitionRevision, self._id_selector(source, "id", "definition_revision_id"))
        if revision is None:
            return None
        definition = self.db.get(DefinitionEntry, revision.definition_id)
        if definition is None or definition.status != "ACTIVE" or definition.current_revision_id != revision.id or revision.status != "CURRENT":
            raise IntelligenceContractError("CONTEXT_DEFINITION_REVISION_NOT_CURRENT")
        projection = self._safe_projection({
            "definition_revision_id": revision.id,
            "definition_id": definition.id,
            "ref": definition.ref,
            "term": revision.term,
            "description": revision.description,
            "category": revision.category,
            "revision_number": revision.revision_number,
            "aliases": revision.aliases,
        })
        return _ResolvedSource(
            "DEFINITION_REVISION", "DEFINITION_REVISION", revision.id,
            stable_hash({"revision_id": revision.id, "revision_number": revision.revision_number, "term": revision.term, "description": revision.description, "aliases": revision.aliases}),
            "CANONICAL", "CURRENT", "INTERNAL", False, False, projection,
            {"definition_id": definition.id, "revision_number": revision.revision_number},
        )

    def _resolve_domain_entity_revision(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        selector = self._validate_selector(source, {"entity_type", "entity_id"})
        if str(selector.get("entity_type", "")).upper() != "PROJECT":
            raise IntelligenceContractError("CONTEXT_DOMAIN_ENTITY_TYPE_UNSUPPORTED")
        entity_id = str(selector.get("entity_id") or request.project_id or "")
        if not entity_id:
            raise IntelligenceContractError("CONTEXT_SELECTOR_ID_REQUIRED")
        project = self.db.get(Project, entity_id)
        if project is None:
            return None
        self._check_project(project.id, request)
        projection = self._safe_projection({
            "entity_type": "PROJECT",
            "entity_id": project.id,
            "project_number": project.project_number,
            "project_code": project.project_code,
            "project_name": project.project_name,
            "workstream": project.workstream,
            "status": project.status,
            "municipality": project.municipality,
            "permit_type": project.permit_type,
        })
        synthetic = str(project.id).lower().startswith("synthetic-") or str(project.project_code or "").upper().startswith("SYNTHETIC")
        return _ResolvedSource(
            "DOMAIN_ENTITY_REVISION", "DOMAIN_ENTITY_REVISION", project.id, stable_hash(projection),
            "CANONICAL", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", False, synthetic, projection,
            {"entity_type": "PROJECT", "entity_id": project.id},
        )

    def _resolve_policy_version(self, request: ContextCompileRequest, source: ContextSourceSpec, capabilities: set[str]) -> _ResolvedSource | None:
        selector = self._validate_selector(source, {"version"})
        version = str(selector.get("version") or request.policy_version)
        if version != request.policy_version:
            raise IntelligenceContractError("CONTEXT_POLICY_VERSION_MISMATCH")
        return _ResolvedSource(
            "POLICY_VERSION", "POLICY_VERSION", f"policy:{version}", stable_hash({"policy_version": version}),
            "CANONICAL", "CURRENT", "INTERNAL", False, False,
            self._safe_projection({"policy_version": version}), {"policy_version": version},
        )


ContextCompiler = GovernedContextCompiler


def compile_context(db: Session, request: ContextCompileRequest | dict[str, Any]) -> CompiledContext:
    return GovernedContextCompiler(db).compile(request)
