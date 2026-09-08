"""The sole D2 hosted-model provider: raw Azure OpenAI Responses REST."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

from ..config.settings import Settings
from .errors import AIError
from .identity import acquire_ai_token, acquire_foundry_project_token
from .structured_output import PROVIDER_JSON_SCHEMA


@dataclass(frozen=True)
class AIProviderRequest:
    provider_input: str
    max_output_tokens: int


@dataclass(frozen=True)
class AIProviderUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class AIProviderResult:
    response_id: str
    payload: dict[str, Any]
    usage: AIProviderUsage
    provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    access_mode: str | None = None
    requested_model_name: str | None = None
    requested_model_version: str | None = None
    requested_model_id: str | None = None
    observed_response_model: str | None = None


class AIProvider(Protocol):
    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult: ...


def _approved_endpoint(value: str) -> str:
    parsed = urlsplit(value.rstrip("/"))
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment:
        raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
    host = parsed.hostname.lower()
    if not (host.endswith(".openai.azure.com") or host.endswith(".cognitiveservices.azure.com")):
        raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
    return value.rstrip("/")


def _usage(value: Any) -> AIProviderUsage:
    if not isinstance(value, dict):
        raise AIError("AI_PROVIDER_RESPONSE_INVALID")
    try:
        input_tokens = int(value["input_tokens"])
        output_tokens = int(value["output_tokens"])
        total_tokens = int(value["total_tokens"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AIError("AI_PROVIDER_RESPONSE_INVALID") from exc
    if min(input_tokens, output_tokens, total_tokens) < 0 or total_tokens != input_tokens + output_tokens:
        raise AIError("AI_PROVIDER_RESPONSE_INVALID")
    return AIProviderUsage(input_tokens, output_tokens, total_tokens)


def _output_text(body: dict[str, Any]) -> str:
    if not isinstance(body, dict):
        raise AIError("AI_PROVIDER_RESPONSE_INVALID")
    if body.get("status") == "incomplete" or body.get("incomplete_details"):
        raise AIError("AI_PROVIDER_RESPONSE_INVALID")
    for item in body.get("output", ()):
        if not isinstance(item, dict) or item.get("type") != "message":
            raise AIError("AI_PROVIDER_RESPONSE_INVALID")
        for content in item.get("content", ()):
            if not isinstance(content, dict) or content.get("type") not in {"output_text", "text"}:
                raise AIError("AI_PROVIDER_RESPONSE_INVALID")
            if content.get("refusal"):
                raise AIError("AI_PROVIDER_RESPONSE_INVALID")
            text = content.get("text")
            if isinstance(text, str) and text:
                return text
    raise AIError("AI_PROVIDER_RESPONSE_INVALID")


class AzureOpenAIResponsesProvider:
    def __init__(self, settings: Settings, *, token_provider=acquire_ai_token, http_client_factory=httpx.Client):
        self.settings = settings
        self.token_provider = token_provider
        self.http_client_factory = http_client_factory

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        endpoint = _approved_endpoint(self.settings.ai_azure_openai_endpoint)
        token = self.token_provider(self.settings)
        body = {
            "model": self.settings.ai_azure_openai_deployment,
            "store": False,
            "max_output_tokens": request.max_output_tokens,
            "input": request.provider_input,
            "tools": [],
            "text": {"format": {"type": "json_schema", "name": "technical_methodology_draft", "strict": True, "schema": PROVIDER_JSON_SCHEMA}},
        }
        timeout = httpx.Timeout(connect=self.settings.ai_provider_connect_timeout_seconds, read=self.settings.ai_provider_read_timeout_seconds, write=self.settings.ai_provider_write_timeout_seconds, pool=self.settings.ai_provider_connect_timeout_seconds)
        try:
            with self.http_client_factory(timeout=timeout, follow_redirects=False) as client:
                response = client.post(f"{endpoint}/openai/v1/responses", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        except httpx.TimeoutException as exc:
            raise AIError("AI_PROVIDER_TIMEOUT", status_code=504) from exc
        except httpx.HTTPError as exc:
            raise AIError("AI_PROVIDER_UNAVAILABLE", status_code=503) from exc
        if response.status_code == 429:
            raise AIError("AI_PROVIDER_RATE_LIMITED", status_code=503)
        if response.status_code == 404:
            raise AIError("AI_PROVIDER_DEPLOYMENT_NOT_FOUND", status_code=503)
        if response.status_code >= 500:
            raise AIError("AI_PROVIDER_UNAVAILABLE", status_code=503)
        if response.status_code >= 400:
            raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
        try:
            raw = response.json()
            text = _output_text(raw)
            payload = json.loads(text)
        except AIError:
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AIError("AI_PROVIDER_RESPONSE_INVALID") from exc
        if not isinstance(payload, dict) or not isinstance(raw.get("id"), str):
            raise AIError("AI_PROVIDER_RESPONSE_INVALID")
        return AIProviderResult(raw["id"], payload, _usage(raw.get("usage")))


def _approved_foundry_project_endpoint(value: str) -> str:
    parsed = urlsplit(value.rstrip("/"))
    path_parts = parsed.path.split("/")
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.query
        or parsed.fragment
        or not parsed.hostname.lower().endswith(".services.ai.azure.com")
        or len(path_parts) != 4
        or path_parts[:3] != ["", "api", "projects"]
        or not path_parts[3]
    ):
        raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
    return value.rstrip("/")


def _instant_model_parts(model_id: str, model_version: str) -> tuple[str, str]:
    suffix = f"-{model_version}"
    if model_id.endswith(suffix):
        return model_id[: -len(suffix)], model_version
    return model_id, model_version


def _instant_requested_model_id(model_id: str, model_version: str) -> str:
    suffix = f"-{model_version}"
    return model_id if model_id.endswith(suffix) else f"{model_id}{suffix}"


def _foundry_output_text(body: dict[str, Any]) -> str:
    if not isinstance(body, dict) or body.get("status") == "incomplete" or body.get("incomplete_details"):
        raise AIError("AI_PROVIDER_RESPONSE_INVALID")
    top_level = body.get("output_text")
    if isinstance(top_level, str) and top_level:
        return top_level
    for item in body.get("output", ()):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", ()):
            if not isinstance(content, dict) or content.get("type") not in {"output_text", "text"}:
                continue
            if content.get("refusal"):
                raise AIError("AI_PROVIDER_RESPONSE_INVALID")
            text = content.get("text")
            if isinstance(text, str) and text:
                return text
    raise AIError("AI_PROVIDER_RESPONSE_INVALID")


class FoundryProjectInstantResponsesProvider:
    """Thin Microsoft Foundry Project Instant Access Responses provider."""

    def __init__(self, settings: Settings, *, token_provider=acquire_foundry_project_token, http_client_factory=httpx.Client):
        self.settings = settings
        self.token_provider = token_provider
        self.http_client_factory = http_client_factory

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        endpoint = _approved_foundry_project_endpoint(self.settings.ai_foundry_project_endpoint)
        model_name, model_version = _instant_model_parts(self.settings.ai_instant_model_id, self.settings.ai_instant_model_version)
        requested_model_id = _instant_requested_model_id(self.settings.ai_instant_model_id, model_version)
        if not model_name or not model_version or not requested_model_id:
            raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
        token = self.token_provider(self.settings)
        body = {
            "model": requested_model_id,
            "store": False,
            "max_output_tokens": request.max_output_tokens,
            "input": request.provider_input,
            "tools": [],
            "text": {"format": {"type": "json_schema", "name": "technical_methodology_draft", "strict": True, "schema": PROVIDER_JSON_SCHEMA}},
        }
        timeout = httpx.Timeout(connect=self.settings.ai_provider_connect_timeout_seconds, read=self.settings.ai_provider_read_timeout_seconds, write=self.settings.ai_provider_write_timeout_seconds, pool=self.settings.ai_provider_connect_timeout_seconds)
        try:
            with self.http_client_factory(timeout=timeout, follow_redirects=False) as client:
                response = client.post(f"{endpoint}/openai/v1/responses", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        except httpx.TimeoutException as exc:
            raise AIError("AI_PROVIDER_TIMEOUT", status_code=504) from exc
        except httpx.HTTPError as exc:
            raise AIError("AI_PROVIDER_UNAVAILABLE", status_code=503) from exc
        if response.status_code == 429:
            raise AIError("AI_PROVIDER_RATE_LIMITED", status_code=503)
        if response.status_code in {400, 404, 422}:
            raise AIError("AI_PROVIDER_INSTANT_MODEL_UNAVAILABLE", status_code=503)
        if response.status_code >= 500:
            raise AIError("AI_PROVIDER_UNAVAILABLE", status_code=503)
        if response.status_code >= 400:
            raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
        try:
            raw = response.json()
            text = _foundry_output_text(raw)
            payload = json.loads(text)
        except AIError:
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AIError("AI_PROVIDER_RESPONSE_INVALID") from exc
        if not isinstance(payload, dict) or not isinstance(raw.get("id"), str):
            raise AIError("AI_PROVIDER_RESPONSE_INVALID")
        response_model = raw.get("model")
        if not isinstance(response_model, str) or not response_model:
            raise AIError("AI_PROVIDER_RESPONSE_MODEL_MISMATCH")
        if response_model not in {requested_model_id, model_name}:
            raise AIError("AI_PROVIDER_RESPONSE_MODEL_MISMATCH")
        return AIProviderResult(
            raw["id"],
            payload,
            _usage(raw.get("usage")),
            "MICROSOFT_FOUNDRY",
            model_name,
            model_version,
            "INSTANT",
            model_name,
            model_version,
            requested_model_id,
            response_model,
        )
