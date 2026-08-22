#!/usr/bin/env python3
"""Fail-closed validation for the secret-free A1 release manifest."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def verify(document: dict) -> None:
    if document.get("repository") != "asamiibra/AMEC-Permits-Ops": raise ValueError("wrong repository")
    if not SHA.fullmatch(document.get("source_sha", "")): raise ValueError("source_sha must be a commit SHA")
    if document.get("azure", {}).get("subscription_id") != "61080f8b-16cb-4abc-bb8c-5d8e59ab15bf": raise ValueError("wrong subscription")
    if document.get("azure", {}).get("region") != "qatarcentral": raise ValueError("wrong region")
    database = document.get("database", {})
    if database.get("engine") != "postgresql" or database.get("major") != 16: raise ValueError("wrong database target")
    if database.get("migration_head") != "0059_entra_user_identity": raise ValueError("wrong migration head")
    entra = document.get("entra", {})
    if not all(GUID.fullmatch(entra.get(key, "")) for key in ("tenant_id", "api_client_id", "web_client_id")): raise ValueError("invalid Entra identifier")
    if entra["api_client_id"].lower() == entra["web_client_id"].lower(): raise ValueError("API and web IDs must differ")
    if entra.get("required_scope") != "access_as_user" or entra.get("requested_access_token_version") != 2: raise ValueError("invalid Entra token contract")
    safety = document.get("safety", {})
    if safety.get("app_env") != "AZURE-PREPROD" or safety.get("synthetic_only") is not True or safety.get("real_data_allowed") is not False or safety.get("storage_provider") != "mock" or safety.get("synology_mode") != "SYNTHETIC" or safety.get("azure_to_synology") is not False: raise ValueError("unsafe runtime mode")
    for section in ("frontend", "backend"):
        image = document.get(section, {})
        if "@sha256:" not in image.get("image_reference", ""): raise ValueError(f"{section} image must be immutable")
    if document.get("stage") == "DEPLOYED":
        for section in ("deployment_run", "browser_e2e_run", "restore_run"):
            if not document.get("evidence", {}).get(section): raise ValueError(f"missing deployed evidence: {section}")


def main() -> int:
    try:
        verify(json.loads(Path(sys.argv[1]).read_text()))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"RELEASE_MANIFEST=FAIL:{type(exc).__name__}", file=sys.stderr)
        return 1
    print("RELEASE_MANIFEST=PASS")
    return 0


if __name__ == "__main__": raise SystemExit(main())
