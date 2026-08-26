#!/usr/bin/env python3
"""Fail-closed sweep for Azure account cutover references.

This intentionally distinguishes current account binding from preserved historical
provenance. Retired identifiers may remain only in explicitly allowlisted historical
PostgreSQL/A1 evidence, security deny-lists, or negative tests that prove rejection.
The scan also normalizes backslash-escaped text so regex/shell escaping cannot hide
an email or identifier from the cutover audit.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINDING_PATH = ROOT / "config" / "azure_account_binding.json"

NEW_SUBSCRIPTION_ID = "2bea2887-9255-4273-a73f-43ae33813455"
NEW_TENANT_ID = "2a82f16d-87fa-4036-97a9-17d94060eddd"
NEW_SUBSCRIPTION_NAME = "AMEC Subscription"
NEW_OWNER_EMAIL = "a.sami.ibra@gmail.com"

OLD_SUBSCRIPTION_ID = "61080f8b-16cb-4abc-bb8c-5d8e59ab15bf"
HISTORICAL_TEST_SUBSCRIPTION_ID = "0e0f1028-a1f1-4b87-8cd3-449b7bdc3bc7"
OLD_TENANT_ID = "b27ffe53-8d31-4735-a07a-faa50c336d97"
OLD_SUBSCRIPTION_NAME = "ProposalOps Preprod QC"
OLD_OWNER_EMAIL = "a.sami.ibra@outlook.com"

HISTORICAL_ALLOWLIST = {
    "scripts/azure/step3a4_whatif.sh",
    "infra/azure/README.md",
    ".github/workflows/azure-a1-batch3a-step4c-hardening-validation.yml",
    ".github/workflows/db-rebaseline-validation.yml",
}

DENYLIST_ALLOWLIST = {
    "scripts/azure_sql_foundation/validate_foundation.sh",
}

NEGATIVE_TEST_ALLOWLIST = {
    "backend/tests/test_db_rebaseline.py",
}

NEW_BINDING_ALLOWED = {
    "config/azure_account_binding.json": {
        NEW_SUBSCRIPTION_ID,
        NEW_TENANT_ID,
        NEW_SUBSCRIPTION_NAME,
    },
    "release/a1-release-manifest.schema.json": {
        NEW_SUBSCRIPTION_ID,
    },
}

RETIRED_IDENTIFIERS = {
    OLD_SUBSCRIPTION_ID,
    HISTORICAL_TEST_SUBSCRIPTION_ID,
    OLD_TENANT_ID,
    OLD_SUBSCRIPTION_NAME,
    OLD_OWNER_EMAIL,
}
CURRENT_ACCOUNT_IDENTIFIERS = {
    NEW_SUBSCRIPTION_ID,
    NEW_TENANT_ID,
    NEW_SUBSCRIPTION_NAME,
    NEW_OWNER_EMAIL,
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / item.decode() for item in output.split(b"\0") if item]


def text_of(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def identifier_haystack(text: str) -> str:
    # Catches plain, single-escaped and double-escaped forms such as
    # a.sami..., a\.sami..., and a\\.sami.... Identifiers themselves contain
    # no meaningful backslashes, so removing them is safe for this focused scan.
    return text.replace("\\", "")


def main() -> int:
    failures: list[str] = []
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    expected_binding = {
        "schema_version": "PROPOSALOPS_AZURE_ACCOUNT_BINDING_V1",
        "subscription_id": NEW_SUBSCRIPTION_ID,
        "subscription_display_name": NEW_SUBSCRIPTION_NAME,
        "tenant_id": NEW_TENANT_ID,
        "region": "qatarcentral",
    }
    if binding != expected_binding:
        failures.append("canonical Azure account binding does not match cutover target")

    retired_hits: dict[str, list[str]] = {}
    new_hits: dict[str, list[str]] = {}
    tracked = tracked_files()

    for path in tracked:
        text = text_of(path)
        if text is None:
            continue
        rel = relative(path)
        normalized = identifier_haystack(text)
        for value in RETIRED_IDENTIFIERS:
            if value in normalized:
                retired_hits.setdefault(rel, []).append(value)
        for value in CURRENT_ACCOUNT_IDENTIFIERS:
            if value in normalized:
                new_hits.setdefault(rel, []).append(value)

    allowed_retired_paths = (
        HISTORICAL_ALLOWLIST
        | DENYLIST_ALLOWLIST
        | NEGATIVE_TEST_ALLOWLIST
        | {"scripts/azure/audit_account_cutover.py"}
    )
    unexpected_retired = sorted(set(retired_hits) - allowed_retired_paths)
    if unexpected_retired:
        failures.append(
            "retired Azure identifiers remain outside classified allowlists: "
            + ", ".join(unexpected_retired)
        )

    for rel, values in new_hits.items():
        if rel == "scripts/azure/audit_account_cutover.py":
            continue
        allowed = NEW_BINDING_ALLOWED.get(rel, set())
        unexpected = sorted(set(values) - allowed)
        if unexpected:
            failures.append(
                f"new real account identifier leaked into non-binding source {rel}: "
                + ", ".join(unexpected)
            )

    required_new_hits = {
        "config/azure_account_binding.json": {
            NEW_SUBSCRIPTION_ID,
            NEW_TENANT_ID,
            NEW_SUBSCRIPTION_NAME,
        },
        "release/a1-release-manifest.schema.json": {NEW_SUBSCRIPTION_ID},
    }
    for rel, required in required_new_hits.items():
        observed = set(new_hits.get(rel, []))
        if not required <= observed:
            failures.append(f"missing required current-account binding in {rel}")

    committed_non_audit_text = "\n".join(
        identifier_haystack(text_of(path) or "")
        for path in tracked
        if relative(path) != "scripts/azure/audit_account_cutover.py"
    )
    if NEW_OWNER_EMAIL in committed_non_audit_text:
        failures.append(
            "owner Gmail address must remain deployment-time input, not committed source"
        )

    frontend_text = identifier_haystack(
        (ROOT / "frontend/tests/auth.test.ts").read_text(encoding="utf-8")
    )
    if OLD_TENANT_ID in frontend_text or NEW_TENANT_ID in frontend_text:
        failures.append("frontend auth tests must use synthetic tenant identifiers only")

    schema = json.loads(
        (ROOT / "release/a1-release-manifest.schema.json").read_text(encoding="utf-8")
    )
    schema_subscription = schema["properties"]["azure"]["properties"][
        "subscription_id"
    ]["const"]
    if schema_subscription != NEW_SUBSCRIPTION_ID:
        failures.append("release schema is not rebound to the new subscription")

    verifier = identifier_haystack(
        (ROOT / "scripts/release/verify_a1_release_manifest.py").read_text(
            encoding="utf-8"
        )
    )
    if OLD_SUBSCRIPTION_ID in verifier or HISTORICAL_TEST_SUBSCRIPTION_ID in verifier:
        failures.append("release verifier still hardcodes a retired subscription")
    if "azure_account_binding.json" not in verifier:
        failures.append("release verifier does not load canonical account binding")

    print(f"TRACKED_TEXT_RETIRED_REFERENCE_FILES={len(retired_hits)}")
    print(f"TRACKED_TEXT_NEW_ACCOUNT_REFERENCE_FILES={len(new_hits)}")
    print("ESCAPED_IDENTIFIER_NORMALIZATION=ENABLED")
    print(
        "HISTORICAL_RETENTION_PATHS="
        + ",".join(sorted(set(retired_hits) & HISTORICAL_ALLOWLIST))
    )
    print(
        "DENYLIST_RETENTION_PATHS="
        + ",".join(sorted(set(retired_hits) & DENYLIST_ALLOWLIST))
    )
    print(
        "NEGATIVE_TEST_RETENTION_PATHS="
        + ",".join(sorted(set(retired_hits) & NEGATIVE_TEST_ALLOWLIST))
    )
    print(f"ACCOUNT_CUTOVER_FAILURE_COUNT={len(failures)}")
    for failure in failures:
        print(f"FAIL {failure}")
    if failures:
        print("AZURE_ACCOUNT_CUTOVER_AUDIT=FAIL")
        return 1
    print("AZURE_ACCOUNT_CUTOVER_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
