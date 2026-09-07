from __future__ import annotations

import argparse
import json
import os
import platform
import pyodbc
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from sqlalchemy import Boolean, bindparam, create_engine, inspect, literal, select, true

REQUIRED_GATES = [
    "source_event_idempotency", "replay_stable_across_time", "evidence_intake_idempotency",
    "classification_envelope_immutability", "review_locking_concurrency", "correction_append_only",
    "reviewed_assertion_promotion", "assertion_supersession", "projection_idempotency",
    "duplicate_side_effect_protection", "rollback", "freeze_metadata", "hard_gate_short_circuit",
    "out_of_scope_no_projection", "secret_exclude_no_projection", "protected_action_denial",
]


def _junit(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    statuses: dict[str, str] = {}
    for case in cases:
        name = case.attrib.get("name", "")
        status = "PASS"
        if case.find("failure") is not None or case.find("error") is not None:
            status = "FAIL"
        elif case.find("skipped") is not None:
            status = "NOT_EXECUTED"
        statuses[name] = status
    return statuses


def _probe_boolean_predicate(database_url: str) -> bool:
    """Execute a Boolean-typed SQLAlchemy predicate on the live SQL Server."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            statement = select(literal(1)).where(
                bindparam("phase5_bool", type_=Boolean) == true()
            )
            return connection.execute(statement, {"phase5_bool": True}).scalar_one() == 1
    finally:
        engine.dispose()


def _probe_reflection(database_url: str) -> bool:
    """Reflect only supported MSSQL metadata from a migrated real table."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables = {name.lower() for name in inspector.get_table_names()}
            columns = {
                row["name"].lower()
                for row in inspector.get_columns("phase4_review_decisions")
            }
            return "phase4_review_decisions" in tables and {"id", "idempotency_key"} <= columns
    finally:
        engine.dispose()


def _probe_status(statuses: dict[str, str], test_name: str) -> str:
    matches = [status for name, status in statuses.items() if name == test_name or name.endswith(test_name)]
    return matches[0] if len(matches) == 1 else "NOT_EXECUTED"


def run(junitxml: Path, bootstrap_result: Path, output: Path) -> dict[str, Any]:
    statuses = _junit(junitxml)
    bootstrap = json.loads(bootstrap_result.read_text(encoding="utf-8"))
    gates: dict[str, str] = {}
    for gate in REQUIRED_GATES:
        candidates = [name for name in statuses if gate in name]
        gates[gate] = statuses[candidates[0]] if candidates else "NOT_EXECUTED"
    failed = sum(value == "FAIL" for value in gates.values())
    skipped = sum(value == "NOT_EXECUTED" for value in gates.values())
    boolean_probe_status = _probe_status(statuses, "test_native_sql_server_boolean_predicates_portable")
    reflection_probe_status = _probe_status(statuses, "test_native_sql_server_reflection_compatibility")
    portability_statuses = (boolean_probe_status, reflection_probe_status)
    portability_probe_pass_count = portability_statuses.count("PASS")
    portability_probe_fail_count = portability_statuses.count("FAIL")
    portability_probe_not_executed_count = portability_statuses.count("NOT_EXECUTED")
    engine_ok = bootstrap.get("engine") == "MICROSOFT_SQL_SERVER_2022_X64" and bootstrap.get("sqlserver_major") == 16
    native_x64 = platform.machine().lower() in {"x86_64", "amd64"}
    pyodbc_driver = "ODBC Driver 18 for SQL Server" in pyodbc.drivers()
    result = {
        "version": 2, "result": "PASS" if not failed and not skipped and engine_ok and bootstrap.get("result") == "PASS" and native_x64 and pyodbc_driver and portability_probe_pass_count == 2 else "FAIL",
        "engine": bootstrap.get("engine"), "sqlserver_major": bootstrap.get("sqlserver_major"),
        "migration_head": bootstrap.get("migration_head"), "migration_pass": bootstrap.get("migration_pass"),
        "gate_count": len(REQUIRED_GATES), "failed_count": failed, "skipped_count": skipped,
        "gates": gates, "gate_test_names": {gate: next((name for name in statuses if gate in name), None) for gate in REQUIRED_GATES},
        "database_schema_delta": bootstrap.get("database_schema_delta"), "junit_testcase_count": len(statuses),
        "native_x64": native_x64,
        "pyodbc_driver": pyodbc_driver,
        "portability_probe_count": 2,
        "portability_probe_pass_count": portability_probe_pass_count,
        "portability_probe_fail_count": portability_probe_fail_count,
        "portability_probe_not_executed_count": portability_probe_not_executed_count,
        "boolean_predicates_portable": boolean_probe_status == "PASS",
        "reflection_portable": reflection_probe_status == "PASS",
        "portability_probe_test_names": {"boolean_predicates_portable": "test_native_sql_server_boolean_predicates_portable", "reflection_portable": "test_native_sql_server_reflection_compatibility"},
        "result_version": 2,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junitxml", type=Path, required=True)
    parser.add_argument("--bootstrap-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run(args.junitxml, args.bootstrap_result, args.output)["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
