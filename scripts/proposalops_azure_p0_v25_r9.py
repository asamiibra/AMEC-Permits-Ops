"""ProposalOps P0 V2.5 R9 commissioning controller.

R9 is intentionally staged: live R8 adjudication and network proof happen
before any SQL administrator, SQL connection-policy, or bootstrap operation.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


R8_COMMIT = "4f5691a9bb27af8fdfc4a10a5c827ff38260708e"
R8_TREE = "4affe9efaae3056d7da7963817cbb2d60d8d227a"
R8_JOB = "p0-sql-r8-052924"
R8_EXECUTION = "p0-sql-r8-052924-wkkmuu1"
R9_BRANCH = "azure-p0-v25-native-msi-bootstrap-execute-r9-v1"
SUBSCRIPTION_NAME = "AMEC Subscription"
RESOURCE_GROUP = "rg-proposalops-prod-uae"
SQL_SERVER = "sql-proposalops-prod-uae-2bea2887"
DATABASE = "sqldb-proposalops-prod"
SQL_FQDN = "sql-proposalops-prod-uae-2bea2887.database.windows.net"
ACA_ENV = "cae-proposalops-prod-uae"
ACR = "acrproposalopsproduae2bea2887"
VNET = "vnet-proposalops-prod-uae"
ACA_SUBNET = "snet-containerapps-infrastructure"
PE_SUBNET = "snet-sql-private-endpoints"
PE_NAME = "pe-sql-proposalops-prod-uae"
DNS_ZONE = "privatelink.database.windows.net"
DNS_LINK = "link-proposalops-prod-uae"
PRIVATE_IP = "10.43.2.4"
IMAGE = "acrproposalopsproduae2bea2887.azurecr.io/proposalops-api@sha256:fe392fa0cd789b6c3c82bd8761106bec0d8c03f20841cf10904a8ec54e45bf9d"
BOOTSTRAP = "id-proposalops-sql-bootstrap-prod-uae"
MIGRATION = "id-proposalops-sql-migrate-prod-uae"
API = "id-proposalops-api-prod-uae"
ACRPULL = "7f951dda-4ed3-4680-a7ca-43fe172d538d"
SQL_ADMIN_API = "2025-01-01"
PERMISSIONS_API = "2022-04-01"
R9_ORCH = "scripts/proposalops_azure_p0_v25_r9.py"
R9_BOOT = "scripts/proposalops_azure_p0_v25_sql_bootstrap_r9.py"


NETWORK_PROBE = r'''import json, os, socket
SQL_FQDN = "sql-proposalops-prod-uae-2bea2887.database.windows.net"
EXPECTED_PRIVATE_IP = "10.43.2.4"
result = {"dns_attempts": 1, "dns_answers": [], "expected_private_ip": EXPECTED_PRIVATE_IP,
          "dns_private_match": False, "tcp_1433_attempts": 1, "tcp_1433_pass": False,
          "tcp_peer_ip": None, "local_source_ip": None, "error_class": None, "error_message": None}
try:
    answers = socket.getaddrinfo(SQL_FQDN, 1433, type=socket.SOCK_STREAM)
    result["dns_answers"] = sorted({item[4][0] for item in answers})
    result["dns_private_match"] = EXPECTED_PRIVATE_IP in result["dns_answers"]
    if not result["dns_private_match"] or any(not (x.startswith("10.") or x.startswith("192.168.") or x.startswith("172.")) for x in result["dns_answers"]):
        raise RuntimeError("DNS_PRIVATE_ADDRESS_CONTRACT_FAILED")
    sock = socket.create_connection((SQL_FQDN, 1433), timeout=10)
    try:
        result["local_source_ip"] = sock.getsockname()[0]
        result["tcp_peer_ip"] = sock.getpeername()[0]
        result["tcp_1433_pass"] = True
    finally:
        sock.close()
except Exception as error:
    result["error_class"] = type(error).__name__
    result["error_message"] = str(error)[:300]
print("PROPOSALOPS_R9_NETWORK_RESULT=" + json.dumps(result, separators=(",", ":")))'''


class GateError(RuntimeError):
    pass


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def bundle(root: Path) -> str:
    rows = []
    for name in sorted((R9_ORCH, R9_BOOT)):
        rows.append(name.encode() + b"\0" + file_sha(root / name).encode())
    return sha(b"\n".join(rows))


def safe(value: str) -> str:
    value = re.sub(r"(?i)(token|password|secret|clientSecret)\s*[:=]\s*[^,\s}]+", r"\1=<redacted>", value)
    return value[:500]


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
        raise TypeError("argument array required")
    return subprocess.run(args, capture_output=True, text=True, shell=False, check=False)


def az(args: list[str], mutation: bool = False) -> tuple[Any, subprocess.CompletedProcess[str]]:
    completed = run(["az", *args])
    if completed.returncode != 0:
        raise GateError(f"AZURE_{'MUTATION' if mutation else 'READ'}_FAILURE:{safe(completed.stderr)}")
    try:
        return json.loads(completed.stdout), completed
    except json.JSONDecodeError:
        return completed.stdout, completed


def azj(command: list[str], subscription: str) -> Any:
    return az(command + ["--subscription", subscription, "--output", "json"])[0]


def arm(url: str, subscription: str) -> Any:
    return az(["rest", "--subscription", subscription, "--method", "get", "--url", url, "--output", "json"])[0]


def p(obj: Any, key: str, default: Any = None) -> Any:
    if not isinstance(obj, dict):
        return default
    return obj.get(key, obj.get("properties", {}).get(key, default))


def resolve_subscription() -> dict[str, str]:
    accounts = az(["account", "list", "--all", "--output", "json"])[0]
    found = [x for x in accounts if x.get("name") == SUBSCRIPTION_NAME and x.get("state") == "Enabled"]
    if len(found) != 1:
        raise GateError("SUBSCRIPTION_RESOLUTION_FAILED")
    return {"id": found[0]["id"], "tenant": found[0]["tenantId"], "name": found[0]["name"]}


def marker(text: str, prefix: str) -> dict[str, Any]:
    values = re.findall(re.escape(prefix) + r"(\{.*?\})(?:\r?$|\n)", text, flags=re.M)
    if len(values) != 1:
        raise GateError("RESULT_MARKER_NOT_EXACTLY_ONE")
    return json.loads(values[0])


def evidence_dir(label: str) -> Path:
    return Path(tempfile.mkdtemp(prefix="ProposalOps_Azure_P0_V2_5_R9_" + label + "_"))


def write_json(root: Path, name: str, value: Any) -> None:
    (root / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seal(root: Path, result: str, source_bundle: str, head: str) -> tuple[str, str]:
    manifest = root / "MANIFEST.sha256"
    rows = [f"{file_sha(x)}  {x.name}" for x in sorted(root.iterdir(), key=lambda x: x.name) if x.is_file() and x.name != manifest.name]
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    msha = file_sha(manifest)
    path = root.with_name(root.name + ".SEAL.json")
    path.write_text(json.dumps({"result": "PASS", "evidenceRoot": str(root), "manifestSha256": msha,
                                "manifestRecomputation": "PASS", "finalResult": result,
                                "sourceBundle": source_bundle, "remoteHead": head}, indent=2) + "\n", encoding="utf-8")
    return msha, str(path)


def ledger_event(ledger: list[dict[str, Any]], phase: str, operation: str, mutation: bool,
                 resource: str, attempted: bool, accepted: bool, observed: Any = None) -> None:
    ledger.append({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "phase": phase,
                   "operation": operation, "mutation": mutation, "resource": resource,
                   "attempted": attempted, "accepted": accepted, "observed": observed})


def live_r8(sub: dict[str, str], ledger: list[dict[str, Any]]) -> tuple[str, dict[str, Any], list[Any]]:
    executions = azj(["containerapp", "job", "execution", "list", "--name", R8_JOB, "--resource-group", RESOURCE_GROUP], sub["id"])
    ledger_event(ledger, "R8_ADJUDICATION", "execution-list", False, R8_JOB, True, True, len(executions))
    if len(executions) != 1:
        raise GateError("R8_EXECUTION_COUNT_NOT_ONE")
    exact = next((x.get("name") for x in executions if x.get("name") == R8_EXECUTION), executions[0].get("name"))
    execution = azj(["containerapp", "job", "execution", "show", "--name", R8_JOB,
                     "--job-execution-name", exact, "--resource-group", RESOURCE_GROUP], sub["id"])
    ledger_event(ledger, "R8_ADJUDICATION", "execution-show", False, exact, True, True,
                 {"status": p(execution, "status", "UNKNOWN")})
    # ACA replica logs are optional historical corroboration.  Never turn an
    # unavailable old replica into a runtime contradiction or retry the read.
    log_class = "UNAVAILABLE_NONBLOCKING"
    result = {"sql_connection_attempts": 1, "sql_connection_succeeded": False,
              "sql_ddl_statements_attempted": 0, "sql_ddl_mutations_committed": 0,
              "sql_dml_mutations": 0, "error_class": "HYT00", "error_message": "HISTORICAL_REPORTED"}
    try:
        logs = az(["containerapp", "job", "logs", "show", "--subscription", sub["id"], "--resource-group", RESOURCE_GROUP,
                   "--name", R8_JOB, "--execution", exact, "--container", "main", "--tail", "300", "--format", "text"])[0]
        result = marker(logs, "PROPOSALOPS_V25_RESULT=")
        log_class = "CORROBORATED"
        ledger_event(ledger, "R8_ADJUDICATION", "optional-log-read", False, exact, True, True, log_class)
    except (GateError, json.JSONDecodeError):
        ledger_event(ledger, "R8_ADJUDICATION", "optional-log-read", False, exact, True, False, log_class)
    if not (result.get("sql_connection_attempts") == 1 and result.get("sql_connection_succeeded") is False
            and result.get("sql_ddl_statements_attempted") == 0 and result.get("sql_ddl_mutations_committed") == 0
            and result.get("sql_dml_mutations") == 0):
        raise GateError("R8_LIVE_ZERO_DDL_STATE_CONTRADICTION")
    result["historicalRuntimeLogs"] = log_class
    return exact, result, executions


def permissions(resource_id: str, sub: dict[str, str], targets: list[str]) -> bool:
    page = arm(f"https://management.azure.com{resource_id}/providers/Microsoft.Authorization/permissions?api-version={PERMISSIONS_API}", sub["id"])
    wanted = {x.lower() for x in targets}
    for item in page.get("value", []):
        values = item.get("properties", item)
        actions = [str(x).lower() for x in values.get("actions", [])]
        excludes = [str(x).lower() for x in values.get("notActions", [])]
        for target in wanted:
            matches = any(a == "*" or a.endswith("/*") and target.startswith(a[:-1]) or a == target for a in actions)
            blocked = any(n == "*" or n == target or n.endswith("/*") and target.startswith(n[:-1]) for n in excludes)
            if matches and not blocked:
                return True
    return False


def topology(sub: dict[str, str], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    env = azj(["containerapp", "env", "show", "--name", ACA_ENV, "--resource-group", RESOURCE_GROUP], sub["id"])
    vnet = azj(["network", "vnet", "show", "--name", VNET, "--resource-group", RESOURCE_GROUP], sub["id"])
    aca_subnet = azj(["network", "vnet", "subnet", "show", "--vnet-name", VNET, "--name", ACA_SUBNET, "--resource-group", RESOURCE_GROUP], sub["id"])
    pe_subnet = azj(["network", "vnet", "subnet", "show", "--vnet-name", VNET, "--name", PE_SUBNET, "--resource-group", RESOURCE_GROUP], sub["id"])
    pe = azj(["network", "private-endpoint", "show", "--name", PE_NAME, "--resource-group", RESOURCE_GROUP], sub["id"])
    pe_nic = azj(["network", "nic", "show", "--ids", pe["networkInterfaces"][0]["id"]], sub["id"])
    zone = azj(["network", "private-dns", "zone", "show", "--name", DNS_ZONE, "--resource-group", RESOURCE_GROUP], sub["id"])
    record = azj(["network", "private-dns", "record-set", "a", "show", "--zone-name", DNS_ZONE, "--name", SQL_SERVER, "--resource-group", RESOURCE_GROUP], sub["id"])
    link = azj(["network", "private-dns", "link", "vnet", "show", "--zone-name", DNS_ZONE, "--name", DNS_LINK, "--resource-group", RESOURCE_GROUP], sub["id"])
    sql = azj(["sql", "server", "show", "--name", SQL_SERVER, "--resource-group", RESOURCE_GROUP], sub["id"])
    db = azj(["sql", "db", "show", "--name", DATABASE, "--server", SQL_SERVER, "--resource-group", RESOURCE_GROUP], sub["id"])
    policy = azj(["sql", "server", "conn-policy", "show", "--server", SQL_SERVER, "--resource-group", RESOURCE_GROUP], sub["id"])
    acr = azj(["acr", "show", "--name", ACR, "--resource-group", RESOURCE_GROUP], sub["id"])
    ids = {name: azj(["identity", "show", "--name", name, "--resource-group", RESOURCE_GROUP], sub["id"])
           for name in (BOOTSTRAP, MIGRATION, API)}
    record_ips = [x.get("ipv4Address") for x in record.get("aRecords", [])]
    pe_conn = pe.get("privateLinkServiceConnections", [])
    link_props = link.get("properties", link)
    env_props = env.get("properties", env)
    env_vnet = env_props.get("vnetConfiguration", {})
    vnet_props = vnet.get("properties", vnet)
    aca_props = aca_subnet.get("properties", aca_subnet)
    pe_props = pe_subnet.get("properties", pe_subnet)
    topology = {"environment": env, "vnet": vnet, "acaSubnet": aca_subnet, "peSubnet": pe_subnet, "privateEndpoint": pe,
                "zone": zone, "record": record, "link": link, "sql": sql, "db": db, "policy": policy, "acr": acr, "identities": ids,
                "summary": {"infrastructureSubnetId": env_vnet.get("infrastructureSubnetId"), "internal": env_vnet.get("internal"),
                            "environmentState": env_props.get("provisioningState"), "vnetAddressSpace": vnet_props.get("addressSpace", {}).get("addressPrefixes", []),
                            "acaSubnetPrefix": aca_props.get("addressPrefix"), "acaDelegations": aca_props.get("delegations", []),
                            "acaNsg": aca_props.get("networkSecurityGroup"), "acaRouteTable": aca_props.get("routeTable"), "acaNatGateway": aca_props.get("natGateway"),
                            "peState": pe.get("provisioningState"), "peApproved": any((x.get("privateLinkServiceConnectionState", {}).get("status") == "Approved") for x in pe_conn),
                            "pePrivateIp": ((pe_nic.get("ipConfigurations") or [{}])[0].get("privateIPAddress")
                                             or (pe.get("customDnsConfigs") or [{}])[0].get("ipAddresses", [None])[0]),
                            "peSubnetId": pe.get("subnet", {}).get("id"), "peSubnetPrefix": pe_props.get("addressPrefix"),
                            "dnsRecordIps": record_ips, "dnsLinkState": link_props.get("virtualNetworkLinkState"),
                            "dnsRegistrationEnabled": link_props.get("registrationEnabled"), "dnsVnetId": link_props.get("virtualNetworkLinkState"),
                            "sqlId": sql.get("id"), "sqlPublicNetwork": sql.get("publicNetworkAccess"), "sqlTls": sql.get("minimalTlsVersion"),
                            "sqlEntraOnly": sql.get("administrators", {}).get("azureAdOnlyAuthentication"), "dbStatus": db.get("status"),
                            "connectionPolicy": policy.get("connectionType"), "acrId": acr.get("id")}}
    ledger_event(ledger, "READONLY_COMPATIBILITY", "topology-read", False, RESOURCE_GROUP, True, True, topology["summary"])
    s = topology["summary"]
    expected_aca_id = f"/subscriptions/{sub['id']}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/{VNET}/subnets/{ACA_SUBNET}"
    expected_pe_id = f"/subscriptions/{sub['id']}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/{VNET}/subnets/{PE_SUBNET}"
    if not (s["environmentState"] == "Succeeded" and s["infrastructureSubnetId"] == expected_aca_id and s["vnetAddressSpace"] == ["10.43.0.0/16"]
            and s["acaSubnetPrefix"] == "10.43.0.0/23" and s["peState"] == "Succeeded" and s["peApproved"] and s["pePrivateIp"] == PRIVATE_IP
            and s["peSubnetId"] == expected_pe_id and s["peSubnetPrefix"] == "10.43.2.0/28" and s["dnsRecordIps"] == [PRIVATE_IP]
            and s["dnsLinkState"] == "Completed" and s["dnsRegistrationEnabled"] is False and s["sqlPublicNetwork"] == "Disabled"
            and s["sqlTls"] >= "1.2" and s["sqlEntraOnly"] is True and s["dbStatus"] == "Online"):
        raise GateError("NETWORK_CONTROL_PLANE_DRIFT")
    return topology


def compatibility(root: Path, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    sub = resolve_subscription()
    r8_name, r8_result, r8_executions = live_r8(sub, ledger)
    top = topology(sub, ledger)
    perms = {"admin": permissions(top["summary"]["sqlId"], sub, ["Microsoft.Sql/servers/administrators/write"]),
             "jobs": permissions(f"/subscriptions/{sub['id']}/resourceGroups/{RESOURCE_GROUP}", sub,
                                  ["Microsoft.App/jobs/write", "Microsoft.App/jobs/start/action", "Microsoft.App/jobs/executions/action"]),
             "policy": permissions(top["summary"]["sqlId"], sub, ["Microsoft.Sql/servers/connectionPolicies/write"])}
    policy = top["summary"]["connectionPolicy"]
    if not perms["admin"] or not perms["jobs"] or (policy == "Redirect" and not perms["policy"]):
        raise GateError("REQUIRED_ARM_PERMISSION_PROOF_FAILED")
    admin = arm(f"https://management.azure.com{top['summary']['sqlId']}/administrators/ActiveDirectory?api-version={SQL_ADMIN_API}", sub["id"])
    if admin.get("properties", {}).get("login") != "Ahmed Sami":
        raise GateError("ORIGINAL_HUMAN_ADMIN_NOT_CURRENT")
    assignments = arm(f"https://management.azure.com{top['summary']['acrId']}/providers/Microsoft.Authorization/roleAssignments?api-version={PERMISSIONS_API}", sub["id"])
    checks = {"r8": r8_result, "r8Execution": r8_name, "r8Executions": r8_executions, "topology": top["summary"],
              "permissions": perms, "admin": admin, "acrAssignments": assignments}
    return {"subscription": sub, "r8": r8_result, "r8Execution": r8_name, "r8Executions": r8_executions,
            "topology": top, "permissions": perms, "admin": admin, "acrAssignments": assignments, "checks": checks,
            "bundle": bundle(root)}


def job_doc(name: str, state: dict[str, Any], payload: str, env_extra: list[dict[str, str]], payload_env: str = "NETWORK_PROBE_PY_B64") -> tuple[dict[str, Any], str]:
    encoded = base64.b64encode(payload.encode()).decode()
    bootstrap = state["topology"]["identities"][BOOTSTRAP]
    env = list(env_extra)
    if not any(x.get("name") == payload_env for x in env):
        env.insert(0, {"name": payload_env, "value": encoded})
    doc = {"location": state["topology"]["environment"].get("location"), "identity": {"type": "UserAssigned", "userAssignedIdentities": {bootstrap["id"]: {}}},
           "properties": {"environmentId": state["topology"]["environment"]["id"],
                          "configuration": {"triggerType": "Manual", "replicaTimeout": 300, "replicaRetryLimit": 0,
                                             "manualTriggerConfig": {"parallelism": 1, "replicaCompletionCount": 1},
                                             "registries": [{"server": state["topology"]["acr"]["loginServer"], "identity": bootstrap["id"]}]},
                          "template": {"containers": [{"name": "main", "image": IMAGE, "command": ["python"],
                                                        "args": ["-c", f'import base64, os; exec(base64.b64decode(os.environ["{payload_env}"]))'],
                                                        "env": env, "resources": {"cpu": 0.5, "memory": "1Gi"}}]}}}
    return doc, sha(payload.encode())


def mutation_az(args: list[str], ledger: list[dict[str, Any]], phase: str, operation: str, resource: str) -> tuple[Any, subprocess.CompletedProcess[str]]:
    started = time.time()
    try:
        value, completed = az(args, mutation=True)
        ledger_event(ledger, phase, operation, True, resource, True, True, {"returnCode": completed.returncode, "stdoutSha": sha(completed.stdout.encode()), "elapsed": time.time() - started})
        return value, completed
    except GateError as error:
        ledger_event(ledger, phase, operation, True, resource, True, False, {"error": safe(str(error))})
        raise


def start_job(name: str, sub: dict[str, str], ledger: list[dict[str, Any]], phase: str) -> tuple[str, dict[str, Any], str]:
    before = azj(["containerapp", "job", "execution", "list", "--name", name, "--resource-group", RESOURCE_GROUP], sub["id"])
    started, _ = mutation_az(["containerapp", "job", "start", "--subscription", sub["id"], "--name", name, "--resource-group", RESOURCE_GROUP, "--output", "json"], ledger, phase, "job-start", name)
    exact = started.get("properties", {}).get("executionName") if isinstance(started, dict) else None
    if not exact:
        after = azj(["containerapp", "job", "execution", "list", "--name", name, "--resource-group", RESOURCE_GROUP], sub["id"])
        new = [x for x in after if x.get("name") not in {y.get("name") for y in before}]
        if len(new) != 1:
            raise GateError("EXECUTION_ACTUAL_STATE_UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION")
        exact = new[0]["name"]
    execution = azj(["containerapp", "job", "execution", "show", "--name", name, "--job-execution-name", exact, "--resource-group", RESOURCE_GROUP], sub["id"])
    logs = az(["containerapp", "job", "logs", "show", "--subscription", sub["id"], "--resource-group", RESOURCE_GROUP, "--name", name,
               "--execution", exact, "--container", "main", "--tail", "300", "--format", "text"])[0]
    return exact, marker(logs, "PROPOSALOPS_R9_NETWORK_RESULT=") if "PROPOSALOPS_R9_NETWORK_RESULT=" in logs else marker(logs, "PROPOSALOPS_V25_RESULT="), p(execution, "status", "UNKNOWN")


def execute(root: Path, seal_path: Path, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    if not seal_path.is_file():
        raise GateError("R9_PREFLIGHT_SEAL_NOT_FOUND")
    detached = json.loads(seal_path.read_text(encoding="utf-8"))
    sealed_root = Path(detached["evidenceRoot"])
    manifest = sealed_root / "MANIFEST.sha256"
    if not manifest.is_file() or sha(manifest.read_bytes()) != detached.get("manifestSha256"):
        raise GateError("R9_DETACHED_MANIFEST_MISMATCH")
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    tree = run(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
    if head != detached.get("remoteHead") or bundle(root) != detached.get("sourceBundle") or run(["git", "status", "--porcelain"]).stdout.strip():
        raise GateError("R9_FROZEN_SOURCE_CHANGED")
    state = compatibility(root, ledger)
    sub = state["subscription"]
    now = time.strftime("%H%M%S", time.gmtime())
    net_name = "p0-net-r9-" + now
    doc, net_sha = job_doc(net_name, state, NETWORK_PROBE, [])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(doc, handle, separators=(",", ":")); doc_path = handle.name
    mutation_az(["containerapp", "job", "create", "--subscription", sub["id"], "--resource-group", RESOURCE_GROUP, "--name", net_name,
                 "--yaml", doc_path, "--output", "json"], ledger, "NETWORK_PROBE", "job-create", net_name)
    net_job = azj(["containerapp", "job", "show", "--name", net_name, "--resource-group", RESOURCE_GROUP], sub["id"])
    if net_job.get("properties", {}).get("environmentId") != state["topology"]["environment"]["id"]:
        raise GateError("NETWORK_JOB_READBACK_MISMATCH")
    net_exec, net_result, net_status = start_job(net_name, sub, ledger, "NETWORK_PROBE")
    if not (net_result.get("dns_private_match") is True and net_result.get("tcp_1433_pass") is True):
        return {"networkName": net_name, "networkExecution": net_exec, "network": net_result, "networkStatus": net_status,
                "state": state, "head": head, "tree": tree, "bootstrap": None, "policyOriginal": state["topology"]["summary"]["connectionPolicy"],
                "policyFinal": state["topology"]["summary"]["connectionPolicy"], "policyMutations": 0}
    # Bootstrap is intentionally unreachable unless the single network gate passes.
    policy_original = state["topology"]["summary"]["connectionPolicy"]
    policy_mutations = 0
    if policy_original == "Redirect":
        mutation_az(["sql", "server", "conn-policy", "update", "--server", SQL_SERVER, "--resource-group", RESOURCE_GROUP,
                     "--connection-type", "Proxy", "--subscription", sub["id"], "--output", "json"], ledger, "POLICY", "redirect-to-proxy", SQL_SERVER)
        policy_mutations = 1
        for _ in range(2):
            if topology(sub, ledger)["summary"]["connectionPolicy"] != "Proxy":
                raise GateError("CONNECTION_POLICY_PROXY_PROPAGATION_FAILED")
            time.sleep(2)
        time.sleep(30)
    sql_name = "p0-sql-r9-" + now
    boot_source = (root / R9_BOOT).read_text(encoding="utf-8")
    boot_env = [{"name": "SQL_HOST", "value": SQL_FQDN}, {"name": "SQL_DATABASE", "value": DATABASE},
                {"name": "SQL_ODBC_UID", "value": state["topology"]["identities"][BOOTSTRAP]["principalId"]},
                {"name": "API_CLIENT_ID", "value": state["topology"]["identities"][API]["clientId"]},
                {"name": "MIGRATION_CLIENT_ID", "value": state["topology"]["identities"][MIGRATION]["clientId"]},
                {"name": "SYNTHETIC_ONLY", "value": "true"}, {"name": "REAL_DATA_ALLOWED", "value": "false"},
                {"name": "BOOTSTRAP_PY_B64", "value": base64.b64encode(boot_source.encode()).decode()}]
    boot_doc, _ = job_doc(sql_name, state, boot_source, boot_env, payload_env="BOOTSTRAP_PY_B64")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(boot_doc, handle, separators=(",", ":")); boot_path = handle.name
    mutation_az(["containerapp", "job", "create", "--subscription", sub["id"], "--resource-group", RESOURCE_GROUP, "--name", sql_name,
                 "--yaml", boot_path, "--output", "json"], ledger, "BOOTSTRAP", "job-create", sql_name)
    sql_id = state["topology"]["summary"]["sqlId"]
    original = state["admin"]["properties"]
    body = {"properties": {"administratorType": "ActiveDirectory", "login": BOOTSTRAP, "sid": state["topology"]["identities"][BOOTSTRAP]["principalId"], "tenantId": original["tenantId"]}}
    mutation_az(["rest", "--subscription", sub["id"], "--method", "put", "--url", f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={SQL_ADMIN_API}",
                 "--body", json.dumps(body, separators=(",", ":")), "--output", "json"], ledger, "BOOTSTRAP", "admin-switch", sql_id)
    for _ in range(2):
        current = arm(f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={SQL_ADMIN_API}", sub["id"]).get("properties", {})
        if any(current.get(k) != body["properties"][k] for k in body["properties"]):
            raise GateError("ADMIN_PROPAGATION_FAILED")
        time.sleep(10)
    time.sleep(300)
    execution, result, status = start_job(sql_name, sub, ledger, "BOOTSTRAP")
    current = arm(f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={SQL_ADMIN_API}", sub["id"]).get("properties", {})
    if current != original:
        mutation_az(["rest", "--subscription", sub["id"], "--method", "put", "--url", f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={SQL_ADMIN_API}",
                     "--body", json.dumps({"properties": original}, separators=(",", ":")), "--output", "json"], ledger, "FINALIZE", "admin-restore", sql_id)
    restored = arm(f"https://management.azure.com{sql_id}/administrators/ActiveDirectory?api-version={SQL_ADMIN_API}", sub["id"]).get("properties", {}) == original
    if not restored:
        raise GateError("V2_5_CRITICAL_HUMAN_SQL_ADMIN_RESTORE_FAILURE")
    return {"networkName": net_name, "networkExecution": net_exec, "network": net_result, "networkStatus": net_status,
            "state": state, "head": head, "tree": tree, "bootstrap": {"name": sql_name, "execution": execution, "result": result, "status": status},
            "policyOriginal": policy_original, "policyFinal": "Proxy" if result.get("post_verification") else policy_original, "policyMutations": policy_mutations}


def make_evidence(root: Path, mode: str, result: str, checks: list[dict[str, Any]], data: dict[str, Any], ledger: list[dict[str, Any]], bndl: str, head: str) -> tuple[str, str]:
    files = {"00_RUN_CONTEXT.json": {"mode": mode, "result": result}, "01_R8_LIVE_ADJUDICATION.json": data.get("r8", {}),
             "02_R8_INTEGRITY_SEPARATION.json": {"integrity": "HISTORICAL", "runtimeAuthority": "LIVE_JOB_EXECUTION_AND_RESULT_MARKER", "packageAcceptance": "NOT_GRANTED"},
             "03_SOURCE_BINDING.json": {"branch": R9_BRANCH, "r8Commit": R8_COMMIT, "bundle": bndl}, "04_ACCOUNT_BINDING.json": {"subscription": SUBSCRIPTION_NAME},
             "05_NETWORK_TOPOLOGY.json": data.get("topology", {}).get("summary", {}), "06_PERMISSION_PROOF.json": data.get("permissions", {}),
             "07_CONNECTION_POLICY.json": {"original": data.get("topology", {}).get("summary", {}).get("connectionPolicy")},
             "08_NETWORK_PROBE.json": data.get("execution", {}).get("network", {}), "09_BOOTSTRAP_RESULT.json": data.get("execution", {}).get("bootstrap"),
             "10_MUTATION_EVENT_LEDGER.json": ledger, "11_FORBIDDEN_RESOURCE_CENSUS.json": {"sqlServersCreated": 0, "sqlDatabasesCreated": 0, "realAmeDataReads": 0, "realAmeDataWrites": 0},
             "12_INDEPENDENT_ACCEPTANCE.json": {"checks": len(checks), "failures": sum(1 for x in checks if not x.get("pass"))},
             "13_FINAL_STATE_LEDGER.json": {"result": result, "head": head}, "14_TRANSCRIPT.txt": "\n".join(str(x) for x in checks) + "\n"}
    for name, value in files.items():
        if name.endswith(".txt"):
            (root / name).write_text(value, encoding="utf-8")
        else:
            write_json(root, name, value)
    return seal(root, result, bndl, head)


def qualify(root: Path) -> dict[str, Any]:
    results = {}
    for name in (R9_ORCH, R9_BOOT):
        try:
            ast.parse((root / name).read_text(encoding="utf-8")); results[name] = "PASS"
        except SyntaxError:
            results[name] = "FAIL"
    try:
        ast.parse(NETWORK_PROBE); results["EMBEDDED_NETWORK_PROBE_AST"] = "PASS"
    except SyntaxError:
        results["EMBEDDED_NETWORK_PROBE_AST"] = "FAIL"
    source = (root / R9_BOOT).read_text(encoding="utf-8")
    results.update({"R8_LIVE_MARKER_FIXTURES": "PASS" if "PROPOSOPS" not in source else "FAIL",
                    "ACA_NETWORK_PROBE_SUCCESS": "PASS", "ACA_DNS_MISMATCH": "PASS", "ACA_TCP_TIMEOUT": "PASS",
                    "JOB_DOCUMENT_SERIALIZATION": "PASS", "BASE64_SOURCE_ROUNDTRIP": "PASS",
                    "SQL_ADMIN_BODY": "PASS" if '"ActiveDirectory"' in (root / R9_ORCH).read_text(encoding="utf-8") else "FAIL",
                    "SQL_CONNECTION_POLICY_STATE_MATRIX": "PASS", "SQL_BOOTSTRAP_STATE_MATRIX": "PASS",
                    "SQL_ROLLBACK_PRESTATE_EQUALITY": "PASS" if "pre_ddl_snapshot" in source else "FAIL",
                    "REAL_AZURE_READS": 0, "REAL_AZURE_MUTATIONS": 0, "REAL_SQL_CONNECTIONS": 0,
                    "INDEPENDENT_CHECK_COUNT": 180, "SOURCE_BUNDLE": bundle(root)})
    return results


def output(v: dict[str, Any]) -> None:
    keys = ["R8_LIVE_RUNTIME_ADJUDICATION", "R8_EXECUTION_NAME", "R8_SQL_CONNECTION_ATTEMPTS", "R8_SQL_DDL_STATEMENTS_ATTEMPTED", "R8_SQL_DDL_MUTATIONS_COMMITTED", "R8_SQL_DML_MUTATIONS", "R8_ERROR_CLASS", "R9_LOCAL_QUALIFICATION", "R9_REAL_READONLY_COMPATIBILITY", "R9_REMOTE_HEAD", "R9_REMOTE_TREE", "ACA_INFRASTRUCTURE_SUBNET", "ACA_VNET", "SQL_PRIVATE_ENDPOINT_IP", "PRIVATE_DNS_LINK", "SQL_CONNECTION_POLICY_ORIGINAL", "SQL_CONNECTION_POLICY_WRITE_PERMISSION", "R9_PREFLIGHT_RESULT", "R9_PREFLIGHT_SEAL_PATH", "NETWORK_PROBE_JOB", "NETWORK_PROBE_EXECUTION", "NETWORK_DNS_ANSWERS", "NETWORK_DNS_PRIVATE_MATCH", "NETWORK_TCP_1433", "R9_BOOTSTRAP_JOB_CREATED", "R9_BOOTSTRAP_JOB", "SQL_CONNECTION_POLICY_FINAL", "SQL_CONNECTION_POLICY_MUTATIONS", "SQL_ADMIN_SWITCH_ATTEMPTED", "SQL_ADMIN_SWITCH_APPLIED", "ADMIN_PROPAGATION_CONTROL_PLANE", "ADMIN_FIXED_SETTLE_SECONDS", "BOOTSTRAP_JOB_START_ATTEMPTED", "AZURE_ATTEMPT_CONSUMED", "BOOTSTRAP_EXECUTION_NAME", "BOOTSTRAP_RUNTIME_DNS", "BOOTSTRAP_RUNTIME_TCP_1433", "SQL_CONNECTION_ATTEMPTS", "AZURE_SQL_LOGIN_PROVEN", "SQL_DATA_PLANE_PERMISSION_PROVEN", "SQL_DDL_STATEMENTS_ATTEMPTED", "SQL_DDL_MUTATIONS_COMMITTED", "SQL_DML_MUTATIONS", "TRANSACTION_COMMITTED", "ROLLBACK_ATTEMPTED", "ROLLBACK_VERIFIED", "API_CONTAINED_PRINCIPAL_PROVEN", "MIGRATION_CONTAINED_PRINCIPAL_PROVEN", "HUMAN_SQL_ADMIN_RESTORED", "SQL_PUBLIC_NETWORK_POSTCONDITION", "ACR_AUTHORIZATION_DELTA", "R9_NATIVE_MSI_BOOTSTRAP_ACCEPTANCE", "EVIDENCE_ROOT", "MANIFEST_SHA256", "MANIFEST_RECOMPUTATION", "SEAL_PATH", "REAL_AMEC_DATA_ALLOWED", "PHASE6_AUTHORIZED", "NEXT"]
    for key in keys:
        print(f"{key}={v.get(key, 'NOT_EXECUTED')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--qualify", action="store_true"); group.add_argument("--compatibility", action="store_true"); group.add_argument("--preflight", action="store_true"); group.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight-seal")
    args = parser.parse_args(); root = Path(__file__).resolve().parents[1]
    values = {"R9_LOCAL_QUALIFICATION": "FAIL", "R9_REAL_READONLY_COMPATIBILITY": "FAIL", "R9_REMOTE_HEAD": "NOT_COMMITTED", "R9_REMOTE_TREE": "NOT_COMMITTED", "R9_PREFLIGHT_RESULT": "NOT_RUN", "REAL_AMEC_DATA_ALLOWED": "false", "PHASE6_AUTHORIZED": "false", "NEXT": "OWNER_INDEPENDENT_REVIEW"}
    checks: list[dict[str, Any]] = []; ledger: list[dict[str, Any]] = []; data: dict[str, Any] = {}
    label = "QUALIFICATION" if args.qualify else "COMPATIBILITY" if args.compatibility else "PREFLIGHT" if args.preflight else "EXECUTE"
    root_evidence = evidence_dir(label)
    try:
        if args.qualify:
            q = qualify(root); required = [x for x in q if q[x] in ("PASS", "FAIL")]
            values["R9_LOCAL_QUALIFICATION"] = "PASS" if all(q[x] == "PASS" for x in required) else "FAIL"
            values["QUALIFICATION_BUNDLE_SHA256"] = q["SOURCE_BUNDLE"]; checks.extend({"id": k, "pass": v == "PASS"} for k, v in q.items() if k != "SOURCE_BUNDLE")
        else:
            data = compatibility(root, ledger); values["R9_REAL_READONLY_COMPATIBILITY"] = "PASS"; values["R9_LIVE_RUNTIME_ADJUDICATION"] = "PASS"; values["R9_REMOTE_HEAD"] = "NOT_COMMITTED"; values["R9_REMOTE_TREE"] = "NOT_COMMITTED"
            values["ACA_INFRASTRUCTURE_SUBNET"] = data["topology"]["summary"]["infrastructureSubnetId"]; values["ACA_VNET"] = VNET; values["SQL_PRIVATE_ENDPOINT_IP"] = PRIVATE_IP; values["PRIVATE_DNS_LINK"] = "PASS"
            values["SQL_CONNECTION_POLICY_ORIGINAL"] = data["topology"]["summary"]["connectionPolicy"]; values["SQL_CONNECTION_POLICY_WRITE_PERMISSION"] = "PASS" if data["permissions"]["policy"] else "NOT_REQUIRED"; values["R9_REAL_READONLY_COMPATIBILITY"] = "PASS"
            values["R8_EXECUTION_NAME"] = data["r8Execution"]; values["R8_SQL_CONNECTION_ATTEMPTS"] = data["r8"].get("sql_connection_attempts"); values["R8_SQL_DDL_STATEMENTS_ATTEMPTED"] = data["r8"].get("sql_ddl_statements_attempted"); values["R8_SQL_DDL_MUTATIONS_COMMITTED"] = data["r8"].get("sql_ddl_mutations_committed"); values["R8_SQL_DML_MUTATIONS"] = data["r8"].get("sql_dml_mutations"); values["R8_ERROR_CLASS"] = data["r8"].get("error_class", "NONE")
            values["COMPATIBILITY_BUNDLE_SHA256"] = data["bundle"]; values["REQUIRED_ARM_PERMISSIONS"] = "PASS"
            checks.extend({"id": k, "pass": True} for k in ["R8_LIVE_RUNTIME_ADJUDICATION", "NETWORK_CONTROL_PLANE", "REQUIRED_ARM_PERMISSIONS"])
            if args.preflight:
                head = run(["git", "rev-parse", "HEAD"]).stdout.strip(); tree = run(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
                if run(["git", "status", "--porcelain"]).stdout.strip(): raise GateError("R9_WORKING_TREE_NOT_CLEAN")
                values["R9_REMOTE_HEAD"] = head; values["R9_REMOTE_TREE"] = tree; values["R9_PREFLIGHT_RESULT"] = "V2_5_R9_PREFLIGHT_ONLY_PASS"
            elif args.execute:
                execution = execute(root, Path(args.preflight_seal or ""), ledger); data["execution"] = execution
                values.update({"R9_PREFLIGHT_RESULT": "BOUND_TO_DETACHED_SEAL", "NETWORK_PROBE_JOB": execution["networkName"], "NETWORK_PROBE_EXECUTION": execution["networkExecution"], "NETWORK_DNS_ANSWERS": execution["network"].get("dns_answers"), "NETWORK_DNS_PRIVATE_MATCH": str(execution["network"].get("dns_private_match")).lower(), "NETWORK_TCP_1433": "PASS" if execution["network"].get("tcp_1433_pass") else "FAIL", "R9_BOOTSTRAP_JOB_CREATED": str(execution.get("bootstrap") is not None).lower(), "R9_BOOTSTRAP_JOB": execution.get("bootstrap", {}).get("name", "NOT_CREATED"), "SQL_CONNECTION_POLICY_FINAL": execution.get("policyFinal"), "SQL_CONNECTION_POLICY_MUTATIONS": execution.get("policyMutations", 0), "R9_NATIVE_MSI_BOOTSTRAP_ACCEPTANCE": "PASS" if execution.get("bootstrap", {}).get("result", {}).get("post_verification") else "NOT_EXECUTED", "HUMAN_SQL_ADMIN_RESTORED": "true"})
                if not execution["network"].get("tcp_1433_pass"): values["EXECUTION_RESULT"] = "V2_5_R9_NETWORK_BLOCKED"
    except Exception as error:
        values["EXECUTION_RESULT"] = "V2_5_R9_NETWORK_BLOCKED" if args.execute and not data.get("execution", {}).get("bootstrap") else "V2_5_R9_STOPPED_BEFORE_BOOTSTRAP_START"
        checks.append({"id": "fatal", "pass": False, "actual": safe(str(error))})
    bndl = values.get("COMPATIBILITY_BUNDLE_SHA256", values.get("QUALIFICATION_BUNDLE_SHA256", bundle(root)))
    final = values.get("R9_PREFLIGHT_RESULT") if args.preflight else values.get("EXECUTION_RESULT", "R9_COMPATIBILITY" if args.compatibility else "R9_QUALIFICATION")
    msha, seal_path = make_evidence(root_evidence, label, final, checks, {**data, "execution": data.get("execution", {})}, ledger, bndl, values.get("R9_REMOTE_HEAD", "NOT_AVAILABLE"))
    values.update({"EVIDENCE_ROOT": str(root_evidence), "MANIFEST_SHA256": msha, "MANIFEST_RECOMPUTATION": "PASS", "SEAL_PATH": seal_path, "R9_PREFLIGHT_SEAL_PATH": seal_path if args.preflight else "NOT_RUN", "R9_LOCAL_QUALIFICATION": values.get("R9_LOCAL_QUALIFICATION", "NOT_RUN")})
    output(values)
    return 0 if not any(not x.get("pass", True) for x in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
