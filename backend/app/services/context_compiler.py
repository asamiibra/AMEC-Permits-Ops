"""Governed, deterministic context compilation for ProposalOps Intelligence v1.

This service resolves only explicitly registered ProposalOps sources.  It
returns minimized in-memory projections and records immutable dependency
identity through the P02 ContextSnapshot/ContextDependency contracts.  It
does not retrieve raw files, call a model, review evidence, write business
truth, or execute protected actions.
"""

from __future__ import annotations

import base64
import io
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import (
    AssertionStatus,
    CandidateAssertion,
    Contract,
    ContractAdminEvidence,
    ContractRevision,
    ContractTemplateSnapshot,
    ContextDependency,
    ContextSnapshot,
    DefinitionEntry,
    DefinitionRevision,
    DocumentApprovalState,
    DocumentVersion,
    ClientAccount,
    FieldDefinition,
    FieldObservation,
    MasterContentGovernanceProfile,
    MasterContentItem,
    Phase4DocumentEvidenceEnvelope,
    Opportunity,
    Project,
    ProposalAcceptedRevision,
    ProposalRevision,
    ProposalLpoReconciliation,
    Role,
    User,
    VerifiedAssertion,
)
from backend.app.config.settings import get_settings, repo_root
from backend.app.services.backend_realignment import CAPABILITY_MATRIX, persona_for_role, require_capability
from backend.app.services.intelligence_contracts import (
    IntelligenceContractError,
    SkillManifest,
    create_context_snapshot,
    manifest_hash_for,
    record_context_dependency,
    stable_hash,
)
from backend.app.services.intelligence_foundation import ensure_builtin_policy
from backend.app.services.master_content import (
    canonical_master_content_candidates,
    exact_master_content_binding_check,
    resolve_master_content_purpose,
)
from backend.app.storage import DocumentStorageService, create_binary_store


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
    synthetic_provider: bool = False
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
        policy = ensure_builtin_policy(self.db, request.policy_version)

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
        governance_dependencies = [
            ("SKILL_MANIFEST", f"skill:{manifest.skill_id}:{manifest.version}", manifest_hash_for(manifest), {"manifest_hash": manifest_hash_for(manifest)}),
            ("POLICY_VERSION", policy.id, policy.immutable_hash, {"policy_id": policy.id, "policy_version": policy.version}),
        ]
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
            "policy_id": policy.id,
            "policy_hash": policy.immutable_hash,
            "governance_dependencies": governance_dependencies,
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
        # The local Content Library acceptance provider may operate on an
        # INTERNAL definition revision that is deliberately created in the
        # synthetic environment. Keep this explicit and provider-scoped; a
        # real gateway call can never claim this override.
        if (
            not synthetic_only
            and request.synthetic_provider
            and resolved
            and all(result.context_type == "DEFINITION_REVISION" and result.data_classification == "INTERNAL" for _, result in resolved)
        ):
            synthetic_only = True
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
            "policy_id": policy.id,
            "policy_hash": policy.immutable_hash,
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
            existing_identities = {
                (result.dependency_type, result.dependency_id, result.dependency_version_or_hash)
                for _source, result in dependency_values
            }
            for dependency_type, dependency_id, dependency_hash, metadata in governance_dependencies:
                if (dependency_type, dependency_id, dependency_hash) in existing_identities:
                    continue
                record_context_dependency(self.db, {
                    "context_snapshot_id": snapshot.id,
                    "dependency_type": dependency_type,
                    "dependency_id": dependency_id,
                    "dependency_version_or_hash": dependency_hash,
                    "required": True,
                    "trust_state": "CANONICAL",
                    "currentness_state_at_capture": "CURRENT",
                    "metadata_json": {"source_key": "__governance__", **metadata},
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
        if scope_type == "PROPOSAL":
            proposal = self.db.get(Opportunity, request.scope_id)
            if proposal is None:
                raise IntelligenceContractError("CONTEXT_PROPOSAL_NOT_FOUND")
            if request.project_id is not None and proposal.project_id != request.project_id:
                raise IntelligenceContractError("CONTEXT_PROJECT_SCOPE_MISMATCH")
            return scope_type, proposal.project_id
        if scope_type in {"CONTRACT", "CONTRACT_REVISION"}:
            contract = self.db.get(Contract, request.scope_id)
            if contract is None:
                raise IntelligenceContractError("CONTEXT_CONTRACT_NOT_FOUND")
            if request.project_id is not None and contract.project_id != request.project_id:
                raise IntelligenceContractError("CONTEXT_PROJECT_SCOPE_MISMATCH")
            return scope_type, contract.project_id
        if scope_type == "MASTER_CONTENT_ITEM":
            item = self.db.get(MasterContentItem, request.scope_id)
            if item is None:
                raise IntelligenceContractError("CONTEXT_MASTER_CONTENT_ITEM_NOT_FOUND")
            if request.project_id is not None:
                raise IntelligenceContractError("CONTEXT_NON_PROJECT_HAS_PROJECT_ID")
            return scope_type, None
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
        if scope_type == "PROPOSAL" and project_id != request_project_id:
            raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
        if scope_type in {"CONTRACT", "CONTRACT_REVISION"} and project_id not in {None, request_project_id}:
            raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
        if project_id is not None and scope_type not in {"PROJECT", "PROPOSAL", "CONTRACT", "CONTRACT_REVISION"}:
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

    @staticmethod
    def _version_bytes(version: DocumentVersion) -> bytes:
        """Read a verified source object without exposing its locator/content.

        Proposal V1 is the only runtime that asks the compiler for bounded
        source excerpts.  The storage service still verifies the immutable
        SHA-256 before any bytes are parsed.
        """
        if version.source_path_or_reference.startswith("storage://"):
            with DocumentStorageService(create_binary_store()).read_verified(version) as stream:
                return stream.read()
        if version.synthetic_content is not None:
            return version.synthetic_content
        # Local TEST/DEVELOPMENT source uploads are persisted by the
        # provisional intake SOR adapter as files under the configured mock
        # systems root. Read those bytes only after constraining the resolved
        # path to that root and verifying the immutable version hash/size.
        # Production and hosted runtimes must use storage:// or DB-backed
        # synthetic_content and never accept an arbitrary filesystem path.
        settings = get_settings()
        if str(settings.app_env).upper() in {"TEST", "DEV", "DEVELOPMENT"}:
            configured_root = Path(settings.mock_systems_root)
            if not configured_root.is_absolute():
                configured_root = repo_root() / configured_root
            try:
                allowed_root = configured_root.resolve(strict=True)
                resolved_path = Path(version.source_path_or_reference).resolve(strict=True)
                resolved_path.relative_to(allowed_root)
            except (FileNotFoundError, OSError, RuntimeError, ValueError):
                resolved_path = None
            if resolved_path is not None and resolved_path.is_file():
                content = resolved_path.read_bytes()
                if len(content) == version.file_size and hashlib.sha256(content).hexdigest() == version.sha256:
                    return content
        raise IntelligenceContractError("CONTEXT_SOURCE_CONTENT_UNAVAILABLE")

    @staticmethod
    def _bounded_text(value: str, limit: int = 1600) -> tuple[str, bool]:
        value = re.sub(r"\x00", "", value).strip()
        if len(value) <= limit:
            return value, False
        return value[:limit], True

    @staticmethod
    def _vision_image(content: bytes, mime: str) -> tuple[str | None, int | None, int | None]:
        """Create a bounded data URL for the Responses vision input part.

        The original verified artifact stays in managed storage. Only a low
        detail, size-capped rendition is placed in the transient provider
        request, and the projection retains its source hash for provenance.
        """
        try:
            from PIL import Image  # type: ignore
            image = Image.open(io.BytesIO(content))
            width, height = image.size
            image.load()
            image.thumbnail((768, 768))
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            for quality in (60, 45, 30):
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
                encoded = buffer.getvalue()
                if len(encoded) <= 20_000:
                    return f"data:image/jpeg;base64,{base64.b64encode(encoded).decode('ascii')}", width, height
        except Exception:
            return None, None, None
        return None, None, None

    @classmethod
    def _vision_pdf_pages(cls, content: bytes, *, max_pages: int = 3) -> tuple[list[dict[str, Any]], int | None]:
        """Render a bounded sample of PDF pages for transient vision input.

        The original PDF remains the governed evidence object.  Page renders
        are deliberately short-lived, size-capped derivatives used only by a
        multimodal provider so scanned permits, letters, plans, and photos do
        not disappear merely because text extraction returned nothing.
        """
        renderer = shutil.which("pdftoppm")
        if not renderer:
            return [], None
        try:
            from pypdf import PdfReader  # type: ignore
            page_count = len(PdfReader(io.BytesIO(content)).pages)
        except Exception:
            page_count = None
        page_limit = max(1, min(max_pages, page_count or max_pages))
        pages: list[dict[str, Any]] = []
        try:
            with tempfile.TemporaryDirectory(prefix="proposalops-pdf-vision-") as directory:
                source = Path(directory) / "source.pdf"
                prefix = Path(directory) / "page"
                source.write_bytes(content)
                subprocess.run(
                    [renderer, "-jpeg", "-scale-to", "768", "-f", "1", "-l", str(page_limit), str(source), str(prefix)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                )
                for page_path in sorted(Path(directory).glob("page-*.jpg")):
                    match = re.search(r"-(\d+)\.jpg$", page_path.name)
                    if not match:
                        continue
                    image_data_url, width, height = cls._vision_image(page_path.read_bytes(), "image/jpeg")
                    if not image_data_url:
                        continue
                    pages.append({
                        "page_number": int(match.group(1)),
                        "image_data_url": image_data_url,
                        "image_width": width,
                        "image_height": height,
                    })
        except (OSError, subprocess.SubprocessError, ValueError):
            return [], page_count
        return pages, page_count

    @classmethod
    def _proposal_source_projection(cls, version: DocumentVersion, *, source_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a small, source-grounded projection for Proposal V1.

        Raw bytes, full paths and transport locators never enter the model
        input.  DOCX blocks retain their immutable anchor/hash preconditions so
        a returned change plan can only target the exact baseline package.
        Other readable sources receive a bounded UTF-8 excerpt and media
        metadata. Images retain their source hash while a low-detail,
        size-capped rendition is available only to the transient vision input.
        """
        metadata = source_metadata if source_metadata is not None else (version.metadata_json if isinstance(version.metadata_json, dict) else {})
        # Master Content stores the semantic template contract under
        # engineering_metadata; flatten it into the bounded projection so the
        # provider can prove which canonical baseline it received.
        nested_metadata = metadata.get("engineering_metadata") if isinstance(metadata.get("engineering_metadata"), dict) else {}
        metadata = {**nested_metadata, **metadata}
        projection: dict[str, Any] = {
            "document_version_id": version.id,
            "document_id": version.document_id,
            "version_number": version.version_number,
            "sha256": version.sha256,
            "mime_type": version.mime_type,
            "approval_state": version.approval_state.value if hasattr(version.approval_state, "value") else str(version.approval_state),
            "revision_label": version.revision_label,
            "document_date": version.document_date.isoformat() if version.document_date else None,
            "source_filename": version.source_filename,
            "source_relative_path": metadata.get("source_relative_path"),
            "template_baseline": bool(metadata.get("template_baseline")),
            "template_id": metadata.get("template_id"),
            "template_version": metadata.get("template_version"),
            "template_contract_version": metadata.get("template_contract_version"),
            "template_purpose": metadata.get("template_purpose"),
            "source_role": metadata.get("source_role"),
            "logical_category": metadata.get("logical_category") or "OTHER_UNCLASSIFIED",
            "logical_category_source": metadata.get("logical_category_source") or "AUTO_CLASSIFIED",
        }
        content = cls._version_bytes(version)
        mime = (version.mime_type or "").lower()
        filename = (version.source_filename or "").lower()
        if filename.endswith(".docx") or "wordprocessingml.document" in mime:
            # Import locally to keep the compiler's package boundary clear.
            from .proposal_document_package import document_map
            all_blocks = document_map(content)
            # The governed Owner template intentionally leaves table value
            # cells empty. Keep those native Word paragraphs in the baseline
            # projection so the anchored mutation engine can insert generated
            # values without rebuilding the table. Other evidence documents
            # retain the bounded non-empty projection used historically.
            blocks = all_blocks if metadata.get("template_id") == "AMEC-PROPOSAL-V1-TECHNICAL-REPORT" else [item for item in all_blocks if item.text.strip()]
            # Every editable paragraph is represented. The prior first-40
            # slice silently made later sections invisible to Proposal V1.
            editable = [
                {"anchor": item.anchor, "expected_xml_hash": item.xml_hash, "value": item.text[:500], "document_order": index}
                for index, item in enumerate(blocks)
            ]
            excerpt, truncated = cls._bounded_text("\n".join(item.text for item in blocks), 2400)
            projection.update({"source_excerpt": excerpt, "source_excerpt_truncated": truncated, "editable_blocks": editable, "document_coverage": {"state": "FULL_EDITABLE_BLOCKS", "block_count": len(editable)}})
        elif mime.startswith("text/") or filename.endswith((".txt", ".csv", ".json", ".xml", ".eml", ".md")):
            try:
                value = content.decode("utf-8", errors="replace")
            except Exception:
                value = ""
            excerpt, truncated = cls._bounded_text(value)
            projection.update({"source_excerpt": excerpt, "source_excerpt_truncated": truncated})
        elif mime == "application/pdf" or filename.endswith(".pdf"):
            # PDF parsing is intentionally optional.  Keep a deterministic
            # marker when no text extractor is present so the model can still
            # cite the verified artifact without receiving binary gibberish.
            text = ""
            try:
                from pypdf import PdfReader  # type: ignore
                reader = PdfReader(io.BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                text = ""
            excerpt, truncated = cls._bounded_text(text)
            vision_pages, page_count = cls._vision_pdf_pages(content)
            media: dict[str, Any] = {
                "mime_type": version.mime_type,
                "byte_size": version.file_size,
                "sha256": version.sha256,
                "vision_state": "READY" if vision_pages else "UNAVAILABLE",
                "vision_pages": vision_pages,
            }
            if page_count is not None:
                media["page_count"] = page_count
            projection.update({
                "source_excerpt": excerpt,
                "source_excerpt_truncated": truncated,
                "source_text_state": "EXTRACTED" if excerpt else "BINARY_ARTIFACT_ONLY",
                "source_media": media,
            })
        else:
            media: dict[str, Any] = {"mime_type": version.mime_type, "byte_size": version.file_size, "sha256": version.sha256}
            if mime.startswith("image/") or filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
                image_data_url, width, height = cls._vision_image(content, mime)
                media["vision_state"] = "READY" if image_data_url else "UNAVAILABLE"
                if width is not None and height is not None:
                    media["image_width"] = width
                    media["image_height"] = height
                if image_data_url:
                    media["image_data_url"] = image_data_url
            projection.update({"source_excerpt": "", "source_excerpt_truncated": False, "source_media": media})
        return cls._safe_projection(projection)

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
        if request.scope_type.upper() in {"CONTRACT", "CONTRACT_REVISION"}:
            metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
            contract = self.db.get(Contract, request.scope_id)
            current_revision_id = contract.current_revision_id if contract else None
            linked_template = self.db.scalar(select(ContractTemplateSnapshot.id).where(
                ContractTemplateSnapshot.contract_id == request.scope_id,
                ContractTemplateSnapshot.contract_revision_id == current_revision_id,
                ContractTemplateSnapshot.document_version_id == version.id,
            ))
            linked_evidence = self.db.scalar(select(ContractAdminEvidence.id).where(
                ContractAdminEvidence.contract_id == request.scope_id,
                ContractAdminEvidence.contract_revision_id == current_revision_id,
                ContractAdminEvidence.document_version_id == version.id,
            ))
            if metadata.get("contract_id") != request.scope_id and not (linked_template or linked_evidence):
                raise IntelligenceContractError("CONTEXT_CONTRACT_SOURCE_SCOPE_MISMATCH")
        synthetic = self._synthetic_version(version)
        metadata = version.metadata_json if isinstance(version.metadata_json, dict) else {}
        data_classification = str(metadata.get("sensitivity_class") or ("SYNTHETIC" if synthetic else "INTERNAL")).upper()
        contains_sensitive = bool(metadata.get("contains_sensitive_data") or data_classification in {"CONFIDENTIAL", "RESTRICTED"})
        is_proposal = request.skill_manifest.owning_module.upper() == "BD_PROPOSAL"
        # Resolve the same Owner source decision ledger used by Source
        # Workspace and Active Proposal Sources before compiling AI context.
        effective_metadata = dict(metadata)
        if is_proposal and request.scope_type.upper() == "PROPOSAL":
            proposal = self.db.get(Opportunity, request.scope_id)
            workspace = (proposal.proposal_fields_json or {}).get("source_workspace") if proposal else {}
            from .proposal_source_workspace import source_decision_for_version, source_category
            decision = source_decision_for_version(
                self.db,
                source_project_identity=(workspace or {}).get("source_project_identity"),
                version=version,
            )
            if decision is not None:
                effective_metadata["logical_category"] = source_category(version, decision)
                effective_metadata["logical_category_source"] = decision.category_origin or "OWNER"
        projection = self._proposal_source_projection(version, source_metadata=effective_metadata) if is_proposal else self._safe_projection({
            "document_version_id": version.id,
            "document_id": version.document_id,
            "version_number": version.version_number,
            "sha256": version.sha256,
            "mime_type": version.mime_type,
            "approval_state": version.approval_state.value if hasattr(version.approval_state, "value") else str(version.approval_state),
            "revision_label": version.revision_label,
            "document_date": version.document_date.isoformat() if version.document_date else None,
        })
        return _ResolvedSource(
            "DOCUMENT_VERSION", "DOCUMENT_VERSION", version.id, version.sha256,
            "GOVERNED_EVIDENCE", "CURRENT", data_classification, contains_sensitive,
            synthetic, projection, {"document_id": version.document_id, "source_relative_path": metadata.get("source_relative_path"), "logical_category": effective_metadata.get("logical_category") or "OTHER_UNCLASSIFIED", "logical_category_source": effective_metadata.get("logical_category_source") or "AUTO_CLASSIFIED"},
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
            "category_id": item.category_id,
            "category_label": item.category.label if item.category else None,
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
        entity_type = str(selector.get("entity_type", "")).upper()
        if entity_type == "CONTRACT":
            if request.scope_type.upper() not in {"CONTRACT", "CONTRACT_REVISION"}:
                raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
            entity_id = str(selector.get("entity_id") or request.scope_id)
            if entity_id != request.scope_id:
                raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
            contract = self.db.get(Contract, entity_id)
            if contract is None:
                return None
            revision = getattr(contract, "current_revision_id", None)
            current_revision = self.db.get(ContractRevision, revision) if revision else None
            revision_identity = current_revision.content_hash if current_revision else stable_hash({"contract_id": contract.id, "updated_at": contract.updated_at.isoformat()})
            self._check_project(contract.project_id, request)
            projection = self._safe_projection({
                "entity_type": "CONTRACT", "entity_id": contract.id,
                "contract_reference": contract.contract_reference, "status": contract.status,
                "stage": contract.stage, "project_id": contract.project_id,
                "current_revision_id": current_revision.id if current_revision else None,
                "current_revision_number": current_revision.revision_number if current_revision else None,
                "current_revision_identity": revision_identity,
            })
            synthetic = str(contract.id).lower().startswith("synthetic-") or bool(contract.project_id and str(contract.project_id).lower().startswith("synthetic-"))
            return _ResolvedSource(
                "DOMAIN_ENTITY_REVISION", "DOMAIN_ENTITY_REVISION", contract.id, revision_identity,
                "CANONICAL", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", False, synthetic,
                projection, {"domain_entity": "CONTRACT", "current_revision_id": current_revision.id if current_revision else None},
            )
        if entity_type == "PROPOSAL":
            if request.scope_type.upper() != "PROPOSAL":
                raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
            entity_id = str(selector.get("entity_id") or request.scope_id)
            if entity_id != request.scope_id:
                raise IntelligenceContractError("CONTEXT_CROSS_PROJECT_SOURCE")
            proposal = self.db.get(Opportunity, entity_id)
            if proposal is None:
                return None
            accepted = self.db.scalar(select(ProposalAcceptedRevision).where(
                ProposalAcceptedRevision.proposal_id == proposal.id,
                ProposalAcceptedRevision.status == "ACCEPTED",
            ).order_by(ProposalAcceptedRevision.revision_number.desc(), ProposalAcceptedRevision.accepted_at.desc()))
            working = self.db.scalar(select(ProposalRevision).where(
                ProposalRevision.proposal_id == proposal.id,
                ProposalRevision.status == "DRAFT",
            ).order_by(ProposalRevision.revision_number.desc()))
            accepted_required = request.skill_manifest.purpose in {
                "PROPOSAL_LPO_VARIANCE_ANALYSIS",
                "PROPOSAL_HANDOFF_PREFLIGHT",
            }
            if accepted_required and accepted is None:
                raise IntelligenceContractError("CONTEXT_PROPOSAL_ACCEPTED_REVISION_REQUIRED")
            if not accepted_required and working is None and accepted is None:
                # Intake and pre-acceptance skills operate on the current
                # Proposal working state, which is the immutable intake
                # projection until a mutable working revision is created.
                revision_identity = stable_hash({"proposal_id": proposal.id, "proposal_fields": proposal.proposal_fields_json, "updated_at": proposal.updated_at.isoformat()})
            else:
                selected_revision = accepted if accepted_required and accepted else (working if working else accepted)
                revision_identity = (
                    f"{selected_revision.id}:{selected_revision.revision_number}:{selected_revision.content_hash}"
                    if selected_revision is not None
                    else stable_hash({"proposal_id": proposal.id, "proposal_fields": proposal.proposal_fields_json, "updated_at": proposal.updated_at.isoformat()})
                )
            self._check_project(proposal.project_id, request)
            project = self.db.get(Project, proposal.project_id) if proposal.project_id else None
            client = self.db.get(ClientAccount, proposal.client_account_id) if proposal.client_account_id else None
            lpo = self.db.scalar(select(ProposalLpoReconciliation).where(
                ProposalLpoReconciliation.proposal_id == proposal.id,
                ProposalLpoReconciliation.accepted_revision_id == accepted.id if accepted else False,
            ).order_by(ProposalLpoReconciliation.compared_at.desc()))
            synthetic = proposal.fixture_classification == "SYNTHETIC_OWNER_TEST"
            projection = self._safe_projection({
                "entity_type": "PROPOSAL",
                "entity_id": proposal.id,
                "proposal_reference": proposal.opportunity_reference,
                "title": proposal.title,
                "status": proposal.status,
                "project_id": proposal.project_id,
                "project_number": proposal.canonical_project_reference or proposal.provisional_reference,
                "project_name": project.project_name if project is not None else None,
                "client_name": (client.display_name or client.legal_name) if client is not None else None,
                "working_revision_id": working.id if working else None,
                "working_revision_number": working.revision_number if working else None,
                "working_revision_hash": working.content_hash if working else None,
                "accepted_revision_id": accepted.id if accepted else None,
                "accepted_revision_number": accepted.revision_number if accepted else None,
                "accepted_revision_hash": accepted.content_hash if accepted else None,
                "current_revision_identity": revision_identity,
                "lpo_evidence_id": lpo.id if lpo else None,
                "lpo_result": lpo.result if lpo else None,
            })
            return _ResolvedSource(
                "DOMAIN_ENTITY_REVISION", "DOMAIN_ENTITY_REVISION", proposal.id,
                f"{revision_identity}",
                "CANONICAL", "CURRENT", "SYNTHETIC" if synthetic else "INTERNAL", False, synthetic, projection,
                {"domain_entity": "PROPOSAL", "fixture_classification": proposal.fixture_classification, "accepted_revision_required": accepted_required, "working_revision_id": working.id if working else None, "accepted_revision_id": accepted.id if accepted else None, "lpo_evidence_id": lpo.id if lpo else None},
            )
        if entity_type != "PROJECT":
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
        policy = ensure_builtin_policy(self.db, version)
        return _ResolvedSource(
            "POLICY_VERSION", "POLICY_VERSION", policy.id, policy.immutable_hash,
            "CANONICAL", "CURRENT", "INTERNAL", False, False,
            self._safe_projection({"policy_version": version, "policy_id": policy.id, "policy_hash": policy.immutable_hash}), {"policy_version": version, "policy_id": policy.id},
        )


ContextCompiler = GovernedContextCompiler


def compile_context(db: Session, request: ContextCompileRequest | dict[str, Any]) -> CompiledContext:
    return GovernedContextCompiler(db).compile(request)
