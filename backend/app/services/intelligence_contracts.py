"""Persistence-only service boundary for ProposalOps Intelligence v1.

The service records candidate, context, work-product, and citation metadata.
It deliberately has no provider, retrieval, orchestration, review, or
authority-promotion dependency.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.intelligence_entities import (
    AIWorkProduct,
    CandidateAssertion,
    ContextDependency,
    ContextSnapshot,
    IntelligenceCitation,
)


SCOPE_TYPES = {"PROJECT", "MODULE", "GLOBAL", "DOCUMENT", "WORKFLOW", "ENTITY"}
DEPENDENCY_TYPES = {
    "CANDIDATE_ASSERTION",
    "DOCUMENT_VERSION",
    "EVIDENCE_ENVELOPE",
    "VERIFIED_ASSERTION",
    "MASTER_CONTENT_VERSION",
    "DEFINITION_REVISION",
    "DOMAIN_ENTITY_REVISION",
    "POLICY_VERSION",
}
OUTPUT_CLASSES = {"CANDIDATE", "ANALYSIS", "DRAFT", "RECOMMENDATION"}
WORK_PRODUCT_STATES = {"CURRENT", "STALE", "INVALID"}
CANDIDATE_STATES = {"CURRENT", "SUPERSEDED", "STALE", "REJECTED", "PROMOTED"}
FORBIDDEN_AUTHORITY = {"APPROVED", "ACCEPTED", "AUTHORIZED", "PROTECTED", "CANONICAL"}
_T = TypeVar("_T")


class IntelligenceContractError(ValueError):
    """Deterministic contract error with a machine-readable code."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def canonical_json(value: Any) -> str:
    """Return the stable identity serialization required by the contract."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _identity(payload: dict[str, Any], *derived_fields: str) -> str:
    ignored = {"id", "created_at", *derived_fields}
    return canonical_json({key: value for key, value in payload.items() if key not in ignored})


def _reject_forbidden_authority(payload: dict[str, Any]) -> None:
    for key in payload:
        if key.lower() in {"approved", "accepted", "authorized", "protected", "canonical"}:
            raise IntelligenceContractError("INTELLIGENCE_PROTECTED_SIDE_EFFECT_FORBIDDEN")


def _validate_scope(scope_type: str, scope_id: str) -> None:
    if not scope_type or not scope_id:
        raise IntelligenceContractError("INTELLIGENCE_SCOPE_REQUIRED")
    if scope_type.upper() not in SCOPE_TYPES:
        raise IntelligenceContractError("INTELLIGENCE_SCOPE_TYPE_UNSUPPORTED")


def _existing_or_new(
    db: Session,
    model: type[_T],
    idempotency_key: str,
    identity: str,
    values: dict[str, Any],
    derived_fields: tuple[str, ...] = (),
) -> _T:
    existing = db.scalar(select(model).where(model.idempotency_key == idempotency_key))
    if existing is not None:
        if getattr(existing, "_contract_identity", None) != identity:
            # The transient marker is not present after a new session, so the
            # identity is reconstructed from the persisted object below.
            persisted = {key: getattr(existing, key) for key in values if key not in {"id", "created_at"}}
            if _identity(persisted, *derived_fields) != identity:
                raise IntelligenceContractError("INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return existing
    obj = model(**values)
    obj._contract_identity = identity
    db.add(obj)
    db.flush()
    return obj


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_id: str
    version: str
    owning_module: str
    input_schema_version: str
    output_schema_version: str
    allowed_scope_types: list[str]
    allowed_context_types: list[str]
    input_trust_floor: str
    allowed_tools: list[str]
    model_policy: dict[str, Any]
    output_class: str
    canonical_write_authority: str = "NONE"
    protected_action_authority: str = "NONE"
    canonical_or_protected_authority: str = "NONE"
    review_trigger: str
    suggested_role: str | None = None
    dependency_capture: dict[str, Any]
    invalidation: dict[str, Any]
    eval_pack_version: str
    manifest_hash: str = ""

    @model_validator(mode="after")
    def validate_authority_and_hash(self) -> "SkillManifest":
        if any(
            value.upper() != "NONE"
            for value in (
                self.canonical_write_authority,
                self.protected_action_authority,
                self.canonical_or_protected_authority,
            )
        ):
            raise ValueError("INTELLIGENCE_CANONICAL_WRITE_AUTHORITY_FORBIDDEN")
        if self.manifest_hash and self.manifest_hash != manifest_hash_for(self):
            raise ValueError("INTELLIGENCE_MANIFEST_HASH_MISMATCH")
        return self


def manifest_hash_for(manifest: SkillManifest | dict[str, Any]) -> str:
    values = manifest.model_dump() if isinstance(manifest, SkillManifest) else dict(manifest)
    values.pop("manifest_hash", None)
    return stable_hash(values)


def build_skill_manifest(**values: Any) -> SkillManifest:
    draft = SkillManifest(**dict(values))
    values = draft.model_dump()
    values["manifest_hash"] = manifest_hash_for(draft)
    return SkillManifest(**values)


def create_candidate_assertion(db: Session, payload: dict[str, Any]) -> CandidateAssertion:
    values = dict(payload)
    _reject_forbidden_authority(values)
    _validate_scope(values.get("scope_type", ""), values.get("scope_id", ""))
    if values.get("status", "CURRENT") not in CANDIDATE_STATES:
        raise IntelligenceContractError("INTELLIGENCE_CANDIDATE_STATUS_UNSUPPORTED")
    if values.get("status", "CURRENT") == "PROMOTED" and not values.get("promoted_verified_assertion_id"):
        raise IntelligenceContractError("INTELLIGENCE_PROMOTION_REQUIRES_EXPLICIT_REFERENCE")
    if "value_hash" not in values:
        values["value_hash"] = stable_hash(values.get("value_json"))
    identity = _identity(values, "value_hash")
    return _existing_or_new(db, CandidateAssertion, values["idempotency_key"], identity, values, ("value_hash",))


def create_context_snapshot(db: Session, payload: dict[str, Any]) -> ContextSnapshot:
    values = dict(payload)
    _reject_forbidden_authority(values)
    _validate_scope(values.get("scope_type", ""), values.get("scope_id", ""))
    if "context_hash" not in values:
        values["context_hash"] = stable_hash({key: value for key, value in values.items() if key not in {"id", "created_at", "context_hash"}})
    identity = _identity(values, "context_hash")
    return _existing_or_new(db, ContextSnapshot, values["idempotency_key"], identity, values, ("context_hash",))


def record_context_dependency(db: Session, payload: dict[str, Any]) -> ContextDependency:
    values = dict(payload)
    if values.get("dependency_type") not in DEPENDENCY_TYPES:
        raise IntelligenceContractError("INTELLIGENCE_DEPENDENCY_TYPE_UNSUPPORTED")
    metadata = values.get("metadata_json") or {}
    if any(key.lower() in {"raw", "text", "bytes", "content", "prompt", "output"} for key in metadata):
        raise IntelligenceContractError("INTELLIGENCE_DEPENDENCY_RAW_CONTENT_FORBIDDEN")
    existing = db.scalar(
        select(ContextDependency).where(
            ContextDependency.context_snapshot_id == values["context_snapshot_id"],
            ContextDependency.dependency_type == values["dependency_type"],
            ContextDependency.dependency_id == values["dependency_id"],
            ContextDependency.dependency_version_or_hash == values["dependency_version_or_hash"],
        )
    )
    if existing is not None:
        if _identity(values) != _identity({key: getattr(existing, key) for key in values}):
            raise IntelligenceContractError("INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return existing
    obj = ContextDependency(**values)
    db.add(obj)
    db.flush()
    snapshot = db.get(ContextSnapshot, values["context_snapshot_id"])
    if snapshot is not None:
        snapshot.dependency_count = db.scalar(
            select(func.count(ContextDependency.id)).where(
                ContextDependency.context_snapshot_id == snapshot.id
            )
        ) or 0
        db.flush()
    return obj


def create_ai_work_product(db: Session, payload: dict[str, Any]) -> AIWorkProduct:
    values = dict(payload)
    _reject_forbidden_authority(values)
    _validate_scope(values.get("scope_type", ""), values.get("scope_id", ""))
    if values.get("output_class") not in OUTPUT_CLASSES:
        raise IntelligenceContractError("INTELLIGENCE_OUTPUT_CLASS_UNSUPPORTED")
    if values.get("state", "CURRENT") not in WORK_PRODUCT_STATES:
        raise IntelligenceContractError("INTELLIGENCE_WORK_PRODUCT_STATE_UNSUPPORTED")
    if "output_hash" not in values:
        values["output_hash"] = stable_hash(values.get("structured_output_json"))
    identity = _identity(values, "output_hash")
    return _existing_or_new(db, AIWorkProduct, values["idempotency_key"], identity, values, ("output_hash",))


def record_intelligence_citation(db: Session, payload: dict[str, Any]) -> IntelligenceCitation:
    values = dict(payload)
    citation_identity = _identity(values, "citation_hash")
    values.setdefault("citation_hash", stable_hash({key: value for key, value in values.items() if key not in {"id", "created_at", "citation_hash"}}))
    existing = db.scalar(
        select(IntelligenceCitation).where(
            IntelligenceCitation.work_product_id == values["work_product_id"],
            IntelligenceCitation.ordinal == values["ordinal"],
        )
    )
    if existing is not None:
        persisted = {key: getattr(existing, key) for key in values}
        if _identity(persisted, "citation_hash") != citation_identity:
            raise IntelligenceContractError("INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return existing
    obj = IntelligenceCitation(**values)
    db.add(obj)
    db.flush()
    return obj


def require_new_ledger_scope(payload: dict[str, Any]) -> None:
    """Guard used by future writers; historical rows remain nullable in metadata."""

    required = ("scope_type", "scope_id", "owning_module", "skill_id", "skill_version", "skill_manifest_hash")
    if any(not payload.get(key) for key in required):
        raise IntelligenceContractError("INTELLIGENCE_LEDGER_METADATA_REQUIRED")
    _validate_scope(payload["scope_type"], payload["scope_id"])
