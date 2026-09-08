"""Explicit ACA user-assigned managed-identity token acquisition."""

from __future__ import annotations

import base64
import binascii
import json
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from ..config.settings import Settings
from .errors import AIError


def _claims(token: str) -> dict[str, object]:
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    encoded = parts[1] + ("=" * (-len(parts[1]) % 4))
    try:
        value = json.loads(base64.urlsafe_b64decode(encoded).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        return {}
    return value if isinstance(value, dict) else {}


def _guid_equal(left: object, right: str) -> bool:
    return str(left or "").lower() == right.lower()


def _approved_audience(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.rstrip("/").lower()
    return normalized in {
        "https://cognitiveservices.azure.com",
        "https://azure.cognitiveservices.azure.com",
    } or normalized.endswith(".cognitiveservices.azure.com")


def _approved_foundry_audience(value: object) -> bool:
    return isinstance(value, str) and value.rstrip("/").lower() == "https://ai.azure.com"


def _acquire_token(settings: Settings, *, resource: str, audience_check) -> str:
    endpoint = os.getenv("IDENTITY_ENDPOINT", "").strip()
    header_value = os.getenv("IDENTITY_HEADER", "").strip()
    if not endpoint or not header_value:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503)
    parsed = urlsplit(endpoint)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"resource": resource, "client_id": settings.ai_uami_client_id, "api-version": "2019-08-01"})
    request_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    try:
        response = httpx.get(request_url, headers={"X-IDENTITY-HEADER": header_value}, timeout=settings.ai_identity_timeout_seconds, follow_redirects=False)
    except httpx.TimeoutException as exc:
        raise AIError("AI_PROVIDER_TIMEOUT", status_code=504) from exc
    except httpx.HTTPError as exc:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503) from exc
    if response.status_code in {401, 403} or response.status_code >= 400:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503)
    try:
        token = response.json()["access_token"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503) from exc
    claims = _claims(str(token))
    if not (_guid_equal(claims.get("oid"), settings.ai_uami_principal_id) and _guid_equal(claims.get("tid"), settings.ai_azure_tenant_id) and audience_check(claims.get("aud"))):
        raise AIError("AI_PROVIDER_IDENTITY_TOKEN_MISMATCH", status_code=503)
    return str(token)


def acquire_ai_token(settings: Settings) -> str:
    endpoint = os.getenv("IDENTITY_ENDPOINT", "").strip()
    header_value = os.getenv("IDENTITY_HEADER", "").strip()
    if not endpoint or not header_value:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503)
    parsed = urlsplit(endpoint)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({"resource": "https://cognitiveservices.azure.com", "client_id": settings.ai_uami_client_id, "api-version": "2019-08-01"})
    request_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    try:
        response = httpx.get(request_url, headers={"X-IDENTITY-HEADER": header_value}, timeout=settings.ai_identity_timeout_seconds, follow_redirects=False)
    except httpx.TimeoutException as exc:
        raise AIError("AI_PROVIDER_TIMEOUT", status_code=504) from exc
    except httpx.HTTPError as exc:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503) from exc
    if response.status_code in {401, 403}:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503)
    if response.status_code >= 400:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503)
    try:
        token = response.json()["access_token"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AIError("AI_PROVIDER_IDENTITY_DENIED", status_code=503) from exc
    claims = _claims(str(token))
    if not (_guid_equal(claims.get("oid"), settings.ai_uami_principal_id) and _guid_equal(claims.get("tid"), settings.ai_azure_tenant_id) and _approved_audience(claims.get("aud"))):
        raise AIError("AI_PROVIDER_IDENTITY_TOKEN_MISMATCH", status_code=503)
    return str(token)


def acquire_foundry_project_token(settings: Settings) -> str:
    """Acquire a dedicated UAMI token for the Microsoft Foundry audience."""

    return _acquire_token(settings, resource="https://ai.azure.com", audience_check=_approved_foundry_audience)
