#!/usr/bin/env python3
"""Bootstrap the isolated Azure SQL principals for canonical synthetic preprod.

This is an operator-side, preprod-only action. It uses the approved Entra
administrator's Azure CLI token and never accepts an application password.
The runtime identities receive DML roles; only the migration identity also
receives DDL authority. The database remains private-only after this action.
"""

from __future__ import annotations

import argparse
import json
import re
import struct

import pyodbc
from azure.identity import AzureCliCredential


SQL_COPT_SS_ACCESS_TOKEN = 1256
SQL_SCOPE = "https://database.windows.net/.default"
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def _identifier(value: str, label: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _connection(server: str, database: str):
    token = AzureCliCredential().get_token(SQL_SCOPE).token
    token_bytes = token.encode("utf-16-le")
    packed_token = struct.pack("<I", len(token_bytes)) + token_bytes
    connection_string = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{server},1433;"
        f"Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(
        connection_string,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: packed_token},
        autocommit=False,
    )


def _principal(cursor, name: str, role_names: tuple[str, ...]) -> None:
    quoted = f"[{name}]"
    cursor.execute(
        "IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = ?) "
        "BEGIN CREATE USER " + quoted + " FROM EXTERNAL PROVIDER; END",
        name,
    )
    for role in role_names:
        cursor.execute(
            "IF NOT EXISTS ("
            "SELECT 1 FROM sys.database_role_members drm "
            "JOIN sys.database_principals rp ON rp.principal_id = drm.role_principal_id "
            "JOIN sys.database_principals dp ON dp.principal_id = drm.member_principal_id "
            "WHERE rp.name = ? AND dp.name = ?) "
            f"ALTER ROLE [{role}] ADD MEMBER {quoted};",
            role,
            name,
        )


def bootstrap(
    *,
    environment: str,
    server: str,
    database: str,
    api_name: str,
    worker_name: str,
    migration_name: str,
) -> list[dict[str, str]]:
    if environment.upper() != "AZURE-PREPROD":
        raise ValueError("canonical SQL bootstrap is restricted to AZURE-PREPROD")
    server = _identifier(server, "server")
    database = _identifier(database, "database")
    api_name = _identifier(api_name, "api identity name")
    worker_name = _identifier(worker_name, "worker identity name")
    migration_name = _identifier(migration_name, "migration identity name")
    if len({api_name, worker_name, migration_name}) != 3:
        raise ValueError("api, worker, and migration identities must differ")

    principals = (
        (api_name, ("db_datareader", "db_datawriter")),
        (worker_name, ("db_datareader", "db_datawriter")),
        (migration_name, ("db_datareader", "db_datawriter", "db_ddladmin")),
    )
    with _connection(server, database) as connection:
        cursor = connection.cursor()
        for name, roles in principals:
            _principal(cursor, name, roles)
        connection.commit()
        cursor.execute(
            "SELECT dp.name AS principal_name, rp.name AS role_name "
            "FROM sys.database_role_members drm "
            "JOIN sys.database_principals rp ON rp.principal_id = drm.role_principal_id "
            "JOIN sys.database_principals dp ON dp.principal_id = drm.member_principal_id "
            "WHERE dp.name IN (?, ?, ?) ORDER BY dp.name, rp.name",
            api_name,
            worker_name,
            migration_name,
        )
        return [
            {"principal_name": row.principal_name, "role_name": row.role_name}
            for row in cursor.fetchall()
        ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--api-name", required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--migration-name", required=True)
    args = parser.parse_args()
    print(json.dumps(bootstrap(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
