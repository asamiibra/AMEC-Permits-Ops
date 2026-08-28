"""R8 native-MSI SQL bootstrap payload.

This file is intentionally self-contained because it is transported to the
single, manually started ACA Job as BOOTSTRAP_PY_B64.
"""

import json
import os

import pyodbc


API_USER = "proposalops_api_uami"
MIGRATION_USER = "proposalops_migration_uami"
BOOTSTRAP_USER = "proposalops_bootstrap_uami"
API_ROLES = {"db_datareader", "db_datawriter"}
MIGRATION_ROLES = {"db_datareader", "db_datawriter", "db_ddladmin"}


def _guid(value):
    return str(value).lower()


def _row_dict(row):
    return {
        "name": row[0],
        "type": row[1],
        "type_desc": row[2],
        "sid": _guid(row[3]) if row[3] is not None else None,
    }


def _read_state(cursor, api_id, migration_id):
    cursor.execute(
        """
        SELECT name, type, type_desc,
               CONVERT(varchar(36), CONVERT(uniqueidentifier, sid))
        FROM sys.database_principals
        WHERE name IN (?, ?, ?)
        """,
        BOOTSTRAP_USER,
        API_USER,
        MIGRATION_USER,
    )
    principals = {_row_dict(row)["name"]: _row_dict(row) for row in cursor.fetchall()}

    cursor.execute(
        """
        SELECT USER_NAME(rm.member_principal_id), r.name
        FROM sys.database_role_members AS rm
        JOIN sys.database_principals AS r
          ON r.principal_id = rm.role_principal_id
        WHERE USER_NAME(rm.member_principal_id) IN (?, ?)
        """,
        API_USER,
        MIGRATION_USER,
    )
    roles = {API_USER: set(), MIGRATION_USER: set()}
    for member, role in cursor.fetchall():
        roles.setdefault(member, set()).add(role)

    cursor.execute(
        """
        SELECT USER_NAME(grantee_principal_id), permission_name, state_desc
        FROM sys.database_permissions
        WHERE grantee_principal_id IN (USER_ID(?), USER_ID(?))
        """,
        API_USER,
        MIGRATION_USER,
    )
    permissions = {API_USER: [], MIGRATION_USER: []}
    for member, permission, state in cursor.fetchall():
        permissions.setdefault(member, []).append(
            {"permission_name": permission, "state_desc": state}
        )

    expected = {API_USER: _guid(api_id), MIGRATION_USER: _guid(migration_id)}
    invalid = []
    for user in (API_USER, MIGRATION_USER):
        principal = principals.get(user)
        if principal is not None and (
            principal["type"] != "E" or principal["sid"] != expected[user]
        ):
            invalid.append(f"{user}:wrong_type_or_sid")
    if BOOTSTRAP_USER in principals:
        invalid.append("bootstrap_contained_principal_present")

    api_permissions = permissions.get(API_USER, [])
    if api_permissions:
        invalid.append("api_unexpected_explicit_permission")
    migration_permissions = permissions.get(MIGRATION_USER, [])
    for permission in migration_permissions:
        if permission != {"permission_name": "VIEW DEFINITION", "state_desc": "GRANT"}:
            invalid.append("migration_unexpected_explicit_permission")
    if len(migration_permissions) > 1:
        invalid.append("migration_duplicate_explicit_permission")

    api_roles = roles.get(API_USER, set())
    migration_roles = roles.get(MIGRATION_USER, set())
    if not api_roles.issubset(API_ROLES):
        invalid.append("api_unexpected_role")
    if not migration_roles.issubset(MIGRATION_ROLES):
        invalid.append("migration_unexpected_role")

    return {
        "principals": principals,
        "roles": {API_USER: sorted(api_roles), MIGRATION_USER: sorted(migration_roles)},
        "permissions": permissions,
        "invalid": invalid,
    }


def _exact(state, api_id, migration_id):
    principals = state["principals"]
    return (
        BOOTSTRAP_USER not in principals
        and principals.get(API_USER, {}).get("type") == "E"
        and principals.get(API_USER, {}).get("sid") == _guid(api_id)
        and principals.get(MIGRATION_USER, {}).get("type") == "E"
        and principals.get(MIGRATION_USER, {}).get("sid") == _guid(migration_id)
        and set(state["roles"].get(API_USER, [])) == API_ROLES
        and set(state["roles"].get(MIGRATION_USER, [])) == MIGRATION_ROLES
        and state["permissions"].get(API_USER, []) == []
        and state["permissions"].get(MIGRATION_USER, [])
        == [{"permission_name": "VIEW DEFINITION", "state_desc": "GRANT"}]
    )


def _sid_literal(cursor, client_id):
    # This is SQL Server's documented GUID conversion path.  It deliberately
    # does not strip dashes and reinterpret the GUID in Python.
    cursor.execute(
        "SELECT CONVERT(varchar(34), CONVERT(varbinary(16), CAST(? AS uniqueidentifier)), 1)",
        client_id,
    )
    value = cursor.fetchone()[0]
    if not isinstance(value, str) or not value.lower().startswith("0x"):
        raise RuntimeError("SQL_SID_CONVERSION_CONTRACT_FAILED")
    return value


def bootstrap():
    result = {
        "sql_connection_attempts": 0,
        "sql_connection_succeeded": False,
        "sql_login": "FAIL",
        "sql_target_db": "FAIL",
        "sql_required_permission": "FAIL",
        "preinspection_pass": False,
        "sql_ddl_statements_attempted": 0,
        "sql_ddl_mutations_committed": 0,
        "sql_mutation_state": "NOT_EXECUTED",
        "sql_dml_mutations": 0,
        "api_user_state": "FAIL",
        "migration_user_state": "FAIL",
        "bootstrap_principal_absent": False,
        "post_verification": False,
        "transaction_committed": False,
        "rollback_attempted": False,
        "rollback_verified": False,
        "error_class": None,
        "error_message": None,
    }
    connection = None
    cursor = None
    transaction_started = False
    try:
        host = os.environ["SQL_HOST"]
        database = os.environ["SQL_DATABASE"]
        uid = os.environ["SQL_ODBC_UID"]
        connection_string = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={host};DATABASE={database};"
            "Authentication=ActiveDirectoryMsi;"
            f"UID={uid};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
        )
        result["sql_connection_attempts"] = 1
        connection = pyodbc.connect(connection_string)
        result["sql_connection_succeeded"] = True
        cursor = connection.cursor()

        cursor.execute("SELECT 1")
        result["sql_login"] = "PASS" if cursor.fetchone()[0] == 1 else "FAIL"
        cursor.execute("SELECT DB_NAME()")
        result["sql_target_db"] = "PASS" if cursor.fetchone()[0] == database else "FAIL"
        cursor.execute(
            "SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER ANY USER')"
        )
        result["sql_required_permission"] = (
            "PASS" if cursor.fetchone()[0] == 1 else "FAIL"
        )
        if not all(
            result[key] == "PASS"
            for key in ("sql_login", "sql_target_db", "sql_required_permission")
        ):
            raise RuntimeError("SQL_DATA_PLANE_GATE_FAILED")

        api_id = os.environ["API_CLIENT_ID"]
        migration_id = os.environ["MIGRATION_CLIENT_ID"]
        state = _read_state(cursor, api_id, migration_id)
        if state["invalid"]:
            raise RuntimeError("PREINSPECTION_FORBIDDEN_STATE:" + ",".join(state["invalid"]))
        result["preinspection_pass"] = True

        statements = []
        if API_USER not in state["principals"]:
            statements.append(
                f"CREATE USER [{API_USER}] WITH SID = {_sid_literal(cursor, api_id)}, TYPE = E"
            )
        if MIGRATION_USER not in state["principals"]:
            statements.append(
                f"CREATE USER [{MIGRATION_USER}] WITH SID = {_sid_literal(cursor, migration_id)}, TYPE = E"
            )
        for role in sorted(API_ROLES - set(state["roles"].get(API_USER, []))):
            statements.append(f"ALTER ROLE [{role}] ADD MEMBER [{API_USER}]")
        for role in sorted(MIGRATION_ROLES - set(state["roles"].get(MIGRATION_USER, []))):
            statements.append(f"ALTER ROLE [{role}] ADD MEMBER [{MIGRATION_USER}]")
        if state["permissions"].get(MIGRATION_USER, []) != [
            {"permission_name": "VIEW DEFINITION", "state_desc": "GRANT"}
        ]:
            statements.append(f"GRANT VIEW DEFINITION TO [{MIGRATION_USER}]")

        transaction_started = True
        for statement in statements:
            result["sql_ddl_statements_attempted"] += 1
            cursor.execute(statement)

        in_transaction = _read_state(cursor, api_id, migration_id)
        if in_transaction["invalid"] or not _exact(in_transaction, api_id, migration_id):
            raise RuntimeError("POSTVERIFY_BEFORE_COMMIT_FAILED")
        connection.commit()
        transaction_started = False
        result["transaction_committed"] = True
        result["sql_ddl_mutations_committed"] = len(statements)
        result["sql_mutation_state"] = "COMMITTED"

        after = _read_state(cursor, api_id, migration_id)
        result["bootstrap_principal_absent"] = BOOTSTRAP_USER not in after["principals"]
        result["api_user_state"] = (
            "PASS"
            if after["principals"].get(API_USER, {}).get("type") == "E"
            and after["principals"].get(API_USER, {}).get("sid") == _guid(api_id)
            and set(after["roles"].get(API_USER, [])) == API_ROLES
            and not after["permissions"].get(API_USER, [])
            else "FAIL"
        )
        result["migration_user_state"] = (
            "PASS"
            if after["principals"].get(MIGRATION_USER, {}).get("type") == "E"
            and after["principals"].get(MIGRATION_USER, {}).get("sid") == _guid(migration_id)
            and set(after["roles"].get(MIGRATION_USER, [])) == MIGRATION_ROLES
            and after["permissions"].get(MIGRATION_USER, [])
            == [{"permission_name": "VIEW DEFINITION", "state_desc": "GRANT"}]
            else "FAIL"
        )
        result["post_verification"] = (
            result["api_user_state"] == "PASS"
            and result["migration_user_state"] == "PASS"
            and result["bootstrap_principal_absent"]
        )
        if not result["post_verification"]:
            result["sql_mutation_state"] = "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
    except Exception as error:
        result["error_class"] = type(error).__name__
        result["error_message"] = str(error)[:300]
        if connection is not None and transaction_started:
            result["rollback_attempted"] = True
            try:
                connection.rollback()
                rolled_back = _read_state(cursor, os.environ["API_CLIENT_ID"], os.environ["MIGRATION_CLIENT_ID"])
                result["rollback_verified"] = _exact(
                    rolled_back, os.environ["API_CLIENT_ID"], os.environ["MIGRATION_CLIENT_ID"]
                ) or result["sql_ddl_statements_attempted"] == 0
                result["sql_mutation_state"] = (
                    "ROLLED_BACK_VERIFIED"
                    if result["rollback_verified"]
                    else "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
                )
            except Exception:
                result["rollback_verified"] = False
                result["sql_mutation_state"] = "UNKNOWN_REQUIRES_READ_ONLY_ADJUDICATION"
    finally:
        if connection is not None:
            connection.close()
        print("PROPOSALOPS_V25_RESULT=" + json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    bootstrap()
