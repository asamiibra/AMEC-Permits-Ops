"""Canonical governed Model Gateway for registered Intelligence skills."""

from __future__ import annotations

from typing import Any

from ..config.settings import Settings
from .errors import AIError
from .provider import (
    AIProvider,
    AIProviderRequest,
    AIProviderResult,
    AzureOpenAIResponsesProvider,
)
from .runtime_binding import AIRuntimeBinding
from .skill_registry import SkillDefinition


_POLICY_BINDING_FIELDS = {
    "provider": "provider",
    "model": "model",
    "model_version": "version",
    "deployment": "deployment",
    "region": "region",
    "deployment_type": "deployment_type",
}


class ModelGateway:
    """One provider boundary with server-owned schemas and binding checks."""

    def __init__(self, settings: Settings, *, provider: AIProvider | None = None):
        self.settings = settings
        self.provider = provider

    def _validate_runtime_boundary(self) -> AIRuntimeBinding:
        if not self.settings.ai_feature_enabled:
            raise AIError("AI_FEATURE_DISABLED", status_code=503)
        if not self.settings.ai_external_inference_enabled:
            raise AIError("AI_EXTERNAL_INFERENCE_DISABLED", status_code=503)
        if not self.settings.ai_d4_commissioning_id.strip():
            raise AIError("AI_D4_COMMISSIONING_REQUIRED", status_code=503)
        # Global real-content switches remain prohibited.  Proposal V1 has a
        # separate, execution-scoped commissioning flag checked below after
        # skill identity and context sensitivity have been proven.
        if self.settings.real_data_allowed or self.settings.ai_real_content_allowed:
            raise AIError("AI_REAL_CONTENT_NOT_AUTHORIZED", status_code=403)
        binding = AIRuntimeBinding.from_settings(self.settings)
        try:
            binding.validate()
        except ValueError as exc:
            raise AIError("AI_RUNTIME_BINDING_INVALID", status_code=503) from exc
        return binding

    @staticmethod
    def _validate_skill_binding(skill: SkillDefinition, binding: AIRuntimeBinding) -> None:
        policy = dict(skill.manifest.model_policy or {})
        if policy.get("binding") != "D4_COMMISSIONED":
            raise AIError("AI_SKILL_MODEL_POLICY_UNCOMMISSIONED", status_code=403)
        unknown = set(policy) - {"binding", *(_POLICY_BINDING_FIELDS.keys())}
        if unknown:
            raise AIError("AI_SKILL_MODEL_POLICY_UNSUPPORTED", status_code=500)
        for policy_key, binding_attr in _POLICY_BINDING_FIELDS.items():
            if policy_key in policy and str(policy[policy_key]) != str(getattr(binding, binding_attr)):
                raise AIError("AI_SKILL_MODEL_BINDING_MISMATCH", status_code=403)

    def execute(
        self,
        skill: SkillDefinition,
        *,
        provider_input: str,
        max_output_tokens: int,
        context_synthetic_proven: bool = False,
        context_contains_sensitive_data: bool = True,
        real_content_authorized: bool = False,
        provider_input_content: list[dict[str, Any]] | None = None,
    ) -> AIProviderResult:
        binding = self._validate_runtime_boundary()
        proposal_real_content = (
            real_content_authorized
            and self.settings.ai_proposal_real_content_allowed
            and skill.manifest.owning_module == "BD_PROPOSAL"
        )
        if (
            context_contains_sensitive_data
            or self.settings.ai_real_content_allowed
            or self.settings.real_data_allowed
            or (not context_synthetic_proven and not proposal_real_content)
        ):
            raise AIError("AI_REAL_CONTENT_NOT_AUTHORIZED", status_code=403)
        self._validate_skill_binding(skill, binding)
        if skill.manifest.allowed_tools:
            # P05 establishes a deny-by-default registry.  Function calling is
            # intentionally deferred until a later skill pack proves a safe
            # read-only tool invocation contract.
            raise AIError("AI_TOOL_RUNTIME_NOT_ENABLED", status_code=403)
        request = AIProviderRequest(
            provider_input=provider_input,
            max_output_tokens=max_output_tokens,
            response_schema=skill.output.provider_schema,
            schema_name=skill.output.schema_name,
            tools=(),
            provider_input_content=provider_input_content,
        )
        active_provider = self.provider or AzureOpenAIResponsesProvider(self.settings)
        return active_provider.execute_structured(request)
