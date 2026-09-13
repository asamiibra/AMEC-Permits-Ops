"""Fail-closed helpers for the Proposal production/synthetic mode boundary."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..models import ClientAccount, DocumentVersion


def synthetic_test_mode() -> bool:
    """Synthetic fixtures are valid only in the explicit TEST environment."""
    return get_settings().app_env.upper() == "TEST"


def production_mode() -> bool:
    settings = get_settings()
    return settings.app_env.upper() in {"AZURE-PREPROD", "PROD", "PRODUCTION"} or not settings.synthetic_only


def reject_synthetic_value(value: Any, *, code: str) -> None:
    if value is None:
        return
    encoded = json.dumps(value, sort_keys=True, default=str).upper()
    if any(token in encoded for token in ("AMEC-SYN", "SYNTHETIC://", "SYN-CAPABILITY", "SYN-POLICY", "X-DEV-ROLE")):
        raise HTTPException(409, {"code": code, "reason": "SYNTHETIC_INPUT_FORBIDDEN_IN_PRODUCTION"})


def require_canonical_active_client(db: Session, client_account_id: str | None) -> ClientAccount:
    if not client_account_id:
        raise HTTPException(409, {"code": "CANONICAL_CLIENT_ACCOUNT_REQUIRED"})
    client = db.scalar(select(ClientAccount).where(ClientAccount.id == client_account_id, ClientAccount.status == "ACTIVE"))
    if not client:
        raise HTTPException(409, {"code": "CANONICAL_CLIENT_ACCOUNT_REQUIRED", "client_account_id": client_account_id})
    reject_synthetic_value(client.client_reference, code="CANONICAL_CLIENT_ACCOUNT_REQUIRED")
    reject_synthetic_value(client.data_classification, code="CANONICAL_CLIENT_ACCOUNT_REQUIRED")
    return client


def require_exact_document_version(db: Session, version_id: str | None, *, code: str) -> DocumentVersion:
    if not version_id:
        raise HTTPException(409, {"code": code})
    version = db.get(DocumentVersion, version_id)
    if not version or not version.source_path_or_reference.startswith("storage://"):
        raise HTTPException(409, {"code": code, "reason": "DURABLE_DOCUMENT_VERSION_REQUIRED"})
    if not version.sha256 or version.file_size <= 0:
        raise HTTPException(409, {"code": code, "reason": "DOCUMENT_VERSION_INTEGRITY_METADATA_REQUIRED"})
    return version


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
