"""Fail-closed Entra machine identity validation for the Qatar intake bridge."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from ..config.settings import get_settings


class BridgeAuthenticationError(Exception):
    """Raised when a bridge machine token cannot be trusted."""


@dataclass(frozen=True)
class BridgeIdentity:
    tenant_id: str
    client_id: str
    object_id: str
    audience: str
    role: str


def validate_bridge_claims(claims: dict[str, Any], settings) -> BridgeIdentity:
    try:
        tenant_id = str(UUID(str(claims.get("tid", ""))))
        client_id = str(UUID(str(claims.get("azp") or claims.get("appid") or "")))
        object_id = str(UUID(str(claims.get("oid", ""))))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BridgeAuthenticationError("Bridge machine identity claims are invalid") from exc

    expected_tenant = str(UUID(settings.bridge_tenant_id))
    expected_client = str(UUID(settings.bridge_client_id))
    expected_audience = settings.bridge_audience.strip()
    if tenant_id != expected_tenant:
        raise BridgeAuthenticationError("Bridge tenant is not authorized")
    if client_id != expected_client:
        raise BridgeAuthenticationError("Bridge client identity is not authorized")
    if claims.get("aud") != expected_audience:
        raise BridgeAuthenticationError("Bridge token audience is not authorized")
    if claims.get("ver") != "2.0":
        raise BridgeAuthenticationError("Bridge token must be Microsoft Entra v2")

    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = roles.split()
    if not isinstance(roles, (list, tuple, set)):
        raise BridgeAuthenticationError("Bridge token roles are invalid")
    required_role = settings.bridge_required_role.strip()
    if required_role not in roles:
        raise BridgeAuthenticationError("Bridge machine role is not authorized")

    return BridgeIdentity(
        tenant_id=tenant_id,
        client_id=client_id,
        object_id=object_id,
        audience=expected_audience,
        role=required_role,
    )


class BridgeTokenValidator:
    def __init__(self, settings, jwks_client: PyJWKClient | None = None):
        self.settings = settings
        self.tenant_id = str(UUID(settings.bridge_tenant_id))
        self.audience = settings.bridge_audience.strip()
        self.jwks_client = jwks_client or PyJWKClient(
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys",
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def validate(self, token: str) -> BridgeIdentity:
        if not token or not token.strip():
            raise BridgeAuthenticationError("Bridge bearer token is required")
        try:
            header = jwt.get_unverified_header(token.strip())
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise BridgeAuthenticationError("Bridge token signing algorithm is invalid")
            signing_key = self.jwks_client.get_signing_key_from_jwt(token.strip())
            claims = jwt.decode(
                token.strip(),
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
                options={"require": ["aud", "exp", "iat", "iss", "nbf", "oid", "tid", "ver"]},
            )
        except BridgeAuthenticationError:
            raise
        except PyJWTError as exc:
            raise BridgeAuthenticationError("Invalid bridge bearer token") from exc
        except Exception as exc:
            raise BridgeAuthenticationError("Unable to validate bridge bearer token") from exc
        return validate_bridge_claims(claims, self.settings)


@lru_cache
def get_bridge_validator() -> BridgeTokenValidator:
    return BridgeTokenValidator(get_settings())


bridge_bearer_scheme = HTTPBearer(auto_error=False)


def current_bridge_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bridge_bearer_scheme),
) -> BridgeIdentity:
    settings = get_settings()
    if settings.app_env.upper() != "PROD" or settings.source_intake_mode.upper() != "BRIDGE":
        raise HTTPException(status_code=503, detail="Bridge intake is not enabled")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bridge bearer token is required")
    try:
        return get_bridge_validator().validate(credentials.credentials)
    except BridgeAuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Invalid bridge machine identity") from exc
