"""The sole D2 hosted-model provider: raw Azure OpenAI Responses REST."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx

from ..config.settings import Settings
from .errors import AIError
from .identity import acquire_ai_token
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
    model_name: str | None = None
    model_version: str | None = None
    access_mode: str | None = None
    latency_ms: int | None = None


class AIProvider(Protocol):
    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult: ...


def _approved_endpoint(value: str, *, access_mode: str) -> str:
    parsed = urlsplit(value.rstrip("/"))
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.query or parsed.fragment:
        raise AIError("AI_PROVIDER_REQUEST_REJECTED", status_code=503)
    host = parsed.hostname.lower()
    if access_mode == "INSTANT":
        path_parts = [part for part in parsed.path.rstrip("/").split("/") if part]
        approved = host.endswith(".services.ai.azure.com") and len(path_parts) == 3 and path_parts[:2] == ["api", "projects"]
    else:
        approved = not parsed.path and (host.endswith(".openai.azure.com") or host.endswith(".cognitiveservices.azure.com"))
    if not approved:
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
    if body.get("status") != "completed" or body.get("incomplete_details"):
        raise AIError("AI_PROVIDER_RESPONSE_INVALID")
    top_level = body.get("output_text")
    if isinstance(top_level, str) and top_level:
        return top_level
    for item in body.get("output", ()):
        # Reasoning and other non-message output items are deliberately
        # ignored.  Only final message text may cross the provider boundary.
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


class AzureOpenAIResponsesProvider:
    def __init__(self, settings: Settings, *, token_provider=acquire_ai_token, http_client_factory=httpx.Client):
        self.settings = settings
        self.token_provider = token_provider
        self.http_client_factory = http_client_factory

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        access_mode = self.settings.ai_access_mode.upper()
        endpoint = _approved_endpoint(self.settings.ai_azure_openai_endpoint, access_mode=access_mode)
        token = self.token_provider(self.settings)
        body = {
            "model": self.settings.ai_azure_openai_expected_model if access_mode == "INSTANT" else self.settings.ai_azure_openai_deployment,
            "store": False,
            "max_output_tokens": request.max_output_tokens,
            "input": request.provider_input,
            "tools": [],
            "text": {"format": {"type": "json_schema", "name": "technical_methodology_draft", "strict": True, "schema": PROVIDER_JSON_SCHEMA}},
        }
        timeout = httpx.Timeout(connect=self.settings.ai_provider_connect_timeout_seconds, read=self.settings.ai_provider_read_timeout_seconds, write=self.settings.ai_provider_write_timeout_seconds, pool=self.settings.ai_provider_connect_timeout_seconds)
        started = time.monotonic()
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
        response_model = raw.get("model")
        if not isinstance(response_model, str) or not response_model:
            raise AIError("AI_PROVIDER_RESPONSE_INVALID")
        response_version = raw.get("model_version")
        if not isinstance(response_version, str) or not response_version:
            response_version = None
        if response_version is None and len(response_model) >= 11 and response_model[-11] == "-" and response_model[-10:].count("-") == 2:
            response_model, response_version = response_model[:-11], response_model[-10:]
        if response_model != self.settings.ai_azure_openai_expected_model or response_version != self.settings.ai_azure_openai_expected_version:
            raise AIError("AI_PROVIDER_RESPONSE_MODEL_MISMATCH")
        return AIProviderResult(raw["id"], payload, _usage(raw.get("usage")), response_model, response_version, access_mode, int((time.monotonic() - started) * 1000))
