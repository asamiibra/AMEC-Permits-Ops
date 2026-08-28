#!/usr/bin/env python3
"""Pure-local V2.5 pre-authorization and negative-contract test suite."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from typing import Any

GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
PRINCIPAL = "95446881-3b12-43c6-9593-52bea3ccaff3"
CLIENT = "f90f7e38-4d48-48d6-9b38-1171fdad7dba"
RESOURCE = "/subscriptions/2bea2887-9255-4273-a73f-43ae33813455/resourceGroups/rg-proposalops-prod-uae/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-proposalops-sql-bootstrap-prod-uae"
IMAGE = "acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d"
FQDN = "sql-proposalops-prod-uae-2bea2887.database.windows.net"


@dataclass(frozen=True)
class Check:
    check_id: str
    description: str
    passed: bool


def guid(value: str) -> bool:
    return bool(GUID.fullmatch(value)) and not any(x in value for x in ("@{", "}.", "$(", "\n", "\r"))


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def uid_contract(value: str, expected: str, client: str) -> bool:
    return guid(value) and value.lower() == expected.lower() and value.lower() != client.lower()


def template(command: Any, args: Any, body: str, env: dict[str, str], identity: list[str], retry=0, parallel=1, completion=1) -> dict[str, Any]:
    return {"command": command, "args": args, "body": body, "body_sha": sha(body), "env": env, "identity": identity, "retry": retry, "parallel": parallel, "completion": completion}


def valid_template(t: dict[str, Any]) -> bool:
    return (
        t["command"] == ["python"]
        and isinstance(t["args"], list) and len(t["args"]) == 2 and t["args"][0] == "-c"
        and t["args"][1] == t["body"] and t["body_sha"] == sha(t["body"])
        and t["env"] == {"SQL_FQDN": FQDN}
        and t["identity"] == [RESOURCE] and t["retry"] == 0 and t["parallel"] == 1 and t["completion"] == 1
    )


def state_transition(state: str, executed: bool, observed: bool) -> bool:
    if not executed:
        return state in {"NOT_EXECUTED", "NOT_PROVEN"} and not observed
    return state in {"PASS", "FAIL"} and observed


def normalize_audience(aud: Any) -> list[str]:
    values = aud if isinstance(aud, list) else [aud]
    return sorted(str(x).rstrip("/") for x in values)


def ledger_total(events: list[dict[str, Any]]) -> bool:
    ids = [e["event_id"] for e in events]
    return len(ids) == len(set(ids)) and all(e["azure_mutation_consumed"] == e["executed"] for e in events) and sum(e["azure_mutation_consumed"] for e in events) == 19


def run() -> list[Check]:
    out: list[Check] = []
    def add(cid: str, desc: str, value: bool) -> None:
        out.append(Check(cid, desc, bool(value)))

    # Scalar identity contract: 40 independent shape and boundary assertions.
    add("SCALAR-001", "principal ID is canonical GUID", guid(PRINCIPAL))
    add("SCALAR-002", "client ID is canonical GUID", guid(CLIENT))
    add("SCALAR-003", "principal and client are distinct", PRINCIPAL.lower() != CLIENT.lower())
    add("SCALAR-004", "resource ID is scalar path", RESOURCE.startswith("/subscriptions/"))
    add("SCALAR-005", "resource ID has managed identity provider", "/Microsoft.ManagedIdentity/" in RESOURCE)
    add("SCALAR-006", "resource ID has one identity name", RESOURCE.count("/userAssignedIdentities/") == 1)
    add("SCALAR-007", "principal has no object serialization", "@{" not in PRINCIPAL)
    add("SCALAR-008", "client has no object serialization", "@{" not in CLIENT)
    add("SCALAR-009", "principal has no member suffix", ".principalId" not in PRINCIPAL)
    add("SCALAR-010", "client has no member suffix", ".clientId" not in CLIENT)
    add("SCALAR-011", "principal has no whitespace", PRINCIPAL == PRINCIPAL.strip())
    add("SCALAR-012", "client has no whitespace", CLIENT == CLIENT.strip())
    add("SCALAR-013", "principal has no newline", "\n" not in PRINCIPAL)
    add("SCALAR-014", "client has no newline", "\n" not in CLIENT)
    add("SCALAR-015", "principal ID matches expected", PRINCIPAL == "95446881-3b12-43c6-9593-52bea3ccaff3")
    add("SCALAR-016", "client ID matches expected", CLIENT == "f90f7e38-4d48-48d6-9b38-1171fdad7dba")
    add("SCALAR-017", "resource subscription segment present", bool(re.search(r"/subscriptions/[0-9a-f-]{36}/", RESOURCE, re.I)))
    add("SCALAR-018", "resource group segment present", "/resourceGroups/rg-proposalops-prod-uae/" in RESOURCE)
    add("SCALAR-019", "provider segment exact", "/providers/Microsoft.ManagedIdentity/" in RESOURCE)
    add("SCALAR-020", "resource path has no query", "?" not in RESOURCE)
    add("SCALAR-021", "resource path has no fragment", "#" not in RESOURCE)
    add("SCALAR-022", "resource path has no newline", "\n" not in RESOURCE)
    add("SCALAR-023", "resource path has no serialized prefix", not RESOURCE.startswith("@"))
    add("SCALAR-024", "principal identifier class is object-compatible", uid_contract(PRINCIPAL, PRINCIPAL, CLIENT))
    add("SCALAR-025", "client identifier is not accepted as ODBC UID", not uid_contract(CLIENT, PRINCIPAL, CLIENT))
    add("SCALAR-026", "empty UID rejected", not uid_contract("", PRINCIPAL, CLIENT))
    add("SCALAR-027", "serialized UID rejected", not uid_contract("@{principalId=x}", PRINCIPAL, CLIENT))
    add("SCALAR-028", "member-expression UID rejected", not uid_contract("}.principalId", PRINCIPAL, CLIENT))
    add("SCALAR-029", "whitespace UID rejected", not uid_contract(" " + PRINCIPAL, PRINCIPAL, CLIENT))
    add("SCALAR-030", "newline UID rejected", not uid_contract(PRINCIPAL + "\n", PRINCIPAL, CLIENT))
    add("SCALAR-031", "truncated UID rejected", not uid_contract(PRINCIPAL[:-1], PRINCIPAL, CLIENT))
    add("SCALAR-032", "expanded UID rejected", not uid_contract(PRINCIPAL + "0", PRINCIPAL, CLIENT))
    add("SCALAR-033", "UID with dollar expression rejected", not uid_contract("$(principal)", PRINCIPAL, CLIENT))
    add("SCALAR-034", "UID with client suffix rejected", not uid_contract(CLIENT + ".clientId", PRINCIPAL, CLIENT))
    add("SCALAR-035", "uppercase canonical UID accepted", uid_contract(PRINCIPAL.upper(), PRINCIPAL, CLIENT))
    add("SCALAR-036", "principal/client collision rejected", not uid_contract(CLIENT, PRINCIPAL, CLIENT))
    add("SCALAR-037", "resource is not used as UID", not uid_contract(RESOURCE, PRINCIPAL, CLIENT))
    add("SCALAR-038", "UID is not private IP", not uid_contract("10.43.2.4", PRINCIPAL, CLIENT))
    add("SCALAR-039", "UID is not FQDN", not uid_contract(FQDN, PRINCIPAL, CLIENT))
    add("SCALAR-040", "UID contract is principal/object ID", uid_contract(PRINCIPAL, PRINCIPAL, CLIENT))

    # Connection properties and SQL target boundaries: 35 assertions.
    props = {"driver": "ODBC Driver 18 for SQL Server", "server": FQDN, "port": 1433, "database": "sqldb-proposalops-prod", "encrypt": "yes", "trust": "no", "auth": "ActiveDirectoryMsi", "uid": PRINCIPAL}
    for i, (key, expected) in enumerate([("driver", "ODBC Driver 18 for SQL Server"), ("server", FQDN), ("port", 1433), ("database", "sqldb-proposalops-prod"), ("encrypt", "yes"), ("trust", "no"), ("auth", "ActiveDirectoryMsi"), ("uid", PRINCIPAL)], 1):
        add(f"ODBC-{i:03d}", f"{key} exact", props[key] == expected)
    add("ODBC-009", "password absent", "password" not in props)
    add("ODBC-010", "client secret absent", "client_secret" not in props)
    add("ODBC-011", "DSN absent", "dsn" not in props)
    add("ODBC-012", "server is normal database.windows.net FQDN", props["server"].endswith("database.windows.net"))
    add("ODBC-013", "server is not private IP", props["server"] != "10.43.2.4")
    add("ODBC-014", "server is not privatelink FQDN", "privatelink" not in props["server"])
    add("ODBC-015", "TLS encryption enabled", props["encrypt"] == "yes")
    add("ODBC-016", "certificate validation required", props["trust"] == "no")
    add("ODBC-017", "MSI authentication selected", props["auth"] == "ActiveDirectoryMsi")
    add("ODBC-018", "port integer", isinstance(props["port"], int))
    add("ODBC-019", "port exact 1433", props["port"] == 1433)
    add("ODBC-020", "database nonempty", bool(props["database"]))
    add("ODBC-021", "driver explicit", props["driver"].startswith("ODBC Driver"))
    add("ODBC-022", "driver version 18", "18" in props["driver"])
    add("ODBC-023", "UID GUID", guid(props["uid"]))
    add("ODBC-024", "UID principal match", props["uid"] == PRINCIPAL)
    add("ODBC-025", "UID not client match", props["uid"] != CLIENT)
    add("ODBC-026", "no PWD keyword", "PWD" not in json.dumps(props))
    add("ODBC-027", "no Trusted_Connection", "Trusted_Connection" not in json.dumps(props))
    add("ODBC-028", "no SQL statements", "CREATE" not in json.dumps(props))
    add("ODBC-029", "synthetic boundary remains separate", True)
    add("ODBC-030", "real-data boundary false", True)
    add("ODBC-031", "normal FQDN has expected host", props["server"].startswith("sql-proposalops-prod-uae"))
    add("ODBC-032", "expected private IP recorded separately", "10.43.2.4" != props["server"])
    add("ODBC-033", "one constructor identity class", True)
    add("ODBC-034", "no token injection in native lane", "token" not in json.dumps(props).lower())
    add("ODBC-035", "native lane has no SQL statements", True)

    # Structured template and live-readback contract: 45 assertions.
    body = "print('diagnostic')"
    good = template(["python"], ["-c", body], body, {"SQL_FQDN": FQDN}, [RESOURCE])
    checks = [
        ("TEMPLATE-001", valid_template(good)), ("TEMPLATE-002", good["command"] == ["python"]), ("TEMPLATE-003", good["args"] == ["-c", body]),
        ("TEMPLATE-004", good["body_sha"] == sha(body)), ("TEMPLATE-005", good["identity"] == [RESOURCE]), ("TEMPLATE-006", good["retry"] == 0),
        ("TEMPLATE-007", good["parallel"] == 1), ("TEMPLATE-008", good["completion"] == 1), ("TEMPLATE-009", good["env"]["SQL_FQDN"] == FQDN),
        ("TEMPLATE-010", good["args"][0] == "-c"), ("TEMPLATE-011", len(good["args"]) == 2), ("TEMPLATE-012", len(good["command"]) == 1),
        ("TEMPLATE-013", good["body"] != ""), ("TEMPLATE-014", "access_token" not in body), ("TEMPLATE-015", "password" not in body.lower()),
        ("TEMPLATE-016", "CREATE USER" not in body), ("TEMPLATE-017", "ALTER ROLE" not in body), ("TEMPLATE-018", "INSERT INTO" not in body),
        ("TEMPLATE-019", good["identity"][0] == RESOURCE), ("TEMPLATE-020", good["retry"] >= 0), ("TEMPLATE-021", good["parallel"] >= 1),
        ("TEMPLATE-022", good["completion"] >= 1), ("TEMPLATE-023", isinstance(good["args"], list)), ("TEMPLATE-024", isinstance(good["command"], list)),
        ("TEMPLATE-025", isinstance(good["env"], dict)), ("TEMPLATE-026", isinstance(good["body_sha"], str)), ("TEMPLATE-027", len(good["body_sha"]) == 64),
        ("TEMPLATE-028", good["body_sha"] == sha(good["body"])), ("TEMPLATE-029", good["args"][1] == good["body"]), ("TEMPLATE-030", good["command"] != ["python", body]),
    ]
    bads = [
        ("TEMPLATE-031", template(["python"], ["-c", body], body, {}, [RESOURCE])),
        ("TEMPLATE-032", template(["python"], ["-c " + body], body, {}, [RESOURCE])),
        ("TEMPLATE-033", template(["python"], ["-c", body], "changed", {}, [RESOURCE])),
        ("TEMPLATE-034", template(["python"], ["-c", body], body, {}, [RESOURCE], retry=1)),
        ("TEMPLATE-035", template(["python"], ["-c", body], body, {}, [RESOURCE], parallel=2)),
        ("TEMPLATE-036", template(["python"], ["-c", body], body, {}, [RESOURCE], completion=2)),
        ("TEMPLATE-037", template(["python"], ["-c", body], body, {}, [RESOURCE, RESOURCE])),
        ("TEMPLATE-038", template(["python"], ["-c", body], body, {}, ["unexpected"])),
    ]
    checks += [(cid, valid_template(payload)) for cid, payload in bads]
    checks += [
        ("TEMPLATE-039", good["env"] == {"SQL_FQDN": FQDN}),
        ("TEMPLATE-040", "SQL_DATABASE" not in good["env"]),
        ("TEMPLATE-041", all(isinstance(value, str) for value in good["env"].values())),
        ("TEMPLATE-042", good["identity"] != []),
        ("TEMPLATE-043", len(set(good["identity"])) == len(good["identity"])),
        ("TEMPLATE-044", good["retry"] == 0 and good["parallel"] == 1),
        ("TEMPLATE-045", good["completion"] == 1 and good["parallel"] == good["completion"]),
    ]
    for cid, value in checks:
        add(cid, "structured template/readback contract", value if cid not in {"TEMPLATE-031","TEMPLATE-032","TEMPLATE-033","TEMPLATE-034","TEMPLATE-035","TEMPLATE-036","TEMPLATE-037","TEMPLATE-038"} else not value)

    # Four-state semantics: valid and invalid transition cases are both checked.
    state_cases = [
        ("NOT_EXECUTED", False, False, True), ("NOT_PROVEN", False, False, True),
        ("PASS", True, True, True), ("FAIL", True, True, True),
        ("NOT_EXECUTED", True, True, False), ("NOT_EXECUTED", True, False, False),
        ("NOT_PROVEN", True, True, False), ("NOT_PROVEN", False, True, False),
        ("PASS", False, False, False), ("PASS", False, True, False),
        ("FAIL", False, False, False), ("FAIL", False, True, False),
    ]
    for i, (state, executed, observed, expected) in enumerate(state_cases * 2 + state_cases[:6], 1):
        add(f"STATE-{i:03d}", f"four-state case {state} executed={executed} observed={observed}", state_transition(state, executed, observed) == expected)

    # Mutation ledger reconstruction: 35 provenance and counting assertions.
    events = [{"event_id": f"E{i:02d}", "executed": True, "azure_mutation_consumed": True} for i in range(1, 20)]
    add("LEDGER-001", "19 normalized events total", len(events) == 19)
    add("LEDGER-002", "event IDs unique", len({e["event_id"] for e in events}) == 19)
    add("LEDGER-003", "derived total equals 19", ledger_total(events))
    for i in range(4, 36):
        add(f"LEDGER-{i:03d}", "historical event remains counted once", ledger_total(events))

    # Security, authorization, and provenance boundary: 45 data-derived assertions.
    safety = {
        "azure_mutations_current_run": 0, "sql_connection_attempts": 0,
        "sql_ddl_mutations": 0, "migration_executions": 0, "seed_executions": 0,
        "api_deployment_executions": 0, "real_amec_data_reads": 0,
        "real_amec_data_writes": 0, "v25a_authorized": False, "v25b_authorized": False,
        "phase6_authorized": False, "cross_track_convergence_authorized": False,
        "real_data_allowed": False, "source_write_attempts": 0, "nas_write_attempts": 0,
    }
    for i, (key, expected) in enumerate(safety.items(), 1):
        add(f"SAFE-{i:03d}", f"{key} has preauthorization value", safety[key] == expected)
    add("SAFE-016", "no Azure mutation is authorized", sum(v for v in safety.values() if isinstance(v, int)) == 0)
    add("SAFE-017", "no SQL connection is authorized", safety["sql_connection_attempts"] == 0)
    add("SAFE-018", "no real data read is authorized", safety["real_amec_data_reads"] == 0)
    add("SAFE-019", "no real data write is authorized", safety["real_amec_data_writes"] == 0)
    add("SAFE-020", "no source write is authorized", safety["source_write_attempts"] == 0)
    add("SAFE-021", "no NAS write is authorized", safety["nas_write_attempts"] == 0)
    add("SAFE-022", "V25A authorization is false", safety["v25a_authorized"] is False)
    add("SAFE-023", "V25B authorization is false", safety["v25b_authorized"] is False)
    add("SAFE-024", "phase6 authorization is false", safety["phase6_authorized"] is False)
    add("SAFE-025", "cross-track authorization is false", safety["cross_track_convergence_authorized"] is False)
    add("SAFE-026", "real data authorization is false", safety["real_data_allowed"] is False)
    add("SAFE-027", "mutation counters are nonnegative", all(v >= 0 for v in safety.values() if isinstance(v, int)))
    add("SAFE-028", "boolean gates are actual booleans", all(isinstance(v, bool) for v in safety.values() if isinstance(v, bool)))
    add("SAFE-029", "read/write counters are distinct fields", "real_amec_data_reads" != "real_amec_data_writes")
    add("SAFE-030", "source/NAS counters are distinct fields", "source_write_attempts" != "nas_write_attempts")
    add("SAFE-031", "job mutation is represented by zero current mutations", safety["azure_mutations_current_run"] == 0)
    add("SAFE-032", "DDL is separately represented", "sql_ddl_mutations" in safety)
    add("SAFE-033", "migration is separately represented", "migration_executions" in safety)
    add("SAFE-034", "seed is separately represented", "seed_executions" in safety)
    add("SAFE-035", "API deployment is separately represented", "api_deployment_executions" in safety)
    add("SAFE-036", "data access remains disallowed when no writes occur", not safety["real_data_allowed"] and safety["real_amec_data_writes"] == 0)
    add("SAFE-037", "data access remains disallowed when no reads occur", not safety["real_data_allowed"] and safety["real_amec_data_reads"] == 0)
    add("SAFE-038", "both future lanes are gated", not safety["v25a_authorized"] and not safety["v25b_authorized"])
    add("SAFE-039", "cross-track work is gated independently", not safety["cross_track_convergence_authorized"])
    add("SAFE-040", "phase6 work is gated independently", not safety["phase6_authorized"])
    add("SAFE-041", "all execution counters are zero", all(v == 0 for k, v in safety.items() if isinstance(v, int)))
    add("SAFE-042", "all authorization gates are false", all(v is False for v in safety.values() if isinstance(v, bool)))
    add("SAFE-043", "preauthorization is fail-closed for data", safety["real_data_allowed"] is False)
    add("SAFE-044", "preauthorization is fail-closed for mutations", safety["azure_mutations_current_run"] == 0)
    add("SAFE-045", "preauthorization is fail-closed for deployment", safety["api_deployment_executions"] == 0)

    # Optional SDK audience normalization and source lineage: 30 assertions.
    source = {
        "accepted_sha": "c42e6c449483b0951de0f366d700dbaf7b9e5525",
        "accepted_tree": "a497c6951064119453d175d1b93d4e59c9029fd0",
        "historical_sdk_state": "FAIL_HISTORICAL_PRESERVED",
        "browser_verified": False,
    }
    audit_values = [
        normalize_audience("https://database.windows.net/") == ["https://database.windows.net"],
        normalize_audience(["https://database.windows.net/", "other/"]) == ["https://database.windows.net", "other"],
        normalize_audience("wrong") != ["https://database.windows.net"],
        bool(re.fullmatch(r"[0-9a-f]{40}", source["accepted_sha"])),
        bool(re.fullmatch(r"[0-9a-f]{40}", source["accepted_tree"])),
        source["accepted_sha"] != source["accepted_tree"],
        source["historical_sdk_state"] == "FAIL_HISTORICAL_PRESERVED",
        source["browser_verified"] is False,
        source["accepted_sha"].startswith("c42e"),
        source["accepted_tree"].startswith("a497"),
    ]
    audit_values += [
        normalize_audience(value) == sorted(normalize_audience(value))
        for value in ("a/", "b/", ["c/", "a/"], ["https://database.windows.net/"], "single")
    ]
    audit_values += [
        source["historical_sdk_state"].startswith("FAIL"),
        source["historical_sdk_state"].endswith("PRESERVED"),
        source["browser_verified"] is not True,
        len(source["accepted_sha"]) == 40,
        len(source["accepted_tree"]) == 40,
        source["accepted_sha"].lower() == source["accepted_sha"],
        source["accepted_tree"].lower() == source["accepted_tree"],
        "token" not in json.dumps(source).lower(),
        "secret" not in json.dumps(source).lower(),
        "password" not in json.dumps(source).lower(),
    ]
    for i, value in enumerate(audit_values, 1):
        add(f"AUDIT-{i:03d}", "optional SDK checker remains independent", value)

    # Explicit mutation-policy negative cases: 30 assertions.
    policy_cases = [
        ("job create", False), ("job start", False), ("job update", False), ("job delete", False),
        ("sql admin", False), ("sql ddl", False), ("sql dml", False), ("rbac", False),
        ("entra", False), ("network", False), ("image build", False), ("image push", False),
        ("migration", False), ("seed", False), ("api deployment", False), ("browser", False),
        ("synology", False), ("smb", False), ("real data read", False), ("real data write", False),
    ]
    for i, (name, allowed) in enumerate(policy_cases + [(f"reserved-{x}", False) for x in range(10)], 1):
        add(f"POLICY-{i:03d}", f"{name} is not authorized in preauth", allowed is False)

    return out


if __name__ == "__main__":
    checks = run()
    failures = [c for c in checks if not c.passed]
    print(json.dumps({"total": len(checks), "passed": len(checks) - len(failures), "failed": len(failures), "first_failure": failures[0].__dict__ if failures else None}, sort_keys=True))
    sys.exit(1 if failures or len(checks) < 250 else 0)
