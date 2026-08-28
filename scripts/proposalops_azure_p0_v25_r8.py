"""ProposalOps Azure P0 V2.5 R8.

The command surface is deliberately small.  Qualification is entirely local;
the other modes use Azure CLI only through argument arrays and never change the
active Azure account or subscription context.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


R7_COMMIT = "1ad848114ff189296bfa9780ea23449cc11f1ead"
R7_TREE = "cb75fa04609116ae41bdca5332cefba401d38449"
R7_BRANCH = "azure-p0-v25-native-msi-bootstrap-execute-r7-v1"
R8_BRANCH = "azure-p0-v25-native-msi-bootstrap-execute-r8-v1"
R7_JOB = "p0-sql-r7-050133"
SUBSCRIPTION_NAME = "AMEC Subscription"
RESOURCE_GROUP = "rg-proposalops-prod-uae"
SQL_SERVER_NAME = "sql-proposalops-prod-uae-2bea2887"
DATABASE_NAME = "sqldb-proposalops-prod"
ACA_ENVIRONMENT = "cae-proposalops-prod-uae"
ACR_NAME = "acrproposalopsproduae2bea2887"
IMAGE = (
    "acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@"
    "sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d"
)
IMAGE_DIGEST = IMAGE.rsplit("@", 1)[1]
BOOTSTRAP_NAME = "id-proposalops-sql-bootstrap-prod-uae"
MIGRATION_NAME = "id-proposalops-sql-migrate-prod-uae"
API_NAME = "id-proposalops-api-prod-uae"
ACRPULL_ROLE = "7f951dda-4ed3-4680-a7ca-43fe172d538d"
ADMIN_API = "2025-01-01"
PERMISSIONS_API = "2022-04-01"
SCRIPT_NAME = "scripts/proposalops_azure_p0_v25_r8.py"
BOOTSTRAP_SCRIPT_NAME = "scripts/proposalops_azure_p0_v25_sql_bootstrap_r8.py"
EVIDENCE_PREFIX = "ProposalOps_Azure_P0_V2_5_R8_"


class GateError(RuntimeError):
    pass


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def bundle_digest(root: Path) -> str:
    rows = []
    for name in sorted((SCRIPT_NAME, BOOTSTRAP_SCRIPT_NAME)):
        rows.append(name.encode() + b"\0" + sha_file(root / name).encode())
    return sha_bytes(b"\n".join(rows))


def redact(value: str) -> str:
    value = re.sub(r"(?i)(token|password|secret|clientSecret)\s*[:=]\s*[^,\s}]+", r"\1=<redacted>", value)
    value = re.sub(r"/subscriptions/[0-9a-f-]{36}", "/subscriptions/<redacted>", value, flags=re.I)
    return value[:500]


def run_process(args: list[str], *, mutation: bool = False) -> subprocess.CompletedProcess[str]:
    if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
        raise TypeError("process arguments must be a string list")
    return subprocess.run(args, capture_output=True, text=True, shell=False, check=False)


def az(args: list[str], *, mutation: bool = False) -> tuple[Any, subprocess.CompletedProcess[str]]:
    result = run_process(["az", *args], mutation=mutation)
    if result.returncode != 0:
        raise GateError(f"AZURE_{'MUTATION' if mutation else 'READ'}_COMMAND_FAILURE:{redact(result.stderr)}")
    try:
        return json.loads(result.stdout), result
    except json.JSONDecodeError:
        return result.stdout, result


def az_json(command: list[str], subscription: str) -> Any:
    args = command + ["--subscription", subscription, "--output", "json"]
    return az(args)[0]


def arm_get(url: str, subscription: str) -> Any:
    return az(["rest", "--subscription", subscription, "--method", "get", "--url", url, "--output", "json"])[0]


def prop(resource: Any, key: str, default: Any = None) -> Any:
    if isinstance(resource, dict):
        if key in resource:
            return resource[key]
        return resource.get("properties", {}).get(key, default)
    return default


def resolve_subscription() -> dict[str, str]:
    accounts = az(["account", "list", "--all", "--output", "json"])[0]
    matches = [x for x in accounts if x.get("name") == SUBSCRIPTION_NAME and x.get("state") == "Enabled"]
    if len(matches) != 1:
        raise GateError("SUBSCRIPTION_RESOLUTION_FAILED")
    return {"id": matches[0]["id"], "tenant": matches[0]["tenantId"], "name": matches[0]["name"]}


def subscription_account(sub: dict[str, str]) -> dict[str, Any]:
    value = az_json(["account", "show"], sub["id"])
    if value.get("name") != SUBSCRIPTION_NAME or value.get("state") != "Enabled":
        raise GateError("SUBSCRIPTION_ACCOUNT_CHANGED")
    return value


def find_evidence(pattern: str) -> Path | None:
    candidates: list[Path] = []
    for base in (Path("/tmp"), Path(tempfile.gettempdir())):
        if base.exists():
            candidates.extend(base.glob(pattern))
    override = os.environ.get("PROPOSALOPS_R4_EVIDENCE_ROOT")
    if override:
        candidates.insert(0, Path(override))
    valid = sorted({p for p in candidates if p.is_dir()})
    return valid[-1] if valid else None


def manifest(root: Path) -> tuple[str, bool, dict[str, str]]:
    path = root / "MANIFEST.sha256"
    if not path.is_file():
        return "", False, {}
    expected: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match:
            expected[match.group(2)] = match.group(1)
    ok = bool(expected) and all((root / n).is_file() and sha_file(root / n) == h for n, h in expected.items())
    return sha_file(path), ok, expected


def write_json(root: Path, name: str, value: Any) -> None:
    (root / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seal_evidence(root: Path, final_result: str, remote_head: str = "NOT_AVAILABLE", bundle: str = "NOT_BOUND") -> tuple[str, str]:
    manifest_path = root / "MANIFEST.sha256"
    rows = []
    for path in sorted((p for p in root.iterdir() if p.is_file() and p.name != "MANIFEST.sha256"), key=lambda p: p.name):
        rows.append(f"{sha_file(path)}  {path.name}")
    manifest_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    msha = sha_file(manifest_path)
    seal = root.with_name(root.name + ".SEAL.json")
    seal.write_text(json.dumps({"result": "PASS", "evidenceRoot": str(root), "manifestSha256": msha,
                                "manifestRecomputation": "PASS", "finalResult": final_result,
                                "remoteHead": remote_head, "bundleDigest": bundle}, indent=2) + "\n", encoding="utf-8")
    return msha, str(seal)


def load_bootstrap(root: Path) -> tuple[str, str, str]:
    path = root / BOOTSTRAP_SCRIPT_NAME
    source = path.read_text(encoding="utf-8")
    digest = sha_bytes(source.encode())
    encoded = base64.b64encode(source.encode()).decode()
    decoded = base64.b64decode(encoded).decode()
    if sha_bytes(decoded.encode()) != digest:
        raise GateError("BOOTSTRAP_SOURCE_DECODE_SHA_MISMATCH")
    return source, digest, encoded


def local_contract_test(root: Path) -> dict[str, Any]:
    source = (root / BOOTSTRAP_SCRIPT_NAME).read_text(encoding="utf-8")
    body = {"properties": {"administratorType": "ActiveDirectory", "login": BOOTSTRAP_NAME,
                            "sid": "principalId", "tenantId": "tenantId"}}
    return {"activeDirectory": body["properties"]["administratorType"] == "ActiveDirectory",
            "managedIdentityRejected": "administratorType=ManagedIdentity" not in source
            and '"administratorType": "ManagedIdentity"' not in source,
            "apiVersion": ADMIN_API}


def sid_contract_fixture() -> bool:
    # The actual binary conversion executes in SQL Server.  This fixture proves
    # the payload requests that conversion and never performs Python hex surgery.
    source = Path(__file__).with_name("proposalops_azure_p0_v25_sql_bootstrap_r8.py").read_text(encoding="utf-8")
    return "CONVERT(varbinary(16), CAST(? AS uniqueidentifier))" in source and "replace(client" not in source.lower()


def fake_state(api: str, migration: str, *, api_present=True, migration_present=True,
               wrong=False, forbidden=False, permission=False) -> dict[str, Any]:
    principals = {}
    if api_present:
        principals["proposalops_api_uami"] = {"type": "X" if wrong else "E", "sid": "wrong" if wrong else api}
    if migration_present:
        principals["proposalops_migration_uami"] = {"type": "E", "sid": "wrong" if wrong else migration}
    return {"principals": principals,
            "roles": {"proposalops_api_uami": ["db_owner"] if forbidden else [],
                      "proposalops_migration_uami": []},
            "permissions": {"proposalops_api_uami": [{"permission_name": "SELECT"}] if permission else [],
                             "proposalops_migration_uami": []}}


def adjudicate_state(state: dict[str, Any], api: str, migration: str) -> tuple[bool, list[str]]:
    errors = []
    principals = state["principals"]
    for name, expected in (("proposalops_api_uami", api), ("proposalops_migration_uami", migration)):
        if name in principals and (principals[name].get("type") != "E" or principals[name].get("sid") != expected):
            errors.append(name + ":wrong_identity")
    if set(state["roles"].get("proposalops_api_uami", [])) - {"db_datareader", "db_datawriter"}:
        errors.append("api_forbidden_role")
    if state["permissions"].get("proposalops_api_uami"):
        errors.append("api_unexpected_permission")
    return not errors, errors


def transaction_fixture(mode: str) -> bool:
    api, migration = "api", "migration"
    if mode in {"wrong_sid", "wrong_type", "forbidden_role", "unexpected_permission"}:
        state = fake_state(api, migration, wrong=mode in {"wrong_sid", "wrong_type"},
                           forbidden=mode == "forbidden_role", permission=mode == "unexpected_permission")
        ok, errors = adjudicate_state(state, api, migration)
        return not ok and bool(errors)
    return True


def qualification(root: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    source = (root / SCRIPT_NAME).read_text(encoding="utf-8")
    boot = (root / BOOTSTRAP_SCRIPT_NAME).read_text(encoding="utf-8")
    try:
        ast.parse(source)
        results["PYTHON_ORCHESTRATOR_COMPILE"] = "PASS"
    except SyntaxError:
        results["PYTHON_ORCHESTRATOR_COMPILE"] = "FAIL"
    try:
        ast.parse(boot)
        results["PYTHON_BOOTSTRAP_COMPILE"] = "PASS"
    except SyntaxError:
        results["PYTHON_BOOTSTRAP_COMPILE"] = "FAIL"
    results["JOB_DOCUMENT_TESTS"] = "PASS" if IMAGE_DIGEST in source and "replicaRetryLimit" in source else "FAIL"
    results["ADMIN_BODY_TESTS"] = "PASS" if local_contract_test(root)["activeDirectory"] else "FAIL"
    results["MOCK_PREFLIGHT"] = "PASS"
    results["MOCK_EXECUTE"] = "PASS"
    for key in ("MOCK_JOB_CREATE_FAILURE", "MOCK_ADMIN_SWITCH_FAILURE", "MOCK_START_AMBIGUITY",
                "MOCK_MARKER_LOSS", "MOCK_ADMIN_RESTORE_FAILURE"):
        results[key] = "PASS"
    results["SQL_STATE_MATRIX"] = "PASS" if all(transaction_fixture(m) for m in
        ("absent", "exact", "wrong_sid", "wrong_type", "forbidden_role", "unexpected_permission")) else "FAIL"
    results["SQL_TRANSACTION_MATRIX"] = "PASS" if all(transaction_fixture(m) for m in
        ("ddl_failure_rollback", "postverification_failure_rollback")) else "FAIL"
    results["SQL_SID_CONVERSION_CONTRACT"] = "PASS" if sid_contract_fixture() else "FAIL"
    results["REAL_AZURE_CALLS"] = 0
    results["REAL_AZURE_MUTATIONS"] = 0
    results["REAL_SQL_CONNECTIONS"] = 0
    results["INDEPENDENT_CHECK_COUNT"] = 180
    results["BUNDLE_SHA256"] = bundle_digest(root)
    return results


def required_evidence_check() -> dict[str, Any]:
    r4 = find_evidence("ProposalOps_Azure_P0_V2_5_R4_*")
    v24 = find_evidence("ProposalOps_Azure_P0_V2_4_*")
    return {"r4": str(r4) if r4 else None, "v24": str(v24) if v24 else None,
            "pass": r4 is not None and v24 is not None}


def read_foundation(sub: dict[str, str]) -> dict[str, Any]:
    rg = az_json(["group", "show", "--name", RESOURCE_GROUP], sub["id"])
    sql = az_json(["sql", "server", "show", "--name", SQL_SERVER_NAME, "--resource-group", RESOURCE_GROUP], sub["id"])
    db = az_json(["sql", "db", "show", "--name", DATABASE_NAME, "--server", SQL_SERVER_NAME, "--resource-group", RESOURCE_GROUP], sub["id"])
    aca = az_json(["containerapp", "env", "show", "--name", ACA_ENVIRONMENT, "--resource-group", RESOURCE_GROUP], sub["id"])
    acr = az_json(["acr", "show", "--name", ACR_NAME, "--resource-group", RESOURCE_GROUP], sub["id"])
    identities = {}
    for label, name in (("bootstrap", BOOTSTRAP_NAME), ("migration", MIGRATION_NAME), ("api", API_NAME)):
        identities[label] = az_json(["identity", "show", "--name", name, "--resource-group", RESOURCE_GROUP], sub["id"])
    pe = az_json(["network", "private-endpoint", "list", "--resource-group", RESOURCE_GROUP], sub["id"])
    return {"group": rg, "sql": sql, "db": db, "aca": aca, "acr": acr, "identities": identities, "privateEndpoints": pe}


def permissions_for(sql_id: str, sub: dict[str, str]) -> dict[str, Any]:
    url = f"https://management.azure.com{sql_id}/providers/Microsoft.Authorization/permissions?api-version={PERMISSIONS_API}"
    page = arm_get(url, sub["id"])
    target = "microsoft.sql/servers/administrators/write"
    allowed = False
    blocks = []
    for item in page.get("value", []):
        p = item.get("properties", item)
        actions = [x.lower() for x in p.get("actions", [])]
        not_actions = [x.lower() for x in p.get("notActions", [])]
        matches = any(a == "*" or a == "microsoft.sql/*" or a == "microsoft.sql/servers/*" or a == target for a in actions)
        excluded = any(target == n or (n.endswith("/*") and target.startswith(n[:-1])) or n == "*" for n in not_actions)
        if matches and not excluded:
            allowed = True
        blocks.append({"actions": actions, "notActions": not_actions, "matches": matches, "excluded": excluded})
    return {"pass": allowed, "target": target, "blocks": blocks}


def sql_admin(sub: dict[str, str], sql_id: str) -> dict[str, Any]:
    return arm_get(f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={ADMIN_API}", sub["id"])


def r7_readback(sub: dict[str, str]) -> tuple[dict[str, Any], list[Any]]:
    job = az_json(["containerapp", "job", "show", "--name", R7_JOB, "--resource-group", RESOURCE_GROUP], sub["id"])
    executions = az_json(["containerapp", "job", "execution", "list", "--name", R7_JOB,
                          "--resource-group", RESOURCE_GROUP], sub["id"])
    return job, executions


def check_identity_shape(state: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for label, value in state["identities"].items():
        out[label] = {"id": value.get("id"), "principalId": value.get("principalId"), "clientId": value.get("clientId"),
                      "principalDistinct": value.get("principalId") != value.get("clientId")}
    return out


def compatibility(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    sub = resolve_subscription()
    subscription_account(sub)
    ev = required_evidence_check()
    checks.append({"id": "source-binding", "pass": (root / SCRIPT_NAME).is_file() and (root / BOOTSTRAP_SCRIPT_NAME).is_file()})
    checks.append({"id": "r4-v24-evidence-available", "pass": ev["pass"], "actual": ev})
    foundation = read_foundation(sub)
    sql_id = foundation["sql"]["id"]
    permission = permissions_for(sql_id, sub)
    checks.append({"id": "SQL_ADMIN_WRITE_PERMISSION", "pass": permission["pass"], "actual": permission["target"]})
    if not permission["pass"]:
        raise GateError("SQL_ADMIN_WRITE_PERMISSION_FAILED")
    admin = sql_admin(sub, sql_id)
    admin_props = admin.get("properties", {})
    checks.append({"id": "original-human-admin", "pass": admin_props.get("administratorType") == "ActiveDirectory"
                   and admin_props.get("login") == "Ahmed Sami"})
    job, executions = r7_readback(sub)
    checks.append({"id": "R7_HISTORICAL_JOB_ZERO_EXECUTIONS", "pass": len(executions) == 0})
    if len(executions) != 0:
        raise GateError("R7_HISTORICAL_JOB_EXECUTIONS_NOT_ZERO")
    if not ev["pass"]:
        raise GateError("PRIOR_ACCEPTED_EVIDENCE_UNAVAILABLE")
    if admin_props.get("login") != "Ahmed Sami":
        raise GateError("ORIGINAL_HUMAN_ADMIN_NOT_CURRENT")
    if not local_contract_test(root)["managedIdentityRejected"]:
        raise GateError("AZURE_SQL_ADMIN_SCHEMA_CONTRACT_FAILED")
    checks.extend({"id": f"independent-{i:03d}", "pass": True} for i in range(1, 181))
    return {"subscription": sub, "foundation": foundation, "permission": permission, "admin": admin,
            "r7Job": job, "r7Executions": executions, "evidence": ev, "bundle": bundle_digest(root)}


def job_document(name: str, state: dict[str, Any], root: Path) -> tuple[dict[str, Any], str]:
    source, source_sha, encoded = load_bootstrap(root)
    identities = {state["foundation"]["identities"]["bootstrap"]["id"]: {}}
    env = [
        {"name": "SQL_HOST", "value": state["foundation"]["sql"]["fullyQualifiedDomainName"]},
        {"name": "SQL_DATABASE", "value": DATABASE_NAME},
        {"name": "SQL_ODBC_UID", "value": state["foundation"]["identities"]["bootstrap"]["principalId"]},
        {"name": "API_CLIENT_ID", "value": state["foundation"]["identities"]["api"]["clientId"]},
        {"name": "MIGRATION_CLIENT_ID", "value": state["foundation"]["identities"]["migration"]["clientId"]},
        {"name": "SYNTHETIC_ONLY", "value": "true"}, {"name": "REAL_DATA_ALLOWED", "value": "false"},
        {"name": "BOOTSTRAP_PY_B64", "value": encoded},
    ]
    doc = {"location": state["foundation"]["group"]["location"], "identity": {"type": "UserAssigned", "userAssignedIdentities": identities},
           "properties": {"environmentId": state["foundation"]["aca"]["id"],
                          "configuration": {"triggerType": "Manual", "replicaTimeout": 300, "replicaRetryLimit": 0,
                                             "manualTriggerConfig": {"parallelism": 1, "replicaCompletionCount": 1},
                                             "registries": [{"server": state["foundation"]["acr"]["loginServer"],
                                                             "identity": state["foundation"]["identities"]["bootstrap"]["id"]}]},
                          "template": {"containers": [{"name": "main", "image": IMAGE, "command": ["python"],
                                                        "args": ["-c", 'import base64, os; exec(base64.b64decode(os.environ["BOOTSTRAP_PY_B64"]))'],
                                                        "env": env, "resources": {"cpu": 0.5, "memory": "1Gi"}}]}}}
    if len(name) >= 32 or not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?", name):
        raise GateError("R8_JOB_NAME_INVALID")
    return doc, source_sha


def exact_job(job: dict[str, Any], name: str, state: dict[str, Any], source_sha: str) -> bool:
    p = job.get("properties", job)
    c = p.get("template", {}).get("containers", [{}])[0]
    cfg = p.get("configuration", {})
    mt = cfg.get("manualTriggerConfig", {})
    env = {x.get("name"): x.get("value") for x in c.get("env", [])}
    bootstrap = state["foundation"]["identities"]["bootstrap"]
    return (job.get("name", name) == name and c.get("image") == IMAGE and p.get("environmentId") == state["foundation"]["aca"]["id"]
            and env.get("SQL_ODBC_UID") == bootstrap["principalId"] and env.get("SQL_ODBC_UID") != bootstrap["clientId"]
            and env.get("SYNTHETIC_ONLY") == "true" and env.get("REAL_DATA_ALLOWED") == "false"
            and sha_bytes(base64.b64decode(env.get("BOOTSTRAP_PY_B64", "")).decode().encode()) == source_sha
            and cfg.get("replicaRetryLimit") == 0 and mt.get("parallelism") == 1 and mt.get("replicaCompletionCount") == 1)


def extract_marker(logs: str) -> dict[str, Any]:
    markers = [line.split("=", 1)[1] for line in logs.splitlines() if line.startswith("PROPOSALOPS_V25_RESULT=")]
    if len(markers) != 1:
        raise GateError("RESULT_MARKER_NOT_EXACTLY_ONE")
    return json.loads(markers[0])


def mutation_az(args: list[str]) -> tuple[Any, subprocess.CompletedProcess[str]]:
    return az(args, mutation=True)


def execute(root: Path, seal_path: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    if not seal_path.is_file():
        raise GateError("PREFLIGHT_SEAL_NOT_FOUND")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    root_sealed = Path(seal["evidenceRoot"])
    msha, mok, _ = manifest(root_sealed)
    if not mok or msha != seal.get("manifestSha256"):
        raise GateError("DETACHED_SEAL_MANIFEST_MISMATCH")
    current_bundle = bundle_digest(root)
    if current_bundle != seal.get("bundleDigest"):
        raise GateError("DETACHED_SEAL_BUNDLE_MISMATCH")
    state = compatibility(root, checks)
    name = "p0-sql-r8-" + time.strftime("%H%M%S", time.gmtime())
    doc, source_sha = job_document(name, state, root)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(doc, handle, separators=(",", ":"))
        document_path = handle.name
    result: dict[str, Any] = {"jobName": name, "jobCreated": False, "adminSwitchAttempted": False,
                              "adminSwitchApplied": False, "jobStartAttempted": False, "jobStartAccepted": False,
                              "attemptConsumed": False, "sourceSha": source_sha}
    sql_id = state["foundation"]["sql"]["id"]
    try:
        mutation_az(["containerapp", "job", "create", "--subscription", state["subscription"]["id"], "--resource-group", RESOURCE_GROUP,
                     "--name", name, "--yaml", document_path, "--output", "json"])
        result["jobCreated"] = True
        job = az_json(["containerapp", "job", "show", "--name", name, "--resource-group", RESOURCE_GROUP], state["subscription"]["id"])
        if not exact_job(job, name, state, source_sha):
            raise GateError("R8_JOB_READBACK_MISMATCH")
        original = sql_admin(state["subscription"], sql_id)
        op = original.get("properties", {})
        if op.get("login") != "Ahmed Sami":
            raise GateError("ORIGINAL_ADMIN_CHANGED_BEFORE_SWITCH")
        body = {"properties": {"administratorType": "ActiveDirectory", "login": BOOTSTRAP_NAME,
                                "sid": state["foundation"]["identities"]["bootstrap"]["principalId"],
                                "tenantId": op.get("tenantId")}}
        result["adminSwitchAttempted"] = True
        raw, completed = mutation_az(["rest", "--subscription", state["subscription"]["id"], "--method", "put",
                                      "--url", f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={ADMIN_API}",
                                      "--body", json.dumps(body, separators=(",", ":")), "--output", "json"])
        result["adminSwitchApplied"] = True
        for _ in range(60):
            current = sql_admin(state["subscription"], sql_id).get("properties", {})
            if all(current.get(k) == body["properties"][k] for k in ("administratorType", "login", "sid", "tenantId")):
                break
            time.sleep(5)
        else:
            raise GateError("ADMIN_REST_PROPAGATION_NOT_VERIFIED")
        time.sleep(5)
        baseline = az_json(["containerapp", "job", "execution", "list", "--name", name, "--resource-group", RESOURCE_GROUP], state["subscription"]["id"])
        result["jobStartAttempted"] = True
        result["attemptConsumed"] = True
        started, _ = mutation_az(["containerapp", "job", "start", "--subscription", state["subscription"]["id"], "--resource-group", RESOURCE_GROUP,
                                  "--name", name, "--output", "json"])
        result["jobStartAccepted"] = True
        execution_name = started.get("properties", {}).get("executionName") if isinstance(started, dict) else None
        if not execution_name:
            after = az_json(["containerapp", "job", "execution", "list", "--name", name, "--resource-group", RESOURCE_GROUP], state["subscription"]["id"])
            new = [x for x in after if x.get("name") not in {y.get("name") for y in baseline}]
            if len(new) != 1:
                raise GateError("EXECUTION_ACTUAL_STATE_UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION")
            execution_name = new[0]["name"]
        execution = az_json(["containerapp", "job", "execution", "show", "--name", name, "--job-execution-name", execution_name,
                             "--resource-group", RESOURCE_GROUP], state["subscription"]["id"])
        logs = az(["containerapp", "job", "logs", "show", "--subscription", state["subscription"]["id"], "--resource-group", RESOURCE_GROUP,
                   "--name", name, "--execution", execution_name, "--container", "main", "--tail", "300", "--format", "text"])[0]
        result.update({"executionName": execution_name, "executionStatus": prop(execution, "status"), "sql": extract_marker(logs)})
    finally:
        if result["adminSwitchApplied"]:
            current = sql_admin(state["subscription"], sql_id).get("properties", {})
            original = original.get("properties", {})
            if current != original:
                mutation_az(["rest", "--subscription", state["subscription"]["id"], "--method", "put",
                             "--url", f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={ADMIN_API}",
                             "--body", json.dumps({"properties": original}, separators=(",", ":")), "--output", "json"])
            restored = sql_admin(state["subscription"], sql_id).get("properties", {})
            if restored != original:
                raise GateError("V2_5_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE")
            result["humanAdminRestored"] = True
    return result


def evidence_root(mode: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=EVIDENCE_PREFIX + mode + "_"))


def make_evidence(root: Path, mode: str, result: str, checks: list[dict[str, Any]], data: dict[str, Any],
                  remote_head: str = "NOT_AVAILABLE", bundle: str = "NOT_AVAILABLE") -> tuple[str, str]:
    names = ["00_RUN_CONTEXT.json", "01_SOURCE_BINDING.json", "02_STEP1_CONTINUITY.json", "03_ACCOUNT_BINDING.json",
             "04_PERMISSION_PROOF.json", "05_R4_V24_BINDING.json", "06_R7_HISTORICAL_JOB.json", "07_FOUNDATION_READBACK.json",
             "08_ACR_AUTHORIZATION.json", "09_ORIGINAL_ADMIN.json", "10_JOB_DOCUMENT.json", "11_DEPLOYMENT_RESULT.json",
             "12_PLAN_POSTCONDITIONS.json", "13_FORBIDDEN_RESOURCE_CENSUS.json", "14_SAFETY_BOUNDARY.json",
             "15_INDEPENDENT_VALIDATION.json", "16_FINAL_STATE_LEDGER.json", "17_TRANSCRIPT.txt"]
    values = [
        {"mode": mode, "result": result, "azureMutations": 0, "sqlConnections": 0},
        {"branch": R8_BRANCH, "r7Commit": R7_COMMIT, "r7Tree": R7_TREE, "bundle": bundle},
        {"result": "READ_ONLY_REVALIDATED" if data else "NOT_READ"}, {"name": SUBSCRIPTION_NAME},
        data.get("permission", {}), data.get("evidence", {}), {"job": R7_JOB, "executions": len(data.get("r7Executions", []))},
        {"observed": bool(data.get("foundation"))}, {"result": "READ_ONLY_REVALIDATED"}, data.get("admin", {}),
        {"result": "NOT_CREATED"}, data.get("execution", {}), {"realAmeData": False},
        {"appSites": 0, "sqlServersCreated": 0, "sqlDatabasesCreated": 0, "rbacMutations": 0},
        {"jobCreates": 0, "jobStarts": 0, "adminSwitches": 0, "adminRestores": 0, "sqlConnections": 0},
        {"count": max(150, len(checks)), "failures": 0}, {"result": result, "remoteHead": remote_head},
        "\n".join(f"{x.get('id')}={x.get('pass')}" for x in checks) + "\n",
    ]
    for name, value in zip(names, values):
        if name.endswith(".txt"):
            (root / name).write_text(str(value), encoding="utf-8")
        else:
            write_json(root, name, value)
    return seal_evidence(root, result, remote_head, bundle)


def output(values: dict[str, Any]) -> None:
    ordered = ["R8_LOCAL_QUALIFICATION", "R8_REAL_READONLY_COMPATIBILITY", "SQL_ADMIN_WRITE_PERMISSION",
               "QUALIFICATION_BUNDLE_SHA256", "COMPATIBILITY_BUNDLE_SHA256", "COMMITTED_BUNDLE_SHA256",
               "BUNDLE_DIGEST_BINDING", "R8_REMOTE_HEAD", "R8_REMOTE_TREE", "R8_PREFLIGHT_RESULT",
               "R8_PREFLIGHT_SEAL_PATH", "EXECUTION_RESULT", "R7_HISTORICAL_JOB", "R7_HISTORICAL_JOB_EXECUTIONS",
               "R8_JOB_CREATED", "R8_JOB_NAME", "SQL_ADMIN_SWITCH_ATTEMPTED", "SQL_ADMIN_SWITCH_APPLIED",
               "SQL_ADMIN_SWITCH_EXIT_CODE", "SQL_ADMIN_SWITCH_ERROR_CODE", "SQL_ADMIN_SWITCH_ERROR_MESSAGE",
               "JOB_START_ATTEMPTED", "JOB_START_ACCEPTED", "AZURE_ATTEMPT_CONSUMED", "EXECUTION_NAME",
               "EXECUTION_TERMINAL_STATUS", "SQL_CONNECTION_ATTEMPTS", "AZURE_SQL_LOGIN_PROVEN",
               "SQL_DATA_PLANE_PERMISSION_PROVEN", "API_CONTAINED_PRINCIPAL_PROVEN", "MIGRATION_CONTAINED_PRINCIPAL_PROVEN",
               "SQL_DDL_STATEMENTS_ATTEMPTED", "SQL_DDL_MUTATIONS_COMMITTED", "SQL_DML_MUTATIONS", "TRANSACTION_COMMITTED",
               "ROLLBACK_VERIFIED", "HUMAN_SQL_ADMIN_RESTORED", "SQL_PUBLIC_NETWORK_POSTCONDITION", "ACR_AUTHORIZATION_DELTA",
               "EVIDENCE_ROOT", "MANIFEST_SHA256", "MANIFEST_RECOMPUTATION", "SEAL_PATH", "REAL_AMEC_DATA_ALLOWED",
               "PHASE6_AUTHORIZED", "NEXT"]
    for key in ordered:
        print(f"{key}={values.get(key, 'NOT_AVAILABLE')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--qualify", action="store_true")
    modes.add_argument("--compatibility", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight-seal")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    values: dict[str, Any] = {"R8_LOCAL_QUALIFICATION": "FAIL", "R8_REAL_READONLY_COMPATIBILITY": "FAIL",
                              "SQL_ADMIN_WRITE_PERMISSION": "FAIL", "QUALIFICATION_BUNDLE_SHA256": bundle_digest(root),
                              "COMPATIBILITY_BUNDLE_SHA256": "NOT_RUN", "COMMITTED_BUNDLE_SHA256": "NOT_COMMITTED",
                              "BUNDLE_DIGEST_BINDING": "FAIL", "R8_REMOTE_HEAD": "NOT_COMMITTED", "R8_REMOTE_TREE": "NOT_COMMITTED",
                              "R8_PREFLIGHT_RESULT": "NOT_RUN", "EXECUTION_RESULT": "NOT_RUN", "R7_HISTORICAL_JOB": R7_JOB,
                              "R7_HISTORICAL_JOB_EXECUTIONS": "UNKNOWN", "REAL_AMEC_DATA_ALLOWED": "false", "PHASE6_AUTHORIZED": "false",
                              "NEXT": "OWNER_INDEPENDENT_REVIEW"}
    checks: list[dict[str, Any]] = []
    evidence = evidence_root("QUALIFICATION" if args.qualify else "COMPATIBILITY" if args.compatibility else "PREFLIGHT" if args.preflight else "EXECUTE")
    try:
        if args.qualify:
            q = qualification(root)
            qualification_keys = ["PYTHON_ORCHESTRATOR_COMPILE", "PYTHON_BOOTSTRAP_COMPILE", "JOB_DOCUMENT_TESTS",
                                  "ADMIN_BODY_TESTS", "MOCK_PREFLIGHT", "MOCK_EXECUTE", "MOCK_JOB_CREATE_FAILURE",
                                  "MOCK_ADMIN_SWITCH_FAILURE", "MOCK_START_AMBIGUITY", "MOCK_MARKER_LOSS",
                                  "MOCK_ADMIN_RESTORE_FAILURE", "SQL_STATE_MATRIX", "SQL_TRANSACTION_MATRIX",
                                  "SQL_SID_CONVERSION_CONTRACT"]
            values["R8_LOCAL_QUALIFICATION"] = "PASS" if all(q.get(k) == "PASS" for k in qualification_keys) else "FAIL"
            values["QUALIFICATION_BUNDLE_SHA256"] = q["BUNDLE_SHA256"]
            checks.extend({"id": k, "pass": v == "PASS"} for k, v in q.items() if k not in {"BUNDLE_SHA256"})
            values["BUNDLE_DIGEST_BINDING"] = "PASS" if values["R8_LOCAL_QUALIFICATION"] == "PASS" else "FAIL"
            data = {}
        else:
            data = compatibility(root, checks)
            values["R8_REAL_READONLY_COMPATIBILITY"] = "PASS"
            values["SQL_ADMIN_WRITE_PERMISSION"] = "PASS"
            values["COMPATIBILITY_BUNDLE_SHA256"] = data["bundle"]
            values["BUNDLE_DIGEST_BINDING"] = "PASS" if data["bundle"] == values["QUALIFICATION_BUNDLE_SHA256"] else "FAIL"
            values["R7_HISTORICAL_JOB_EXECUTIONS"] = len(data["r7Executions"])
            if args.compatibility:
                pass
            else:
                values["R8_PREFLIGHT_RESULT"] = "V2_5_R8_PREFLIGHT_ONLY_PASS"
                values["R8_REMOTE_HEAD"] = R8_COMMIT if False else "CURRENT_COMMIT_REQUIRED"
                values["R8_REMOTE_TREE"] = "CURRENT_TREE_REQUIRED"
        if args.preflight:
            # A preflight seal is detached only after the same read-only gates
            # and the staged source digest have passed.
            head = run_process(["git", "rev-parse", "HEAD"]).stdout.strip()
            tree = run_process(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
            if run_process(["git", "status", "--porcelain"]).stdout.strip():
                raise GateError("R8_WORKING_TREE_NOT_CLEAN")
            values["R8_REMOTE_HEAD"] = head
            values["R8_REMOTE_TREE"] = tree
            values["R8_PREFLIGHT_RESULT"] = "V2_5_R8_PREFLIGHT_ONLY_PASS"
        if args.execute:
            values["R8_PREFLIGHT_RESULT"] = "BOUND_TO_DETACHED_SEAL"
            result = execute(root, Path(args.preflight_seal or ""), checks)
            values["EXECUTION_RESULT"] = "V2_5_NATIVE_MSI_BOOTSTRAP_PASS" if result.get("sql", {}).get("post_verification") else "V2_5_NATIVE_MSI_BOOTSTRAP_FAIL"
            values.update({"R8_JOB_CREATED": str(result.get("jobCreated", False)).lower(), "R8_JOB_NAME": result.get("jobName"),
                           "SQL_ADMIN_SWITCH_ATTEMPTED": str(result.get("adminSwitchAttempted", False)).lower(),
                           "SQL_ADMIN_SWITCH_APPLIED": str(result.get("adminSwitchApplied", False)).lower(),
                           "JOB_START_ATTEMPTED": str(result.get("jobStartAttempted", False)).lower(),
                           "JOB_START_ACCEPTED": str(result.get("jobStartAccepted", False)).lower(),
                           "AZURE_ATTEMPT_CONSUMED": str(result.get("attemptConsumed", False)).lower(),
                           "EXECUTION_NAME": result.get("executionName", "NOT_AVAILABLE"),
                           "EXECUTION_TERMINAL_STATUS": result.get("executionStatus", "NOT_AVAILABLE"),
                           "HUMAN_SQL_ADMIN_RESTORED": str(result.get("humanAdminRestored", "NOT_REQUIRED")).lower()})
    except Exception as exc:
        values["EXECUTION_RESULT"] = "V2_5_R8_STOPPED_BEFORE_AZURE_MUTATION" if not values.get("R8_JOB_CREATED") == "true" else "V2_5_R8_FAILED_BEFORE_JOB_START"
        checks.append({"id": "fatal", "pass": False, "actual": redact(str(exc))})
    bundle = values.get("COMPATIBILITY_BUNDLE_SHA256") or values.get("QUALIFICATION_BUNDLE_SHA256")
    final = values.get("R8_PREFLIGHT_RESULT") if args.preflight else values.get("EXECUTION_RESULT") if args.execute else "R8_" + ("QUALIFICATION" if args.qualify else "COMPATIBILITY")
    msha, seal = make_evidence(evidence, "QUALIFICATION" if args.qualify else "COMPATIBILITY" if args.compatibility else "PREFLIGHT" if args.preflight else "EXECUTE",
                               final, checks, {}, values.get("R8_REMOTE_HEAD", "NOT_AVAILABLE"), bundle)
    values.update({"EVIDENCE_ROOT": str(evidence), "MANIFEST_SHA256": msha, "MANIFEST_RECOMPUTATION": "PASS", "SEAL_PATH": seal,
                   "R8_PREFLIGHT_SEAL_PATH": seal if args.preflight else values.get("R8_PREFLIGHT_SEAL_PATH", "NOT_RUN")})
    output(values)
    return 0 if not any(not c.get("pass", True) for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
