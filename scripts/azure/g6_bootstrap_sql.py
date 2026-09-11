#!/usr/bin/env python3
"""Bootstrap only the isolated G6 SQL principals and synthetic probe table.

This is an operator-side bootstrap. It uses the approved Entra administrator
through Azure CLI credentials, never an application password or an ACA job
identity. It must only be pointed at the qualification database.
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
            f"ALTER ROLE [{role}] ADD MEMBER {quoted};"
        )


def bootstrap(*, server: str, database: str, runtime_name: str, migration_name: str) -> list[dict[str, str]]:
    server = _identifier(server, "server")
    database = _identifier(database, "database")
    runtime_name = _identifier(runtime_name, "runtime identity name")
    migration_name = _identifier(migration_name, "migration identity name")
    if runtime_name == migration_name:
        raise ValueError("runtime and migration identities must differ")

    with _connection(server, database) as connection:
        cursor = connection.cursor()
        _principal(cursor, runtime_name, ("db_datareader", "db_datawriter"))
        _principal(cursor, migration_name, ("db_datareader", "db_datawriter", "db_ddladmin"))
        cursor.execute(
            "IF OBJECT_ID(N'dbo.g6_qualification_probe', N'U') IS NULL "
            "CREATE TABLE dbo.g6_qualification_probe "
            "(probe_id nvarchar(100) NOT NULL PRIMARY KEY, payload nvarchar(200) NOT NULL);"
        )
        connection.commit()
        cursor.execute(
            "SELECT dp.name AS principal_name, rp.name AS role_name "
            "FROM sys.database_role_members drm "
            "JOIN sys.database_principals rp ON rp.principal_id = drm.role_principal_id "
            "JOIN sys.database_principals dp ON dp.principal_id = drm.member_principal_id "
            "WHERE dp.name IN (?, ?) ORDER BY dp.name, rp.name",
            runtime_name,
            migration_name,
        )
        rows = [
            {"principal_name": row.principal_name, "role_name": row.role_name}
            for row in cursor.fetchall()
        ]
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--runtime-name", required=True)
    parser.add_argument("--migration-name", required=True)
    args = parser.parse_args()
    print(json.dumps(bootstrap(**vars(args)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

