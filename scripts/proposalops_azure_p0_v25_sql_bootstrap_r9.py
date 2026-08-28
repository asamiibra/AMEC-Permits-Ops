"""R9 bootstrap payload: one runtime network gate, then one MSI ODBC login."""

import json
import os
import socket

import pyodbc


API_USER = "proposalops_api_uami"
MIGRATION_USER = "proposalops_migration_uami"
BOOTSTRAP_USER = "proposalops_bootstrap_uami"
API_ROLES = {"db_datareader", "db_datawriter"}
MIGRATION_ROLES = {"db_datareader", "db_datawriter", "db_ddladmin"}
SQL_FQDN = "sql-proposalops-prod-uae-2bea2887.database.windows.net"
EXPECTED_PRIVATE_IP = "10.43.2.4"


def network_gate():
    result = {"dns_attempts": 1, "dns_answers": [], "expected_private_ip": EXPECTED_PRIVATE_IP,
              "dns_private_match": False, "tcp_1433_attempts": 1, "tcp_1433_pass": False,
              "tcp_peer_ip": None, "local_source_ip": None, "error_class": None, "error_message": None}
    try:
        answers = socket.getaddrinfo(SQL_FQDN, 1433, type=socket.SOCK_STREAM)
        result["dns_answers"] = sorted({item[4][0] for item in answers})
        result["dns_private_match"] = EXPECTED_PRIVATE_IP in result["dns_answers"]
        if not result["dns_private_match"] or any(
            not (value.startswith("10.") or value.startswith("192.168.") or value.startswith("172."))
            for value in result["dns_answers"]
        ):
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
    return result


def _guid(value):
    return str(value).lower()


def _state(cursor, api_id, migration_id):
    cursor.execute("""
        SELECT name, type, type_desc,
               CONVERT(varchar(36), CONVERT(uniqueidentifier, sid))
        FROM sys.database_principals
        WHERE name IN (?, ?, ?)
    """, BOOTSTRAP_USER, API_USER, MIGRATION_USER)
    principals = {row[0]: {"name": row[0], "type": row[1], "type_desc": row[2], "sid": _guid(row[3]) if row[3] else None}
                  for row in cursor.fetchall()}
    cursor.execute("""
        SELECT USER_NAME(rm.member_principal_id), r.name
        FROM sys.database_role_members rm
        JOIN sys.database_principals r ON r.principal_id = rm.role_principal_id
        WHERE USER_NAME(rm.member_principal_id) IN (?, ?)
    """, API_USER, MIGRATION_USER)
    roles = {API_USER: set(), MIGRATION_USER: set()}
    for member, role in cursor.fetchall():
        roles.setdefault(member, set()).add(role)
    cursor.execute("""
        SELECT USER_NAME(grantee_principal_id), permission_name, state_desc
        FROM sys.database_permissions
        WHERE grantee_principal_id IN (USER_ID(?), USER_ID(?))
    """, API_USER, MIGRATION_USER)
    permissions = {API_USER: [], MIGRATION_USER: []}
    for member, permission, state in cursor.fetchall():
        permissions.setdefault(member, []).append((permission, state))
    return {"principals": principals,
            "roles": {key: sorted(value) for key, value in roles.items()},
            "permissions": {key: sorted(value) for key, value in permissions.items()}}


def _validate_prestate(state, api_id, migration_id):
    errors = []
    principals = state["principals"]
    for user, client in ((API_USER, api_id), (MIGRATION_USER, migration_id)):
        if user in principals and (principals[user]["type"] != "E" or principals[user]["sid"] != _guid(client)):
            errors.append(user + "_wrong_type_or_sid")
    if BOOTSTRAP_USER in principals:
        errors.append("bootstrap_principal_present")
    if not set(state["roles"].get(API_USER, [])) <= API_ROLES:
        errors.append("api_forbidden_role")
    if not set(state["roles"].get(MIGRATION_USER, [])) <= MIGRATION_ROLES:
        errors.append("migration_forbidden_role")
    if state["permissions"].get(API_USER):
        errors.append("api_unexpected_permission")
    for permission in state["permissions"].get(MIGRATION_USER, []):
        if permission != ("VIEW DEFINITION", "GRANT"):
            errors.append("migration_unexpected_permission")
    if len(state["permissions"].get(MIGRATION_USER, [])) > 1:
        errors.append("migration_duplicate_permission")
    return errors


def _exact(state, api_id, migration_id):
    return not _validate_prestate(state, api_id, migration_id) and API_USER in state["principals"] \
        and MIGRATION_USER in state["principals"] \
        and set(state["roles"].get(API_USER, [])) == API_ROLES \
        and set(state["roles"].get(MIGRATION_USER, [])) == MIGRATION_ROLES \
        and state["permissions"].get(API_USER, []) == [] \
        and state["permissions"].get(MIGRATION_USER, []) == [("VIEW DEFINITION", "GRANT")]


def _sid_literal(cursor, client_id):
    cursor.execute("SELECT CONVERT(varchar(34), CONVERT(varbinary(16), CAST(? AS uniqueidentifier)), 1)", client_id)
    literal = cursor.fetchone()[0]
    if not isinstance(literal, str) or not literal.lower().startswith("0x"):
        raise RuntimeError("SQL_SID_CONVERSION_CONTRACT_FAILED")
    return literal


def bootstrap():
    result = {"runtime_dns_answers": [], "runtime_dns_private_match": False, "runtime_tcp_1433_pass": False,
              "sql_connection_attempts": 0, "sql_connection_succeeded": False, "sql_login": "FAIL",
              "sql_target_db": "FAIL", "sql_required_permission": "FAIL", "preinspection_pass": False,
              "sql_ddl_statements_attempted": 0, "sql_ddl_mutations_committed": 0, "sql_dml_mutations": 0,
              "transaction_committed": False, "rollback_attempted": False, "rollback_verified": False,
              "sql_mutation_state": "NOT_EXECUTED", "api_user_state": "FAIL", "migration_user_state": "FAIL",
              "bootstrap_principal_absent": False, "post_verification": False, "error_class": None,
              "error_message": None}
    connection = None
    cursor = None
    transaction_started = False
    try:
        net = network_gate()
        result["runtime_dns_answers"] = net["dns_answers"]
        result["runtime_dns_private_match"] = net["dns_private_match"]
        result["runtime_tcp_1433_pass"] = net["tcp_1433_pass"]
        if not (net["dns_private_match"] and net["tcp_1433_pass"]):
            result["error_class"] = net["error_class"] or "NetworkGateError"
            result["error_message"] = net["error_message"] or "R9_RUNTIME_NETWORK_GATE_FAILED"
            return

        database = os.environ["SQL_DATABASE"]
        connection_string = ("DRIVER={ODBC Driver 18 for SQL Server};"
                              f"SERVER=tcp:{SQL_FQDN},1433;DATABASE={database};"
                              "Authentication=ActiveDirectoryMsi;"
                              f"UID={os.environ['SQL_ODBC_UID']};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;")
        result["sql_connection_attempts"] = 1
        connection = pyodbc.connect(connection_string)
        result["sql_connection_succeeded"] = True
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result["sql_login"] = "PASS" if cursor.fetchone()[0] == 1 else "FAIL"
        cursor.execute("SELECT DB_NAME()")
        result["sql_target_db"] = "PASS" if cursor.fetchone()[0] == database else "FAIL"
        cursor.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER ANY USER')")
        result["sql_required_permission"] = "PASS" if cursor.fetchone()[0] == 1 else "FAIL"
        if not all(result[x] == "PASS" for x in ("sql_login", "sql_target_db", "sql_required_permission")):
            raise RuntimeError("SQL_PRECHECK_FAILED")

        api_id = os.environ["API_CLIENT_ID"]
        migration_id = os.environ["MIGRATION_CLIENT_ID"]
        before = _state(cursor, api_id, migration_id)
        result["preinspection_pass"] = not _validate_prestate(before, api_id, migration_id)
        if not result["preinspection_pass"]:
            raise RuntimeError("PREINSPECTION_FORBIDDEN_STATE")
        pre_ddl_snapshot = json.dumps(before, sort_keys=True)
        statements = []
        if API_USER not in before["principals"]:
            statements.append(f"CREATE USER [{API_USER}] WITH SID = {_sid_literal(cursor, api_id)}, TYPE = E")
        if MIGRATION_USER not in before["principals"]:
            statements.append(f"CREATE USER [{MIGRATION_USER}] WITH SID = {_sid_literal(cursor, migration_id)}, TYPE = E")
        for role in sorted(API_ROLES - set(before["roles"].get(API_USER, []))):
            statements.append(f"ALTER ROLE [{role}] ADD MEMBER [{API_USER}]")
        for role in sorted(MIGRATION_ROLES - set(before["roles"].get(MIGRATION_USER, []))):
            statements.append(f"ALTER ROLE [{role}] ADD MEMBER [{MIGRATION_USER}]")
        if before["permissions"].get(MIGRATION_USER, []) == []:
            statements.append(f"GRANT VIEW DEFINITION TO [{MIGRATION_USER}]")
        transaction_started = True
        for statement in statements:
            result["sql_ddl_statements_attempted"] += 1
            cursor.execute(statement)
        after_ddl = _state(cursor, api_id, migration_id)
        if not _exact(after_ddl, api_id, migration_id):
            raise RuntimeError("POSTVERIFY_BEFORE_COMMIT_FAILED")
        connection.commit()
        transaction_started = False
        result["transaction_committed"] = True
        result["sql_ddl_mutations_committed"] = len(statements)
        result["sql_mutation_state"] = "COMMITTED"
        after_commit = _state(cursor, api_id, migration_id)
        result["bootstrap_principal_absent"] = BOOTSTRAP_USER not in after_commit["principals"]
        result["api_user_state"] = "PASS" if set(after_commit["roles"].get(API_USER, [])) == API_ROLES and API_USER in after_commit["principals"] else "FAIL"
        result["migration_user_state"] = "PASS" if _exact(after_commit, api_id, migration_id) else "FAIL"
        result["post_verification"] = result["api_user_state"] == "PASS" and result["migration_user_state"] == "PASS" and result["bootstrap_principal_absent"]
        if not result["post_verification"]:
            result["sql_mutation_state"] = "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
    except Exception as error:
        result["error_class"] = type(error).__name__
        result["error_message"] = str(error)[:300]
        if connection is not None and transaction_started:
            result["rollback_attempted"] = True
            try:
                connection.rollback()
                rolled = _state(cursor, os.environ["API_CLIENT_ID"], os.environ["MIGRATION_CLIENT_ID"])
                result["rollback_verified"] = json.dumps(rolled, sort_keys=True) == pre_ddl_snapshot
                result["sql_mutation_state"] = "ROLLED_BACK_VERIFIED" if result["rollback_verified"] else "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
            except Exception:
                result["sql_mutation_state"] = "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
    finally:
        if connection is not None:
            connection.close()
        print("PROPOSALOPS_V25_RESULT=" + json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    bootstrap()
