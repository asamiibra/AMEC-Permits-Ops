import base64
import json
import struct

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
    connection_kwargs = {}

    db._inject_azure_sql_access_token(None, None, [], connection_kwargs)

    packed = connection_kwargs["attrs_before"][db.SQL_COPT_SS_ACCESS_TOKEN]
    token_bytes = token.encode("utf-16-le")
    assert struct.unpack("<I", packed[:4])[0] == len(token_bytes)
    assert packed[4:] == token_bytes


def test_token_claims_reject_malformed_token():
    assert db._token_claims("not-a-jwt") == {
        "aud": None,
        "oid": None,
        "tid": None,
    }
