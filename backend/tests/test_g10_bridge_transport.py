from __future__ import annotations

import base64
import hashlib
import json
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app.schemas.bridge_intake import BridgePackageIn
from backend.app.services.bridge_intake import canonical_signature_payload, _decode_payload, _validate_package


def _payload(private_key: Ed25519PrivateKey, content: bytes = b"synthetic-qatar-fixture") -> BridgePackageIn:
    values = {
        "attempt_id": "g10-test-attempt-001",
        "source_identity": "QATAR_SYNOLOGY_SYNTHETIC_FIXTURE",
        "source_path_snapshot": "synthetic://qatar-synology/fixture-001.bin",
        "size_bytes": len(content),
        "mtime_utc": "2026-09-11T00:00:00Z",
        "payload_sha256": hashlib.sha256(content).hexdigest(),
        "payload_b64": base64.b64encode(content).decode(),
        "signature_b64": "pending",
        "source_version_token": "fixture-v1",
        "correlation_id": "g10-test-correlation-001",
        "scope_type": "PROJECT",
        "scope_id": "project-001",
        "project_id": "project-001",
        "field_definition_id": "field-001",
        "field_raw_value": "SYNTHETIC_CANDIDATE",
    }
    unsigned = BridgePackageIn(**values)
    values["signature_b64"] = base64.b64encode(private_key.sign(canonical_signature_payload(unsigned))).decode()
    return BridgePackageIn(**values)


def test_bridge_signature_and_hash_are_checked():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes_raw()
    settings = SimpleNamespace(
        bridge_package_signing_public_key=base64.b64encode(public_key).decode(),
        bridge_allowed_source_identities="QATAR_SYNOLOGY_SYNTHETIC_FIXTURE",
        bridge_allowed_source_path_prefixes="synthetic://qatar-synology/",
        bridge_max_payload_bytes=1024,
    )
    payload = _payload(private_key)
    raw, digest = _decode_payload(payload, settings)
    _validate_package(payload, raw, settings)
    assert digest == payload.payload_sha256

    tampered = payload.model_copy(update={"field_raw_value": "TAMPERED"})
    with pytest.raises(Exception, match="BRIDGE_SIGNATURE_INVALID"):
        _validate_package(tampered, raw, settings)


def test_bridge_signature_message_is_stable():
    private_key = Ed25519PrivateKey.generate()
    first = _payload(private_key)
    second = _payload(private_key)
    assert canonical_signature_payload(first) == canonical_signature_payload(second)
