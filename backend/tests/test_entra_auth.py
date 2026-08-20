from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.app.auth.entra import (
    EntraAuthenticationError,
    EntraTokenValidator,
)
from backend.app.config.settings import Settings


TENANT_ID = "11111111-1111-4111-8111-111111111111"
API_CLIENT_ID = "22222222-2222-4222-8222-222222222222"
WEB_CLIENT_ID = "33333333-3333-4333-8333-333333333333"
OBJECT_ID = "44444444-4444-4444-8444-444444444444"

ISSUER = (
    "https://login.microsoftonline.com/"
    f"{TENANT_ID}/v2.0"
)


class _SigningKey:
    def __init__(self, key):
        self.key = key


class _StaticJWKClient:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _SigningKey(self.public_key)


class _FailingJWKClient:
    def get_signing_key_from_jwt(self, token):
        raise RuntimeError("Synthetic JWKS failure")


def _settings() -> Settings:
    return Settings(
        app_env="TEST",
        synthetic_only=True,
        entra_tenant_id=TENANT_ID,
        entra_api_client_id=API_CLIENT_ID,
        entra_web_client_id=WEB_CLIENT_ID,
        entra_required_scope="access_as_user",
    )


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture
def validator(private_key):
    return EntraTokenValidator(
        _settings(),
        jwks_client=_StaticJWKClient(
            private_key.public_key()
        ),
    )


def _claims(**overrides):
    now = datetime.now(timezone.utc)

    values = {
        "aud": API_CLIENT_ID,
        "exp": int(
            (now + timedelta(minutes=5)).timestamp()
        ),
        "iat": int(
            (now - timedelta(seconds=5)).timestamp()
        ),
        "iss": ISSUER,
        "nbf": int(
            (now - timedelta(seconds=5)).timestamp()
        ),
        "oid": OBJECT_ID,
        "scp": "access_as_user other.scope",
        "sub": "synthetic-subject",
        "tid": TENANT_ID,
        "ver": "2.0",
        "azp": WEB_CLIENT_ID,
        "name": "Synthetic User",
        "preferred_username": "synthetic@example.invalid",
    }

    values.update(overrides)
    return values


def _token(
    private_key,
    claims=None,
    *,
    kid="synthetic-key",
):
    headers = (
        {"kid": kid}
        if kid is not None
        else {}
    )

    return jwt.encode(
        claims or _claims(),
        private_key,
        algorithm="RS256",
        headers=headers,
    )


def test_valid_entra_token_returns_stable_identity(
    validator,
    private_key,
):
    identity = validator.validate(
        _token(private_key)
    )

    assert identity.tenant_id == TENANT_ID
    assert identity.object_id == OBJECT_ID
    assert identity.subject == "synthetic-subject"
    assert identity.client_id == WEB_CLIENT_ID
    assert "access_as_user" in identity.scopes
    assert identity.display_name == "Synthetic User"
    assert (
        identity.preferred_username
        == "synthetic@example.invalid"
    )


def test_wrong_signature_is_rejected(
    validator,
):
    other_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    token = _token(other_key)

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_expired_token_is_rejected(
    validator,
    private_key,
):
    now = datetime.now(timezone.utc)

    token = _token(
        private_key,
        _claims(
            exp=int(
                (now - timedelta(minutes=1)).timestamp()
            )
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_not_yet_valid_token_is_rejected(
    validator,
    private_key,
):
    now = datetime.now(timezone.utc)

    token = _token(
        private_key,
        _claims(
            nbf=int(
                (now + timedelta(minutes=5)).timestamp()
            )
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_wrong_issuer_is_rejected(
    validator,
    private_key,
):
    token = _token(
        private_key,
        _claims(
            iss=(
                "https://login.microsoftonline.com/"
                "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/"
                "v2.0"
            )
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_wrong_audience_is_rejected(
    validator,
    private_key,
):
    token = _token(
        private_key,
        _claims(
            aud=(
                "55555555-5555-4555-8555-"
                "555555555555"
            )
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_wrong_tenant_is_rejected(
    validator,
    private_key,
):
    token = _token(
        private_key,
        _claims(
            tid=(
                "66666666-6666-4666-8666-"
                "666666666666"
            )
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_wrong_spa_client_is_rejected(
    validator,
    private_key,
):
    token = _token(
        private_key,
        _claims(
            azp=(
                "77777777-7777-4777-8777-"
                "777777777777"
            )
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_missing_required_scope_is_rejected(
    validator,
    private_key,
):
    token = _token(
        private_key,
        _claims(
            scp="other.scope"
        ),
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_missing_object_id_is_rejected(
    validator,
    private_key,
):
    claims = _claims()
    claims.pop("oid")

    token = _token(
        private_key,
        claims,
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_non_rs256_algorithm_is_rejected(
    validator,
):
    token = jwt.encode(
        _claims(),
        "synthetic-test-secret-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": "synthetic-key"},
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_missing_signing_key_id_is_rejected(
    validator,
    private_key,
):
    token = _token(
        private_key,
        kid=None,
    )

    with pytest.raises(EntraAuthenticationError):
        validator.validate(token)


def test_jwks_failure_fails_closed(
    private_key,
):
    validator = EntraTokenValidator(
        _settings(),
        jwks_client=_FailingJWKClient(),
    )

    token = _token(private_key)

    with pytest.raises(
        EntraAuthenticationError,
        match=(
            "Unable to validate Microsoft Entra "
            "access token"
        ),
    ):
        validator.validate(token)
