#!/usr/bin/env python3
"""Exact sanitized DSM PRE/POST state schema and immutable-field comparison."""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "SYN-T3-DSM-STATE-V1"
IMMUTABLE_FIELDS = (
    "model", "dsm_version", "dsm_build", "hostname", "architecture", "active_lan_ip",
    "gateway", "docker_version", "smb", "firewall", "auto_block", "tun1000",
    "existing_proposalops_identities", "business_share_acl_fingerprint",
)
PRE_FIELDS = set(IMMUTABLE_FIELDS) | {"state_schema_version", "phase", "test_share_exists", "test_accounts_exist"}
POST_FIELDS = set(IMMUTABLE_FIELDS) | {
    "state_schema_version", "phase", "test_share_exists", "test_share_permissions",
    "proposalops_t3_ro_enabled", "proposalops_t3_denied_enabled", "t3_secret_files_retained",
    "t3_recurring_tasks_enabled", "t3_task_removed",
}
FORBIDDEN_FIELD_TERMS = ("password", "hash", "token", "private_key", "secret")


def _walk_forbidden(value: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            allowed_cleanup_field = str(key) == "t3_secret_files_retained"
            if not allowed_cleanup_field and any(term in str(key).lower() for term in FORBIDDEN_FIELD_TERMS):
                errors.append(f"forbidden field:{path}{key}")
            errors.extend(_walk_forbidden(child, f"{path}{key}."))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_forbidden(child, f"{path}{index}."))
    return errors


def validate_state(payload: dict[str, Any], phase: str) -> list[str]:
    required = PRE_FIELDS if phase == "PRE" else POST_FIELDS if phase == "POST" else set()
    errors = []
    if payload.get("state_schema_version") != SCHEMA_VERSION:
        errors.append("state_schema_version mismatch")
    if payload.get("phase") != phase:
        errors.append(f"phase must be {phase}")
    errors.extend(f"missing field:{key}" for key in sorted(required - set(payload)))
    errors.extend(_walk_forbidden(payload))
    ip_value = payload.get("active_lan_ip")
    if isinstance(ip_value, str):
        try:
            if ipaddress.ip_address(ip_value).version != 4:
                errors.append("active_lan_ip must be IPv4")
        except ValueError:
            errors.append("active_lan_ip is invalid")
    else:
        errors.append("active_lan_ip must be present as IPv4")
    if phase == "PRE":
        if payload.get("test_share_exists") is not False:
            errors.append("PRE test_share_exists must be false")
        if payload.get("test_accounts_exist") is not False:
            errors.append("PRE test_accounts_exist must be false")
    if phase == "POST":
        exact_zero = ("t3_secret_files_retained", "t3_recurring_tasks_enabled")
        for key in exact_zero:
            if not isinstance(payload.get(key), int) or isinstance(payload.get(key), bool):
                errors.append(f"{key} must be an integer")
        if payload.get("test_share_exists") is not True:
            errors.append("POST test_share_exists must be true")
        for key in ("proposalops_t3_ro_enabled", "proposalops_t3_denied_enabled", "t3_task_removed"):
            if not isinstance(payload.get(key), bool):
                errors.append(f"{key} must be boolean")
        if payload.get("proposalops_t3_ro_enabled") is not False:
            errors.append("proposalops_t3_ro_enabled must be false")
        if payload.get("proposalops_t3_denied_enabled") is not False:
            errors.append("proposalops_t3_denied_enabled must be false")
        if payload.get("t3_secret_files_retained") != 0:
            errors.append("t3_secret_files_retained must be zero")
        if payload.get("t3_recurring_tasks_enabled") != 0:
            errors.append("t3_recurring_tasks_enabled must be zero")
        if payload.get("t3_task_removed") is not True:
            errors.append("t3_task_removed must be true")
    return sorted(set(errors))


def compare_states(pre: dict[str, Any], post: dict[str, Any]) -> dict[str, Any]:
    errors = validate_state(pre, "PRE") + validate_state(post, "POST")
    immutable_deltas = {key: pre.get(key) != post.get(key) for key in IMMUTABLE_FIELDS}
    global_keys = {"model", "dsm_version", "dsm_build", "hostname", "architecture", "active_lan_ip", "gateway", "docker_version", "smb", "firewall", "auto_block", "tun1000"}
    business_keys = {"business_share_acl_fingerprint"}
    identity_keys = {"existing_proposalops_identities"}
    return {
        "schema_errors": sorted(set(errors)),
        "immutable_field_deltas": immutable_deltas,
        "UNAUTHORIZED_DSM_GLOBAL_DELTA_COUNT": sum(immutable_deltas[key] for key in global_keys),
        "UNAUTHORIZED_BUSINESS_SHARE_DELTA_COUNT": sum(immutable_deltas[key] for key in business_keys),
        "EXISTING_PROPOSALOPS_IDENTITY_MUTATION_COUNT": sum(immutable_deltas[key] for key in identity_keys),
        "proposalops_t3_ro_enabled": post.get("proposalops_t3_ro_enabled"),
        "proposalops_t3_denied_enabled": post.get("proposalops_t3_denied_enabled"),
        "t3_secret_files_retained": post.get("t3_secret_files_retained"),
        "t3_recurring_tasks_enabled": post.get("t3_recurring_tasks_enabled"),
        "t3_task_removed": post.get("t3_task_removed"),
        "test_share_exists": post.get("test_share_exists"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("PRE", "POST"), required=True)
    parser.add_argument("state", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.state.read_text(encoding="utf-8"))
    errors = validate_state(payload, args.phase)
    print(json.dumps({"phase": args.phase, "status": "PASS" if not errors else "FAIL", "errors": errors}, sort_keys=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
