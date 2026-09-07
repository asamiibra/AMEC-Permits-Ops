#!/usr/bin/env python3
"""Fail-closed validation for the secret-free A1 release manifest."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

GUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IMMUTABLE_IMAGE = re.compile(r"^.+@sha256:([0-9a-f]{64})$")


def _required(mapping: dict[str, Any], key: str, label: str) -> Any:
    value = mapping.get(key)
    if value is None or value == "":
        raise ValueError(f"missing {label}")
    return value


def _verify_image(name: str, image: Any, source_sha: str) -> None:
    if not isinstance(image, dict):
        raise ValueError(f"{name} image is required")
    reference = _required(image, "image_reference", f"{name}.image_reference")
    match = IMMUTABLE_IMAGE.fullmatch(reference)
    if not match:
        raise ValueError(f"{name} image must use an immutable digest")
    digest = _required(image, "image_digest", f"{name}.image_digest")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError(f"{name}.image_digest is invalid")
    if match.group(1) != digest:
        raise ValueError(f"{name} image digest does not match its reference")
    release_sha = _required(image, "release_sha", f"{name}.release_sha")
    if release_sha != source_sha or not SHA1.fullmatch(release_sha):
        raise ValueError(f"{name} release_sha must equal source_sha")
    base_digest = _required(image, "base_image_digest", f"{name}.base_image_digest")
    if not isinstance(base_digest, str) or not SHA256.fullmatch(base_digest):
        raise ValueError(f"{name}.base_image_digest is invalid")


def _verify_entra(entra: dict[str, Any], deployed: bool) -> None:
    if entra.get("required_scope") != "access_as_user":
        raise ValueError("invalid Entra token scope")
    if entra.get("requested_access_token_version") != 2:
        raise ValueError("invalid Entra token version")
    keys = ("tenant_id", "api_client_id", "web_client_id")
    values = [entra.get(key) for key in keys]
    if deployed or any(value is not None for value in values):
        if not all(isinstance(value, str) and GUID.fullmatch(value) for value in values):
            raise ValueError("invalid or incomplete Entra identifiers")
        if len({value.lower() for value in values}) != len(values):
            raise ValueError("Entra identifiers must be distinct")


def _verify_evidence(evidence: Any) -> None:
    if not isinstance(evidence, dict):
        raise ValueError("deployed evidence is required")
    for key in (
        "source_ci_run",
        "iac_ci_run",
        "deployment_run",
        "browser_e2e_run",
        "restore_run",
    ):
        _required(evidence, key, f"evidence.{key}")


def verify(document: dict[str, Any], expected_source_sha: str | None = None) -> None:
    if not isinstance(document, dict):
        raise ValueError("manifest must be an object")
    if document.get("repository") != "asamiibra/AMEC-Permits-Ops":
        raise ValueError("wrong repository")
    source_sha = document.get("source_sha", "")
    if not isinstance(source_sha, str) or not SHA1.fullmatch(source_sha):
        raise ValueError("source_sha must be a commit SHA")
    if expected_source_sha is not None and source_sha != expected_source_sha:
        raise ValueError("source_sha does not match the expected release")
    stage = document.get("stage")
    if stage not in {"PREDEPLOY", "DEPLOYED"}:
        raise ValueError("invalid stage")

    azure = document.get("azure")
    if not isinstance(azure, dict):
        raise ValueError("azure section is required")
    if azure.get("subscription_id") != "61080f8b-16cb-4abc-bb8c-5d8e59ab15bf":
        raise ValueError("wrong subscription")
    if azure.get("region") != "qatarcentral":
        raise ValueError("wrong region")

    database = document.get("database")
    if not isinstance(database, dict):
        raise ValueError("database section is required")
    if database.get("engine") != "azure_sql" or database.get("major") != 16:
        raise ValueError("wrong database target")
    if database.get("migration_head") != "baseline_phase4_v36_azure_sql":
        raise ValueError("wrong migration head")

    entra = document.get("entra")
    if not isinstance(entra, dict):
        raise ValueError("entra section is required")
    _verify_entra(entra, stage == "DEPLOYED")

    safety = document.get("safety")
    if not isinstance(safety, dict):
        raise ValueError("safety section is required")
    expected_safety = {
        "app_env": "AZURE-PREPROD",
        "synthetic_only": True,
        "real_data_allowed": False,
        "storage_provider": "mock",
        "synology_mode": "SYNTHETIC",
        "azure_to_synology": False,
    }
    if any(safety.get(key) != value for key, value in expected_safety.items()):
        raise ValueError("unsafe runtime mode")

    if stage == "DEPLOYED":
        for key in (
            "resource_group",
            "frontend_site",
            "backend_site",
            "sql_server",
            "sql_database",
        ):
            _required(azure, key, f"azure.{key}")
        _verify_image("frontend", document.get("frontend"), source_sha)
        _verify_image("backend", document.get("backend"), source_sha)
        webjobs = document.get("webjobs")
        if not isinstance(webjobs, dict):
            raise ValueError("deployed webjobs are required")
        if set(webjobs) != {"worker_package_sha256"}:
            raise ValueError("deployed webjobs must contain only the worker package")
        value = _required(webjobs, "worker_package_sha256", "webjobs.worker_package_sha256")
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise ValueError("worker_package_sha256 is invalid")
        _verify_evidence(document.get("evidence"))
    else:
        for key in ("frontend", "backend"):
            if document.get(key) is not None:
                _verify_image(key, document[key], source_sha)
        webjobs = document.get("webjobs")
        if webjobs is not None:
            if not isinstance(webjobs, dict):
                raise ValueError("webjobs must be an object")
            if set(webjobs) != {"worker_package_sha256"}:
                raise ValueError("webjobs must contain only the worker package")
            value = _required(webjobs, "worker_package_sha256", "webjobs.worker_package_sha256")
            if not isinstance(value, str) or not SHA256.fullmatch(value):
                raise ValueError("worker_package_sha256 is invalid")


def main() -> int:
    try:
        document = json.loads(Path(sys.argv[1]).read_text())
        verify(document)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"RELEASE_MANIFEST=FAIL:{type(exc).__name__}", file=sys.stderr)
        return 1
    print("RELEASE_MANIFEST=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
