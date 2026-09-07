"""Frozen AI-D0/D1 contracts.

The model binding in this module is an architectural target only.  It is not
evidence that a hosted model is deployed, reachable, or approved for real
AMEC content.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..services.governed_retrieval import RetrievalCitation


ARCHITECTURE_CONTRACT_VERSION = "AI-D0-D1-ARCHITECTURE-1.0"
MANIFEST_CONTRACT_VERSION = "AI-CONTEXT-MANIFEST-1.0"
POLICY_VERSION = "ENGINEERING_TECHNICAL_DRAFT-1.0"
MAX_CONTEXT_ITEMS = 20
MAX_ITEM_UTF8_BYTES = 16 * 1024
MAX_CONTEXT_UTF8_BYTES = 96 * 1024


class AIExecutionMode(str, Enum):
    INTERACTIVE = "INTERACTIVE"
    BACKGROUND = "BACKGROUND"


class AIPurpose(str, Enum):
    ENGINEERING_TECHNICAL_DRAFT = "ENGINEERING_TECHNICAL_DRAFT"


class AITargetEntityType(str, Enum):
    PROJECT = "PROJECT"
    AUTHORITY_CASE = "AUTHORITY_CASE"


class AIArchitectureContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    architecture_version: Literal[ARCHITECTURE_CONTRACT_VERSION] = ARCHITECTURE_CONTRACT_VERSION
    execution_modes: tuple[AIExecutionMode, AIExecutionMode] = (
        AIExecutionMode.INTERACTIVE,
        AIExecutionMode.BACKGROUND,
    )
    auto_mode_allowed: Literal[False] = False
    hidden_interactive_background_fallback: Literal[False] = False
    provider: Literal["AZURE_OPENAI_FOUNDRY"] = "AZURE_OPENAI_FOUNDRY"
    model: Literal["gpt-5.1"] = "gpt-5.1"
    model_version: Literal["2025-11-13"] = "2025-11-13"
    deployment_type: Literal["Standard"] = "Standard"
    resource_region: Literal["uaenorth"] = "uaenorth"
    processing_boundary: Literal["UAE_NORTH_REGIONAL"] = "UAE_NORTH_REGIONAL"
    model_router_allowed: Literal[False] = False
    fallback_models: tuple[str, ...] = ()
    provider_managed_memory_allowed: Literal[False] = False
    provider_managed_threads_allowed: Literal[False] = False
    real_content_allowed: Literal[False] = False
    external_invocation_enabled: Literal[False] = False
    canonical_write_authority: Literal["ZERO"] = "ZERO"
    protected_action_authority: Literal["ZERO"] = "ZERO"
    second_rag_store: Literal[False] = False
    vector_database: Literal[False] = False
    azure_ai_search: Literal[False] = False
    agent_framework: Literal[False] = False
    provider_global_readiness_dependency: Literal[False] = False


class AIManifestPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    purpose_id: AIPurpose
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    required_capabilities: tuple[str, ...]
    real_content_allowed: Literal[False] = False
    canonical_write_authority: Literal["ZERO"] = "ZERO"
    protected_action_authority: Literal["ZERO"] = "ZERO"


class AIContextScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str
    target_entity_type: AITargetEntityType
    target_entity_id: str


class AIContextItem(BaseModel):
    """Provider-safe whitelist projection of one governed envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_domain: str
    canonical_entity_type: str
    canonical_entity_id: str
    master_content_id: str | None = None
    transactional_entity_id: str | None = None
    document_id: str | None = None
    document_version_id: str | None = None
    definition_entry_id: str | None = None
    definition_revision_id: str | None = None
    source_artifact_id: str | None = None
    source_intake_id: str | None = None
    source_currentness_state: str | None = None
    verification_state: str
    authority_source_class: str | None = None
    superseded: bool = False
    sensitivity_class: str = "NONE"
    relationship_context: dict[str, Any] = Field(default_factory=dict)
    content: str
    content_trust_class: Literal["UNTRUSTED_EVIDENCE_TEXT"] = "UNTRUSTED_EVIDENCE_TEXT"
    citation: RetrievalCitation


class AIContextManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal[MANIFEST_CONTRACT_VERSION] = MANIFEST_CONTRACT_VERSION
    architecture_version: Literal[ARCHITECTURE_CONTRACT_VERSION] = ARCHITECTURE_CONTRACT_VERSION
    policy_version: Literal[POLICY_VERSION] = POLICY_VERSION
    purpose: AIPurpose
    execution_mode: AIExecutionMode
    scope: AIContextScope
    policy: AIManifestPolicy
    retrieval_contract_version: str
    items: tuple[AIContextItem, ...]
    manifest_fingerprint: str
    canonical_write_count: Literal[0] = 0
    external_model_invocation_count: Literal[0] = 0
    real_content_egress_count: Literal[0] = 0


AI_ARCHITECTURE = AIArchitectureContract()
