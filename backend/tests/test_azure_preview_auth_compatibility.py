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
PREVIEW_CLIENT_ID = "88888888-8888-4888-8888-888888888888"
THIRD_CLIENT_ID = "77777777-7777-4777-8777-777777777777"
OBJECT_ID = "44444444-4444-4444-8444-444444444444"
UAMI_CLIENT_ID = "55555555-5555-4555-8555-555555555555"
UAMI_PRINCIPAL_ID = "66666666-6666-4666-8666-666666666666"

CANONICAL_ORIGIN = "https://canonical.example.test"
PREVIEW_ORIGIN = "https://preview.example.test"
DATABASE_URL = (
    "mssql+pyodbc://sql.example.test/sqldb"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&Encrypt=yes&TrustServerCertificate=no"
)
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"


class _SigningKey:
    def __init__(self, key):
        self.key = key


class _StaticJWKClient:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _SigningKey(self.public_key)


def _azure_settings(*, preview_client_id="", origins=CANONICAL_ORIGIN):
    return Settings(
        app_env="AZURE-PREPROD",
        database_url=DATABASE_URL,
        azure_sql_auth_mode="MANAGED_IDENTITY_ACCESS_TOKEN",
        azure_sql_uami_client_id=UAMI_CLIENT_ID,
        azure_sql_uami_principal_id=UAMI_PRINCIPAL_ID,
        frontend_origins=origins,
        synthetic_only=True,
        real_data_allowed=False,
        auth_mode="ENTRA",
        entra_tenant_id=TENANT_ID,
        entra_api_client_id=API_CLIENT_ID,
        entra_web_client_id=WEB_CLIENT_ID,
        entra_preview_web_client_id=preview_client_id,
        entra_required_scope="access_as_user",
        storage_provider="mock",
        synology_mode="SYNTHETIC",
    )


def _test_settings(*, preview_client_id=""):
    return Settings(
        app_env="TEST",
        synthetic_only=True,
        entra_tenant_id=TENANT_ID,
        entra_api_client_id=API_CLIENT_ID,
        entra_web_client_id=WEB_CLIENT_ID,
        entra_preview_web_client_id=preview_client_id,
        entra_required_scope="access_as_user",
    )


def test_canonical_only_azure_preprod_is_valid(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", CANONICAL_ORIGIN)
    settings = _azure_settings()

    settings.validate_environment()

    assert settings.origins == [CANONICAL_ORIGIN]


def test_canonical_and_preview_azure_preprod_are_valid(monkeypatch):
    origins = f"{CANONICAL_ORIGIN},{PREVIEW_ORIGIN}"
    monkeypatch.setenv("FRONTEND_ORIGINS", origins)
    settings = _azure_settings(
        preview_client_id=PREVIEW_CLIENT_ID,
        origins=origins,
    )

    settings.validate_environment()

    assert settings.origins == [CANONICAL_ORIGIN, PREVIEW_ORIGIN]
    assert len(settings.origins) == 2
    assert len(set(settings.origins)) == 2


@pytest.mark.parametrize(
    "preview_client_id",
    [
        "not-a-guid",
        WEB_CLIENT_ID,
        API_CLIENT_ID,
    ],
)
def test_preview_client_id_is_valid_and_distinct(monkeypatch, preview_client_id):
    monkeypatch.setenv(
        "FRONTEND_ORIGINS",
        f"{CANONICAL_ORIGIN},{PREVIEW_ORIGIN}",
    )
    settings = _azure_settings(
        preview_client_id=preview_client_id,
        origins=f"{CANONICAL_ORIGIN},{PREVIEW_ORIGIN}",
    )

    with pytest.raises(ValueError, match="ENTRA_PREVIEW_WEB_CLIENT_ID"):
        settings.validate_environment()


@pytest.mark.parametrize(
    "origins",
    [
        CANONICAL_ORIGIN,
        f"{CANONICAL_ORIGIN},{PREVIEW_ORIGIN},{CANONICAL_ORIGIN}",
        f"{CANONICAL_ORIGIN},{CANONICAL_ORIGIN}",
    ],
)
def test_preview_mode_rejects_wrong_or_duplicate_origin_cardinality(
    monkeypatch,
    origins,
):
    monkeypatch.setenv("FRONTEND_ORIGINS", origins)
    settings = _azure_settings(
        preview_client_id=PREVIEW_CLIENT_ID,
        origins=origins,
    )

    with pytest.raises(ValueError, match="FRONTEND_ORIGINS"):
        settings.validate_environment()


@pytest.mark.parametrize(
    "invalid_origin",
    [
        "https://*.example.test",
        "https://localhost:3000",
        "http://preview.example.test",
        "https://preview.example.test/path",
        "https://preview.example.test/?query=1",
        "https://preview.example.test/#fragment",
    ],
)
def test_preview_mode_preserves_exact_https_origin_guards(
    monkeypatch,
    invalid_origin,
):
    origins = f"{CANONICAL_ORIGIN},{invalid_origin}"
    monkeypatch.setenv("FRONTEND_ORIGINS", origins)
    settings = _azure_settings(
        preview_client_id=PREVIEW_CLIENT_ID,
        origins=origins,
    )

    with pytest.raises(ValueError, match="FRONTEND_ORIGINS"):
        settings.validate_environment()


def test_prod_rejects_preview_client_at_start_of_validation():
    settings = Settings(
        app_env="PROD",
        entra_preview_web_client_id=PREVIEW_CLIENT_ID,
    )

    with pytest.raises(ValueError, match="ENTRA_PREVIEW_WEB_CLIENT_ID"):
        settings.validate_environment()


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def canonical_validator(private_key):
    return EntraTokenValidator(
        _test_settings(),
        jwks_client=_StaticJWKClient(private_key.public_key()),
    )


@pytest.fixture
def preview_validator(private_key):
    return EntraTokenValidator(
        _test_settings(preview_client_id=PREVIEW_CLIENT_ID),
        jwks_client=_StaticJWKClient(private_key.public_key()),
    )


def _claims(**overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "aud": API_CLIENT_ID,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int((now - timedelta(seconds=5)).timestamp()),
        "iss": ISSUER,
        "nbf": int((now - timedelta(seconds=5)).timestamp()),
        "oid": OBJECT_ID,
        "scp": "access_as_user other.scope",
        "sub": "synthetic-subject",
        "tid": TENANT_ID,
        "ver": "2.0",
        "azp": WEB_CLIENT_ID,
    }
    claims.update(overrides)
    return claims


def _token(private_key, claims=None, *, algorithm="RS256"):
    signing_key = (
        private_key
        if algorithm == "RS256"
        else "synthetic-test-secret-at-least-32-bytes"
    )
    return jwt.encode(
        claims or _claims(),
        signing_key,
        algorithm=algorithm,
        headers={"kid": "synthetic-key"},
    )


def test_canonical_azp_is_accepted_and_identity_client_id_is_exact(
    canonical_validator,
    private_key,
):
    identity = canonical_validator.validate(_token(private_key))

    assert identity.client_id == WEB_CLIENT_ID


def test_preview_azp_is_accepted_and_identity_client_id_is_exact(
    preview_validator,
    private_key,
):
    identity = preview_validator.validate(
        _token(private_key, _claims(azp=PREVIEW_CLIENT_ID))
    )

    assert identity.client_id == PREVIEW_CLIENT_ID


@pytest.mark.parametrize("client_id", [THIRD_CLIENT_ID, API_CLIENT_ID])
def test_third_party_and_api_azp_are_rejected(
    preview_validator,
    private_key,
    client_id,
):
    with pytest.raises(EntraAuthenticationError):
        preview_validator.validate(
            _token(private_key, _claims(azp=client_id))
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": THIRD_CLIENT_ID},
        {"scp": "other.scope"},
        {"tid": THIRD_CLIENT_ID},
    ],
)
def test_wrong_audience_scope_and_tenant_are_rejected(
    canonical_validator,
    private_key,
    overrides,
):
    with pytest.raises(EntraAuthenticationError):
        canonical_validator.validate(_token(private_key, _claims(**overrides)))


def test_non_rs256_is_rejected(canonical_validator, private_key):
    with pytest.raises(EntraAuthenticationError):
        canonical_validator.validate(
            _token(private_key, algorithm="HS256")
        )


def test_authorized_browser_client_set_is_exact_frozenset(private_key):
    validator = EntraTokenValidator(
        _test_settings(preview_client_id=PREVIEW_CLIENT_ID),
        jwks_client=_StaticJWKClient(private_key.public_key()),
    )

    assert isinstance(validator.authorized_browser_client_ids, frozenset)
    assert validator.authorized_browser_client_ids == frozenset(
        {WEB_CLIENT_ID, PREVIEW_CLIENT_ID}
    )
    assert len(validator.authorized_browser_client_ids) == 2
