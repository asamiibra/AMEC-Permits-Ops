from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from ..config.settings import Settings, get_settings


class EntraAuthenticationError(Exception):
    """Raised when a Microsoft Entra access token cannot be trusted."""


@dataclass(frozen=True)
class EntraIdentity:
    tenant_id: str
    object_id: str
    subject: str
    client_id: str
    scopes: frozenset[str]

    # Display-only claims. Never use these for authorization.
    display_name: str | None = None
    preferred_username: str | None = None


class EntraTokenValidator:
    def __init__(
        self,
        settings: Settings,
        jwks_client: PyJWKClient | None = None,
    ) -> None:
        self.settings = settings

        # Canonical GUID forms prevent case/format differences from
        # weakening tenant/client comparisons.
        self.tenant_id = str(UUID(settings.entra_tenant_id))
        self.api_client_id = str(UUID(settings.entra_api_client_id))
        self.web_client_id = str(UUID(settings.entra_web_client_id))
        self.required_scope = settings.entra_required_scope

        # A1 is intentionally single-tenant and v2-token only.
        self.issuer = (
            "https://login.microsoftonline.com/"
            f"{self.tenant_id}/v2.0"
        )
        self.jwks_uri = (
            "https://login.microsoftonline.com/"
            f"{self.tenant_id}/discovery/v2.0/keys"
        )

        # Cache the JWKS set briefly, but do not indefinitely cache
        # individual signing keys. This preserves normal key rotation.
        self.jwks_client = jwks_client or PyJWKClient(
            self.jwks_uri,
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def validate(self, token: str) -> EntraIdentity:
        if not token or not token.strip():
            raise EntraAuthenticationError(
                "Bearer token is required"
            )

        token = token.strip()

        # Reject unsupported algorithms before attempting JWKS resolution.
        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError as exc:
            raise EntraAuthenticationError(
                "Invalid Microsoft Entra access token"
            ) from exc

        if header.get("alg") != "RS256":
            raise EntraAuthenticationError(
                "Microsoft Entra access token must use RS256"
            )

        key_id = header.get("kid")
        if not isinstance(key_id, str) or not key_id.strip():
            raise EntraAuthenticationError(
                "Microsoft Entra access token is missing a signing key ID"
            )

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.api_client_id,
                issuer=self.issuer,
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "nbf",
                        "oid",
                        "scp",
                        "sub",
                        "tid",
                        "ver",
                        "azp",
                    ],
                    "strict_aud": True,
                },
            )
        except PyJWTError as exc:
            raise EntraAuthenticationError(
                "Invalid Microsoft Entra access token"
            ) from exc
        except Exception as exc:
            # Includes fail-closed JWKS retrieval/key-resolution failures.
            raise EntraAuthenticationError(
                "Unable to validate Microsoft Entra access token"
            ) from exc

        if claims.get("ver") != "2.0":
            raise EntraAuthenticationError(
                "Microsoft Entra v2 access token is required"
            )

        try:
            tenant_id = str(
                UUID(str(claims.get("tid", "")))
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise EntraAuthenticationError(
                "Access token tenant ID is invalid"
            ) from exc

        if tenant_id != self.tenant_id:
            raise EntraAuthenticationError(
                "Access token tenant is not authorized"
            )

        try:
            client_id = str(
                UUID(str(claims.get("azp", "")))
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise EntraAuthenticationError(
                "Access token client application ID is invalid"
            ) from exc

        if client_id != self.web_client_id:
            raise EntraAuthenticationError(
                "Access token client application is not authorized"
            )

        try:
            object_id = str(
                UUID(str(claims.get("oid", "")))
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise EntraAuthenticationError(
                "Access token user object ID is invalid"
            ) from exc

        subject_claim = claims.get("sub")
        if (
            not isinstance(subject_claim, str)
            or not subject_claim.strip()
        ):
            raise EntraAuthenticationError(
                "Access token does not contain a valid subject"
            )

        subject = subject_claim.strip()

        scope_claim = claims.get("scp")
        if not isinstance(scope_claim, str):
            raise EntraAuthenticationError(
                "Access token scope claim is invalid"
            )

        scopes = frozenset(
            scope
            for scope in scope_claim.split()
            if scope
        )

        if self.required_scope not in scopes:
            raise EntraAuthenticationError(
                "Required delegated API scope is missing"
            )

        display_name = claims.get("name")
        preferred_username = claims.get("preferred_username")

        return EntraIdentity(
            tenant_id=tenant_id,
            object_id=object_id,
            subject=subject,
            client_id=client_id,
            scopes=scopes,
            display_name=(
                display_name
                if isinstance(display_name, str)
                else None
            ),
            preferred_username=(
                preferred_username
                if isinstance(preferred_username, str)
                else None
            ),
        )


@lru_cache
def get_entra_validator() -> EntraTokenValidator:
    return EntraTokenValidator(get_settings())
