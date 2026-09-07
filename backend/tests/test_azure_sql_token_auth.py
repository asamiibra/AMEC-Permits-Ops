import base64
import json
import struct
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.dialects.mssql.pyodbc import MSDialect_pyodbc

from backend.app import db


def _unsigned_token(claims: dict[str, str]) -> str:
    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    return ".".join(
        (
            encode(b'{"alg":"none"}'),
            encode(json.dumps(claims).encode("utf-8")),
            "",
        )
    )


def test_azure_sql_token_event_packs_utf16le_access_token(monkeypatch):
    token = _unsigned_token(
        {
            "aud": db.AZURE_SQL_RESOURCE,
            "oid": "oid",
            "tid": "tid",
        }
    )
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: token)
    connection_args = [
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=sql.example;DATABASE=app;Encrypt=yes;"
        "TrustServerCertificate=no;Trusted_Connection=Yes"
    ]
    connection_kwargs = {"attrs_before": {1234: "sentinel"}}

    db._inject_azure_sql_access_token(None, None, connection_args, connection_kwargs)

    packed = connection_kwargs["attrs_before"][db.SQL_COPT_SS_ACCESS_TOKEN]
    token_bytes = token.encode("utf-16-le")
    assert struct.unpack("<I", packed[:4])[0] == len(token_bytes)
    assert packed[4:] == token_bytes
    assert connection_kwargs["attrs_before"][1234] == "sentinel"
    assert "Trusted_Connection=" not in connection_args[0]
    for forbidden in ("UID=", "PWD=", "Authentication=", "Trusted_Connection="):
        assert forbidden.lower() not in connection_args[0].lower()
    for retained in (
        "DRIVER={ODBC Driver 18 for SQL Server}",
        "SERVER=sql.example",
        "DATABASE=app",
        "Encrypt=yes",
        "TrustServerCertificate=no",
    ):
        assert retained in connection_args[0]


def test_sqlalchemy_dialect_generates_the_pre_hook_trusted_connection():
    url = make_url(
        "mssql+pyodbc://sql.example:1433/app?driver=ODBC+Driver+18+for+SQL+Server"
        "&Encrypt=yes&TrustServerCertificate=no"
    )
    connection_args, _ = MSDialect_pyodbc().create_connect_args(url)
    assert len(connection_args) == 1
    assert "Trusted_Connection=Yes" in connection_args[0]


@pytest.mark.parametrize(
    "connection_string",
    [
        "DRIVER={ODBC Driver 18 for SQL Server};UID = bad",
        "DRIVER={ODBC Driver 18 for SQL Server};Pwd = {bad;value}",
        "DRIVER={ODBC Driver 18 for SQL Server};Authentication = ActiveDirectoryMsi",
        "DRIVER={ODBC Driver 18 for SQL Server};Trusted_Connection = No",
        "DRIVER={ODBC Driver 18 for SQL Server};Trusted_Connection=Yes;Trusted_Connection=Yes",
        "DRIVER={ODBC Driver 18 for SQL Server};Trusted_Connection=Yes;Trusted_Connection=No",
    ],
)
def test_azure_sql_token_event_rejects_semantic_credential_attributes(monkeypatch, connection_string):
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: "unused")
    with pytest.raises(RuntimeError, match="forbids"):
        db._inject_azure_sql_access_token(None, None, [connection_string], {})


@pytest.mark.parametrize(
    "connection_string",
    [
        "DRIVER={ODBC Driver 18 for SQL Server;SERVER=sql.example",
        "DRIVER={ODBC Driver 18 for SQL Server};MalformedAttribute",
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER={sql.example}trailing",
    ],
)
def test_azure_sql_token_event_rejects_malformed_odbc_attributes(monkeypatch, connection_string):
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: "unused")
    with pytest.raises(RuntimeError, match="malformed"):
        db._inject_azure_sql_access_token(None, None, [connection_string], {})


def test_azure_sql_token_event_rejects_preexisting_access_token(monkeypatch):
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: "unused")
    with pytest.raises(RuntimeError, match="competing"):
        db._inject_azure_sql_access_token(
            None,
            None,
            ["DRIVER={ODBC Driver 18 for SQL Server};Trusted_Connection=Yes"],
            {"attrs_before": {db.SQL_COPT_SS_ACCESS_TOKEN: b"sentinel"}},
        )


def test_azure_sql_token_event_preserves_braced_non_authentication_values(monkeypatch):
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: "unused")
    connection_args = [
        "Driver={ODBC Driver 18 for SQL Server};"
        "Server={sql;example};Database={app};Connection Timeout=8;"
        "Trusted_Connection=Yes"
    ]
    db._inject_azure_sql_access_token(None, None, connection_args, {})
    assert connection_args[0] == (
        "Driver={ODBC Driver 18 for SQL Server};"
        "Server={sql;example};Database={app};Connection Timeout=8"
    )


def test_azure_sql_token_event_acquires_a_fresh_token_per_connection(monkeypatch):
    tokens = iter(("token-one", "token-two"))
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: next(tokens))
    first_args = ["DRIVER={ODBC Driver 18 for SQL Server};Trusted_Connection=Yes"]
    second_args = ["DRIVER={ODBC Driver 18 for SQL Server};Trusted_Connection=Yes"]
    first_kwargs = {}
    second_kwargs = {}
    db._inject_azure_sql_access_token(None, None, first_args, first_kwargs)
    db._inject_azure_sql_access_token(None, None, second_args, second_kwargs)
    assert first_kwargs["attrs_before"][db.SQL_COPT_SS_ACCESS_TOKEN] != second_kwargs["attrs_before"][db.SQL_COPT_SS_ACCESS_TOKEN]


@pytest.mark.parametrize(
    "audience",
    ["https://database.windows.net", "https://database.windows.net/"],
)
def test_azure_sql_audience_accepts_canonical_uri_forms(audience):
    assert db._is_azure_sql_audience(audience)


@pytest.mark.parametrize(
    "audience",
    [
        "https://database.windows.example/",
        "http://database.windows.net/",
        "https://database.windows.net/v1",
        "https://database.windows.net/?x=1",
        "https://database.windows.net/#fragment",
    ],
)
def test_azure_sql_audience_rejects_noncanonical_uri_forms(audience):
    assert not db._is_azure_sql_audience(audience)


def test_azure_sql_access_token_normalizes_guid_claims_and_response(monkeypatch):
    client_id = "11111111-1111-4111-8111-111111111111"
    principal_id = "22222222-2222-4222-8222-222222222222"
    tenant_id = "33333333-3333-4333-8333-333333333333"
    token = _unsigned_token(
        {
            "aud": "https://database.windows.net",
            "oid": principal_id.upper(),
            "tid": tenant_id.upper(),
        }
    )

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {"access_token": token, "client_id": client_id.upper()}
            ).encode("utf-8")

    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://identity.invalid/token")
    monkeypatch.setenv("IDENTITY_HEADER", "test-header")
    monkeypatch.setattr(
        db,
        "get_settings",
        lambda: SimpleNamespace(
            azure_sql_uami_client_id=client_id,
            azure_sql_uami_principal_id=principal_id,
            entra_tenant_id=tenant_id,
        ),
    )
    monkeypatch.setattr(db.urllib.request, "urlopen", lambda *args, **kwargs: Response())

    assert db._azure_sql_access_token() == token


@pytest.mark.parametrize(
    "claims,expected",
    [
        (
            {
                "aud": "https://database.windows.net/",
                "oid": "22222222-2222-4222-8222-222222222222",
                "tid": "33333333-3333-4333-8333-333333333333",
            },
            True,
        ),
        (
            {
                "aud": "https://database.windows.net/",
                "oid": "99999999-9999-4999-8999-999999999999",
                "tid": "33333333-3333-4333-8333-333333333333",
            },
            False,
        ),
        (
            {
                "aud": "https://database.windows.net/",
                "oid": "22222222-2222-4222-8222-222222222222",
                "tid": "99999999-9999-4999-8999-999999999999",
            },
            False,
        ),
    ],
)
def test_azure_sql_token_claim_guid_adjudication(claims, expected):
    kwargs = dict(
        principal_id="22222222-2222-4222-8222-222222222222",
        tenant_id="33333333-3333-4333-8333-333333333333",
    )
    if expected:
        db._validate_azure_sql_token_claims(claims, **kwargs)
    else:
        with pytest.raises(RuntimeError, match="claims mismatch"):
            db._validate_azure_sql_token_claims(claims, **kwargs)


def test_azure_sql_access_token_rejects_different_response_client_id(monkeypatch):
    client_id = "11111111-1111-4111-8111-111111111111"
    token = _unsigned_token(
        {
            "aud": "https://database.windows.net/",
            "oid": "22222222-2222-4222-8222-222222222222",
            "tid": "33333333-3333-4333-8333-333333333333",
        }
    )

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "access_token": token,
                    "client_id": "99999999-9999-4999-8999-999999999999",
                }
            ).encode("utf-8")

    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://identity.invalid/token")
    monkeypatch.setenv("IDENTITY_HEADER", "test-header")
    monkeypatch.setattr(
        db,
        "get_settings",
        lambda: SimpleNamespace(
            azure_sql_uami_client_id=client_id,
            azure_sql_uami_principal_id="22222222-2222-4222-8222-222222222222",
            entra_tenant_id="33333333-3333-4333-8333-333333333333",
        ),
    )
    monkeypatch.setattr(db.urllib.request, "urlopen", lambda *args, **kwargs: Response())

    with pytest.raises(RuntimeError, match="claims mismatch"):
        db._azure_sql_access_token()


def test_azure_sql_token_event_requires_one_connection_string(monkeypatch):
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: "unused")
    with pytest.raises(RuntimeError, match="exactly one ODBC"):
        db._inject_azure_sql_access_token(None, None, [], {})
    with pytest.raises(RuntimeError, match="exactly one ODBC"):
        db._inject_azure_sql_access_token(None, None, ["one", "two"], {})


@pytest.mark.parametrize("credential", ["UID=bad", "PWD=bad", "Authentication=bad", "Trusted_Connection=No"])
def test_azure_sql_token_event_rejects_remaining_credentials(monkeypatch, credential):
    monkeypatch.setattr(db, "_azure_sql_access_token", lambda: "unused")
    with pytest.raises(RuntimeError, match="forbids"):
        db._inject_azure_sql_access_token(
            None,
            None,
            ["DRIVER={ODBC Driver 18 for SQL Server};" + credential],
            {},
        )


def test_token_claims_reject_malformed_token():
    assert db._token_claims("not-a-jwt") == {
        "aud": None,
        "oid": None,
        "tid": None,
    }
