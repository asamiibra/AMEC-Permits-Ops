"""Synthetic-only bridge host client for isolated G10 technical readiness."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from azure.identity import ManagedIdentityCredential
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .schemas.bridge_intake import BridgePackageIn
from .services.bridge_intake import canonical_signature_payload


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    fixture_path = Path(os.getenv("G10_BRIDGE_FIXTURE_PATH", "/workspace/backend/app/fixtures/g10_bridge_fixture.txt"))
    before = fixture_path.stat()
    content = fixture_path.read_bytes()
    after = fixture_path.stat()
    before_hash = _sha(content)
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or before_hash != _sha(fixture_path.read_bytes()):
        raise RuntimeError("G10_SOURCE_MUTATION_DETECTED")

    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(os.environ["BRIDGE_SIGNING_PRIVATE_KEY_B64"], validate=True))
    attempt_id = os.getenv("G10_ATTEMPT_ID", f"g10-{uuid4().hex}")
    project_id = os.environ["G10_PROJECT_ID"]
    field_definition_id = os.environ["G10_FIELD_DEFINITION_ID"]
    payload = BridgePackageIn(
        attempt_id=attempt_id,
        source_identity="QATAR_SYNOLOGY_SYNTHETIC_FIXTURE",
        source_path_snapshot="synthetic://qatar-synology/g10_bridge_fixture.txt",
        size_bytes=len(content),
        mtime_utc=datetime.fromtimestamp(after.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        payload_sha256=before_hash,
        payload_b64=base64.b64encode(content).decode(),
        signature_b64="pending",
        source_version_token=f"g10-fixture-{before.st_mtime_ns}",
        correlation_id=f"g10-bridge-{attempt_id}",
        scope_type="PROJECT",
        scope_id=project_id,
        project_id=project_id,
        field_definition_id=field_definition_id,
        field_raw_value="SYNTHETIC_BRIDGE_CANDIDATE",
        source_filename=fixture_path.name,
        mime_type="text/plain",
    )
    payload = payload.model_copy(update={"signature_b64": base64.b64encode(private_key.sign(canonical_signature_payload(payload))).decode()})
    token = ManagedIdentityCredential(client_id=os.environ["BRIDGE_MI_CLIENT_ID"]).get_token(f"api://{os.environ['BRIDGE_API_CLIENT_ID']}/.default").token
    response = httpx.post(
        os.environ["G10_API_URL"].rstrip("/") + "/api/source-intake/bridge/packages",
        headers={"Authorization": f"Bearer {token}"},
        json=payload.model_dump(),
        timeout=30,
    )
    body = response.json() if response.content else {}
    print(json.dumps({
        "http_status": response.status_code,
        "result": body.get("result"),
        "attempt_id": attempt_id,
        "package_sha256": before_hash,
        "source_hash_before_after_equal": True,
        "source_mtime_before_after_equal": before.st_mtime_ns == after.st_mtime_ns,
        "source_size_before_after_equal": before.st_size == after.st_size,
        "verified_assertion_created": body.get("verified_assertion_created"),
        "projection_created": body.get("projection_created"),
        "error_code": (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else None,
    }, sort_keys=True))
    response.raise_for_status()


if __name__ == "__main__":
    main()
