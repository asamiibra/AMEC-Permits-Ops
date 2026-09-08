"""The immutable deployment binding used by the live D3 runtime.

``AI_ARCHITECTURE`` remains the historical D0/D1 contract.  This module is
the separate, deployment-backed runtime binding so the historical target is
never mistaken for evidence of the hosted model that is actually serving
requests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from ..config.settings import Settings


@dataclass(frozen=True)
class AIRuntimeBinding:
    provider: str
    endpoint: str
    deployment: str
    model: str
    version: str
    region: str
    deployment_type: str
    synthetic_only: bool
    real_content_allowed: bool

    @classmethod
    def from_settings(cls, settings: "Settings") -> "AIRuntimeBinding":
        return cls(
            provider="AZURE_OPENAI_RESPONSES",
            endpoint=settings.ai_azure_openai_endpoint.rstrip("/"),
            deployment=settings.ai_azure_openai_deployment,
            model=settings.ai_azure_openai_expected_model,
            version=settings.ai_azure_openai_expected_version,
            region=settings.ai_azure_openai_region,
            deployment_type=settings.ai_azure_openai_deployment_type,
            synthetic_only=settings.synthetic_only,
            real_content_allowed=settings.ai_real_content_allowed or settings.real_data_allowed,
        )

    def validate(self) -> None:
        if not self.endpoint:
            raise ValueError("AI_AZURE_OPENAI_ENDPOINT is required")
        endpoint = urlsplit(self.endpoint)
        if endpoint.scheme.lower() != "https" or not endpoint.hostname or endpoint.path.rstrip("/"):
            raise ValueError("AI endpoint must be an HTTPS Azure OpenAI resource origin")
        host = endpoint.hostname.lower()
        if not (host.endswith(".openai.azure.com") or host.endswith(".cognitiveservices.azure.com")):
            raise ValueError("AI endpoint host is not an approved Azure OpenAI host")
        if not self.deployment or not self.model or not self.version or not self.region:
            raise ValueError("AI runtime model binding is incomplete")
        if self.deployment_type not in {"Standard", "GlobalStandard", "DataZoneStandard"}:
            raise ValueError("AI runtime deployment type is not synchronous")
        if not self.synthetic_only or self.real_content_allowed:
            raise ValueError("AI runtime must remain synthetic-only")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
