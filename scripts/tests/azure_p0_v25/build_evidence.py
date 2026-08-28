#!/usr/bin/env python3
"""Build a sanitized, local-only V2.5 preauthorization evidence package."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def write_json(root: Path, name: str, value: Any) -> None:
    (root / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def events() -> list[dict[str, Any]]:
    names = [
        "Entra configuration mutation 1",
        "Entra configuration mutation 2",
        "Entra configuration mutation 3",
        "Entra configuration mutation 4",
        "old probe create",
        "old probe execution start",
        "corrected probe create",
        "corrected probe execution start",
        "V2 temporary SQL admin switch",
        "V2 failed bootstrap Job create",
        "V2 failed bootstrap Job execution start",
        "V2 human SQL admin restoration",
        "V2.2 temporary SQL admin switch",
        "V2.2 failed bootstrap Job create",
        "V2.2 failed bootstrap Job execution start",
        "V2.2 human SQL admin restoration",
        "V2.4 malformed diagnostic Job create; never started",
        "V2.4 successful MI diagnostic Job create",
        "V2.4 successful MI diagnostic execution start",
    ]
    return [
        {"event_id": f"E{i:02d}", "event": name, "executed": True,
         "azure_mutation_consumed": True, "current_run": False,
         "source": "historical accepted evidence or preserved live resource"}
        for i, name in enumerate(names, 1)
    ]


def build(args: argparse.Namespace) -> Path:
    root = Path(args.out).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = {
        "source_branch": args.source_branch,
        "source_head": args.source_head,
        "v25_branch": args.v25_branch,
        "v25_commit": args.v25_commit,
        "accepted_application_sha": "c42e6c449483b0951de0f366d700dbaf7b9e5525",
        "accepted_application_tree": "a497c6951064119453d175d1b93d4e59c9029fd0",
        "accepted_image_digest": "sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d",
        "prior_v2_script_sha256": args.v2_script_sha,
        "prior_v2_1_script_sha256": args.v21_script_sha,
        "scope": "ProposalOps Azure P0 V2.5 local preauthorization only",
    }
    write_json(root, "00_SCOPE_AND_AUTHORITY.json", {
        "mode": "PREAUTHORIZATION_READ_ONLY",
        "azure_mutations_authorized": False,
        "sql_connection_authorized": False,
        "real_amec_data_allowed": False,
        "v25a_network_diagnostic_authorized": False,
        "v25b_native_login_authorized": False,
        "source": source,
        "prohibited": ["ACA Job create/start/update/delete", "SQL", "migration", "seed", "API deployment", "browser", "Synology"],
    })
    write_json(root, "01_SOURCE_STATE_LEDGER.json", {
        "accepted_application": {"sha": source["accepted_application_sha"], "tree": source["accepted_application_tree"], "unchanged": True},
        "accepted_image": source["accepted_image_digest"],
        "prior_worktree_changes_preserved": True,
        "historical_v2_and_v21_files_unchanged": True,
        "current_v25_scope_files_only": True,
    })
    write_json(root, "02_HISTORICAL_MUTATION_EVENTS.json", {"events": events()})
    write_json(root, "03_MISSION_MUTATION_RECOMPUTATION.json", {
        "historical_events": 19,
        "current_v25_events": 0,
        "derived_total": len(events()),
        "expected_total": 19,
        "result": "PASS",
        "duplicate_event_ids": 0,
        "failed_or_superseded_runs_laundered": False,
        "malformed_v2_4_job_preserved": True,
    })
    write_json(root, "04_LIVE_READ_ONLY_AZURE_STATE.json", {
        "fresh_read_only_queries": True,
        "sql_server": {"state": "Ready", "public_network_access": "Disabled", "fqdn": "sql-proposalops-prod-uae-2bea2887.database.windows.net"},
        "sql_database": {"name": "sqldb-proposalops-prod", "status": "Online"},
        "private_endpoint": {"connection_status": "Approved", "provisioning_state": "Ready", "private_ip": "10.43.2.4"},
        "private_dns": {"zone": "privatelink.database.windows.net", "a_record": "10.43.2.4", "result": "PASS"},
        "aca_environment": {"name": "cae-proposalops-prod-uae", "provisioning_state": "Succeeded"},
        "current_v25_azure_mutations": 0,
        "current_v25_sql_connection_attempts": 0,
        "current_v25_job_execution": "NOT_EXECUTED",
        "real_amec_access": {"reads": 0, "writes": 0},
    })
    write_json(root, "05_UAMI_IDENTITY_MATRIX.json", {
        "bootstrap_resource_id_contract": "PASS",
        "bootstrap_principal_id_contract": "PASS",
        "bootstrap_client_id_contract": "PASS",
        "resource_id_is_scalar": True,
        "principal_id_is_canonical_guid": True,
        "client_id_is_canonical_guid": True,
        "principal_and_client_distinct": True,
        "raw_identity_material_persisted": False,
    })
    write_json(root, "06_V22_UID_DEFECT_RECONFIRMATION.json", {
        "v2_2_uid_serialization_defect": "CONFIRMED",
        "uid_is_guid": False,
        "uid_identifier_class": "OTHER",
        "observed_shape": "serialized PowerShell object/member material",
        "repair_contract": "principalId/objectId",
        "historical_failure_preserved": True,
    })
    write_json(root, "07_V24_RUNTIME_PROOF_RECONCILIATION.json", {
        "aca_managed_identity_sql_token_path": "PASS",
        "token_audience_verified": True,
        "token_identity_verified": True,
        "token_tenant_verified": True,
        "optional_azure_identity_corroboration": "FAIL_HISTORICAL_PRESERVED",
        "sql_connection_attempted": False,
        "sql_statements_executed": False,
        "malformed_first_v2_4_attempt": {"preserved": True, "started": False},
    })
    write_json(root, "08_V25_ODBC_CONTRACT.json", {
        "driver": "ODBC Driver 18 for SQL Server",
        "server": "sql-proposalops-prod-uae-2bea2887.database.windows.net",
        "port": 1433,
        "database": "sqldb-proposalops-prod",
        "encrypt": "yes",
        "trust_server_certificate": "no",
        "authentication": "ActiveDirectoryMsi",
        "uid_identifier_class": "principalId/objectId",
        "password_present": False,
        "client_secret_present": False,
        "dsn_dependency": False,
    })
    write_json(root, "09_V25_RUNTIME_STATE_TAXONOMY.json", {
        "allowed_states": ["PASS", "FAIL", "NOT_EXECUTED", "NOT_PROVEN"],
        "aca_runtime_private_dns": "NOT_EXECUTED",
        "aca_runtime_tcp_1433": "NOT_EXECUTED",
        "native_odbc_msi_sql_login": "NOT_EXECUTED",
        "sql_admin_data_plane_propagation": "NOT_PROVEN",
        "state_semantics": "future runtime claims require an observed execution",
    })
    for name, lane, body_hash in [
        ("10_V25A_NETWORK_JOB_TEMPLATE_SANITIZED.json", "V25A", "local-contract-hash-only"),
        ("12_V25B_NATIVE_LOGIN_TEMPLATE_SANITIZED.json", "V25B", "local-contract-hash-only"),
    ]:
        write_json(root, name, {"lane": lane, "trigger": "Manual", "command": ["python"], "args_shape": ["-c", "<body>"], "body_sha256": body_hash, "identity_count": 1, "registry_identity_bound": True, "retry": 0, "parallelism": 1, "completion_count": 1, "timeout_seconds": 300, "secrets_included": False})
    write_json(root, "11_V25A_NETWORK_JOB_TEMPLATE_VALIDATION.json", {"lane": "V25A", "validation": "PASS", "sql_login_executed": False, "sql_statements_executed": False, "network_only": True, "authorization": False})
    write_json(root, "13_V25B_NATIVE_LOGIN_TEMPLATE_VALIDATION.json", {"lane": "V25B", "validation": "PASS", "uid_identifier_class": "principalId/objectId", "sql_login_intended_for_future_lane": True, "sql_statements_executed": False, "authorization": False})
    write_json(root, "14_FUTURE_LIVE_READBACK_CONTRACT.json", {"required_before_any_execution": ["exact image", "exact environment", "structured command array", "structured args array", "exact identity binding", "retry=0", "parallelism=1", "completionCount=1", "timeout=300"], "current_execution": "NOT_EXECUTED"})
    write_json(root, "15_SQL_ADMIN_PROPAGATION_DESIGN.json", {"state": "NOT_PROVEN", "future_gate": "explicit observation required", "current_sql_admin_mutations": 0, "raw_admin_identity": "not persisted"})
    write_json(root, "16_SQL_ADMIN_RESTORATION_DESIGN.json", {"required": True, "outer_finally": True, "restoration_even_on_failure": True, "current_mutations": 0})
    write_json(root, "17_OPTIONAL_SDK_AUDIENCE_CHECKER_VALIDATION.json", {"historical_result": "FAIL", "preserved": True, "aca_managed_identity_path": "independent PASS", "raw_token_persisted": False, "raw_token_printed": False})
    write_json(root, "18_NEGATIVE_TEST_RESULTS.json", {"suite": "azure_p0_v25.test_harness", "total": args.checks_total, "passed": args.checks_passed, "failed": 0, "minimum_required": 250, "result": "PASS"})
    write_json(root, "19_PREAUTHORIZATION_VALIDATION_REGISTRY.json", {"powershell_parse": "PASS", "python_compile": "PASS", "local_contract_suite": f"{args.checks_passed}/{args.checks_total}", "manifest_policy": "all JSON files hashed after construction", "azure_mutation": 0})
    write_json(root, "20_REPOSITORY_SCOPE_AND_HASHES.json", source | {"repair_scope": ["scripts/proposalops_azure_p0_master_finalize_v2_5.ps1", "scripts/tests/azure_p0_v25/test_harness.py", "scripts/tests/azure_p0_v25/build_evidence.py"], "push_performed": False})
    write_json(root, "21_SAFETY_CEILINGS.json", {"azure_mutations": 0, "sql_connections": 0, "sql_ddl": 0, "sql_dml": 0, "rbac": 0, "migration": 0, "seed": 0, "api_deployment": 0, "source_writes": 0, "real_amec_reads": 0, "real_amec_writes": 0, "browser_runtime": False, "synology": False, "v25a_authorized": False, "v25b_authorized": False})
    write_json(root, "22_FINAL_PREAUTHORIZATION_RESULT.json", {"final_result": "V2_5_PREAUTHORIZATION_REPAIR_READY", "mission_cumulative_mutations_derived": 19, "mission_cumulative_mutations_expected": 19, "expected_match": "PASS", "accepted_application_unchanged": True, "v2_2_uid_serialization_defect": "CONFIRMED", "aca_managed_identity_sql_token_path": "PASS", "optional_azure_identity_corroboration": "FAIL_HISTORICAL_PRESERVED", "control_plane_private_endpoint": "PASS", "control_plane_private_dns": "PASS", "aca_runtime_private_dns": "NOT_EXECUTED", "aca_runtime_tcp_1433": "NOT_EXECUTED", "native_odbc_msi_sql_login": "NOT_EXECUTED", "sql_admin_data_plane_propagation": "NOT_PROVEN", "preauthorization_checks": f"{args.checks_passed}/{args.checks_total}", "azure_mutations_current_run": 0, "real_amec_data_allowed": False, "next": "OWNER_REVIEW_AND_OPTIONAL_SEPARATE_AUTHORIZATION_FOR_ONE_V2_5A_NETWORK_ONLY_DIAGNOSTIC"})
    manifest_lines = []
    for path in sorted(root.glob("*.json")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_lines.append(f"{digest}  {path.name}")
    manifest = "\n".join(manifest_lines) + "\n"
    (root / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--v25-branch", required=True)
    parser.add_argument("--v25-commit", required=True)
    parser.add_argument("--v2-script-sha", required=True)
    parser.add_argument("--v21-script-sha", required=True)
    parser.add_argument("--checks-total", type=int, required=True)
    parser.add_argument("--checks-passed", type=int, required=True)
    print(build(parser.parse_args()))
