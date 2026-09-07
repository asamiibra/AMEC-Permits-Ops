"""Capture and verify the frozen PostgreSQL reference contract.

This module intentionally uses SQLAlchemy's public inspection API rather than
the application models.  The reference database is authoritative for the
physical contract; ORM comparison is a separate, explicitly classified check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, inspect, text


SOURCE_SHA = "96c4b90968754efd8e5998cd1b1793b67c23d2bc"
SOURCE_PARENT_SHA = "dd24e1c9ac65d6137614252f821d3a3e6b1263c2"
SOURCE_TREE_SHA = "c547005d3a18a9c71965a40a5327aa46edb28c6f"
LEGACY_VERSIONS_TREE_SHA = "4b5df36eaba0816df17bb2078958da946a6442d6"
LEGACY_HEAD = "0059_entra_user_identity"
EXCLUDED_TABLES = {"alembic_version"}
CONTROL_TABLE_ALLOWLIST = {"master_content_reference_sequences"}

NORMALIZATION_RULES = [
    {
        "id": "N001",
        "field": "schema.database_identity",
        "rule": "Exclude database name, OIDs, owner, ACL and physical file identifiers.",
    },
    {
        "id": "N002",
        "field": "schema.alembic_version",
        "rule": "Exclude the Alembic control table and current revision value from physical schema parity.",
    },
    {
        "id": "N003",
        "field": "control_data.*.created_at|updated_at",
        "rule": "Represent migration-owned timestamps as CURRENT_TIMESTAMP semantics, not run-time wall-clock values.",
    },
    {
        "id": "N004",
        "field": "json",
        "rule": "Serialize keys in lexical order and use compact UTF-8 JSON with no insignificant whitespace.",
    },
]

CONTRACT_EXCLUSIONS = [
    {
        "id": "E001",
        "object": "alembic_version",
        "reason": "Alembic owns this control table and writes the active revision after upgrade.",
    },
    {
        "id": "E002",
        "object": "database OID/owner/ACL",
        "reason": "Environment identity is not application schema contract.",
    },
    {
        "id": "E003",
        "object": "control-data timestamp values",
        "reason": "The legacy migration uses CURRENT_TIMESTAMP; stable semantics are authoritative.",
    },
]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (UUID,)):
        return str(value)
    if isinstance(value, bytes):
        return {"__bytes_sha256__": hashlib.sha256(value).hexdigest(), "length": len(value)}
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def source_proof(source_dir: Path) -> dict[str, Any]:
    try:
        git_options = {"text": True, "stderr": subprocess.DEVNULL}
        actual_sha = subprocess.check_output(["git", "-C", str(source_dir), "rev-parse", "HEAD"], **git_options).strip()
        actual_tree = subprocess.check_output(["git", "-C", str(source_dir), "rev-parse", "HEAD^{tree}"], **git_options).strip()
        actual_parent = subprocess.check_output(["git", "-C", str(source_dir), "rev-parse", "HEAD^"], **git_options).strip()
        versions_tree = subprocess.check_output(
            ["git", "-C", str(source_dir), "rev-parse", "HEAD:backend/migrations/versions"], **git_options
        ).strip()
    except subprocess.CalledProcessError:
        actual_sha = actual_tree = actual_parent = versions_tree = "ARCHIVE_OR_UNAVAILABLE"
    count = len(list((source_dir / "backend/migrations/versions").glob("*.py")))
    proof = {
        "source_sha": actual_sha,
        "source_parent_sha": actual_parent,
        "source_tree_sha": actual_tree,
        "legacy_versions_tree_sha": versions_tree,
        "legacy_migration_count": count,
        "expected_source_sha": SOURCE_SHA,
        "expected_source_parent_sha": SOURCE_PARENT_SHA,
        "expected_source_tree_sha": SOURCE_TREE_SHA,
        "expected_legacy_versions_tree_sha": LEGACY_VERSIONS_TREE_SHA,
        "expected_legacy_migration_count": 59,
        "legacy_head": LEGACY_HEAD,
        "reference_source_is_candidate": False,
    }
    if source_dir.name.startswith("AMEC-Permits-Ops-") and actual_sha == "ARCHIVE_OR_UNAVAILABLE":
        proof["archive_materialization"] = True
    return proof


def _type_contract(column_type: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"class": type(column_type).__name__, "sql": str(column_type)}
    for attribute in ("length", "precision", "scale", "timezone", "asdecimal", "collation"):
        value = getattr(column_type, attribute, None)
        if value is not None:
            result[attribute] = value
    if result["class"].upper() == "ENUM":
        result["enum_name"] = getattr(column_type, "name", None)
        result["enum_values"] = list(getattr(column_type, "enums", ()) or ())
        result["enum_schema"] = getattr(column_type, "schema", None) or "public"
    return result


def _strip_check(definition: str) -> str:
    value = definition.strip()
    if value.upper().startswith("CHECK "):
        return value[6:].strip()
    return value


def schema_contract(engine: Any) -> dict[str, Any]:
    database_inspector = inspect(engine)
    tables = sorted(t for t in database_inspector.get_table_names(schema="public") if t not in EXCLUDED_TABLES)
    result: dict[str, Any] = {
        "contract_version": 1,
        "schema": "public",
        "excluded_tables": sorted(EXCLUDED_TABLES),
        "enums": sorted(database_inspector.get_enums(schema="public"), key=lambda item: item["name"]),
        "tables": [],
        "sequences": sorted(database_inspector.get_sequence_names(schema="public")),
    }
    for table in tables:
        columns = []
        for ordinal_position, column in enumerate(database_inspector.get_columns(table, schema="public"), start=1):
            identity = column.get("identity")
            computed = column.get("computed")
            columns.append(
                {
                    "name": column["name"],
                    "ordinal_position": ordinal_position,
                    "type": _type_contract(column["type"]),
                    "nullable": bool(column.get("nullable", True)),
                    "default": str(column["default"]) if column.get("default") is not None else None,
                    "autoincrement": column.get("autoincrement"),
                    "identity": jsonable(identity),
                    "computed": jsonable(computed),
                    "comment": column.get("comment"),
                }
            )
        primary_key = database_inspector.get_pk_constraint(table, schema="public")
        unique_constraints = database_inspector.get_unique_constraints(table, schema="public")
        foreign_keys = database_inspector.get_foreign_keys(table, schema="public")
        checks = database_inspector.get_check_constraints(table, schema="public")
        indexes = database_inspector.get_indexes(table, schema="public")
        result["tables"].append(
            {
                "name": table,
                "columns": columns,
                "primary_key": {
                    "name": primary_key.get("name"),
                    "columns": list(primary_key.get("constrained_columns") or []),
                },
                "unique_constraints": sorted(
                    [
                        {"name": item.get("name"), "columns": list(item.get("column_names") or [])}
                        for item in unique_constraints
                    ],
                    key=lambda item: (item["name"] or "", item["columns"]),
                ),
                "foreign_keys": sorted(
                    [
                        {
                            "name": item.get("name"),
                            "columns": list(item.get("constrained_columns") or []),
                            "referred_schema": item.get("referred_schema") or "public",
                            "referred_table": item.get("referred_table"),
                            "referred_columns": list(item.get("referred_columns") or []),
                            "ondelete": (item.get("options") or {}).get("ondelete"),
                            "onupdate": (item.get("options") or {}).get("onupdate"),
                            "deferrable": (item.get("options") or {}).get("deferrable"),
                            "initially": (item.get("options") or {}).get("initially"),
                        }
                        for item in foreign_keys
                    ],
                    key=lambda item: (item["name"] or "", item["columns"]),
                ),
                "checks": sorted(
                    [
                        {"name": item.get("name"), "sqltext": _strip_check(str(item.get("sqltext") or ""))}
                        for item in checks
                    ],
                    key=lambda item: (item["name"] or "", item["sqltext"]),
                ),
                "indexes": sorted(
                    [
                        {
                            "name": item.get("name"),
                            "columns": list(item.get("column_names") or []),
                            "unique": bool(item.get("unique")),
                            "dialect_options": jsonable(item.get("dialect_options") or {}),
                        }
                        for item in indexes
                        if not item.get("duplicates_constraint")
                    ],
                    key=lambda item: item["name"] or "",
                ),
            }
        )
    result["tables"].sort(key=lambda item: item["name"])
    result["schema_sha256"] = sha256(result)
    return result


def control_contract(engine: Any) -> dict[str, Any]:
    database_inspector = inspect(engine)
    tables = sorted(t for t in database_inspector.get_table_names(schema="public") if t not in EXCLUDED_TABLES)
    nonempty: list[dict[str, Any]] = []
    with engine.connect() as connection:
        for table in tables:
            quoted_table = '"' + table.replace('"', '""') + '"'
            rows = [dict(row._mapping) for row in connection.execute(text(f"SELECT * FROM {quoted_table}"))]
            if not rows:
                continue
            if table not in CONTROL_TABLE_ALLOWLIST:
                raise RuntimeError(f"unexpected non-empty non-control table: {table}")
            normalized_rows = []
            for row in rows:
                normalized = {}
                volatile_fields = []
                for key, value in row.items():
                    if key in {"created_at", "updated_at"} and isinstance(value, datetime):
                        normalized[key] = {"__volatile__": "CURRENT_TIMESTAMP"}
                        volatile_fields.append(key)
                    else:
                        normalized[key] = jsonable(value)
                normalized_rows.append({"stable_fields": normalized, "volatile_fields": sorted(volatile_fields)})
            nonempty.append({"table": table, "rows": normalized_rows})
    contract = {
        "contract_version": 1,
        "allowed_control_tables": sorted(CONTROL_TABLE_ALLOWLIST),
        "tables": nonempty,
        "control_data_sha256": sha256(nonempty),
    }
    return contract


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def capture(args: argparse.Namespace) -> None:
    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    proof = source_proof(source_dir)
    engine = create_engine(args.database_url, future=True)
    schema = schema_contract(engine)
    control = control_contract(engine)
    write_json(output_dir / f"{args.label}-schema.contract.json", schema)
    write_json(output_dir / f"{args.label}-control-data.contract.json", control)
    write_json(output_dir / "normalization-rules.json", NORMALIZATION_RULES)
    write_json(output_dir / "contract-exclusions.json", CONTRACT_EXCLUSIONS)
    write_json(output_dir / f"{args.label}-source-proof.json", proof)
    print(f"{args.label.upper()}_SCHEMA_CONTRACT_SHA256={schema['schema_sha256']}")
    print(f"{args.label.upper()}_CONTROL_DATA_SHA256={control['control_data_sha256']}")
    print(f"{args.label.upper()}_SOURCE_SHA={proof['source_sha']}")


def compare(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    first = json.loads((output_dir / "reference-1-schema.contract.json").read_text())
    second = json.loads((output_dir / "reference-2-schema.contract.json").read_text())
    first_control = json.loads((output_dir / "reference-1-control-data.contract.json").read_text())
    second_control = json.loads((output_dir / "reference-2-control-data.contract.json").read_text())
    if first != second:
        raise SystemExit("STOP_REFERENCE_NONDETERMINISM: schema contracts differ")
    if first_control != second_control:
        raise SystemExit("STOP_REFERENCE_NONDETERMINISM: control-data contracts differ")
    if first["schema_sha256"] != sha256({k: v for k, v in first.items() if k != "schema_sha256"}):
        raise SystemExit("schema contract self-hash mismatch")
    print(f"REFERENCE_SCHEMA_CONTRACT_SHA256={first['schema_sha256']}")
    print(f"REFERENCE_CONTROL_DATA_SHA256={first_control['control_data_sha256']}")
    print("REFERENCE_SCHEMA_DETERMINISTIC=true")
    print("REFERENCE_CONTROL_DATA_DETERMINISTIC=true")


def orm_classify(args: argparse.Namespace) -> None:
    source_dir = Path(args.source_dir).resolve()
    contract = json.loads((Path(args.contract)).read_text())
    sys.path.insert(0, str(source_dir))
    from backend.app.models import Base  # type: ignore

    orm_tables = set(Base.metadata.tables)
    db_tables = {item["name"] for item in contract["tables"]}
    differences: list[dict[str, Any]] = []
    for table in sorted(db_tables - orm_tables):
        differences.append({"kind": "table", "object": table, "classification": "UNCLASSIFIED"})
    for table in sorted(orm_tables - db_tables):
        differences.append({"kind": "table", "object": table, "classification": "UNCLASSIFIED"})
    for item in contract["tables"]:
        table = item["name"]
        if table not in orm_tables:
            continue
        db_columns = {column["name"] for column in item["columns"]}
        orm_columns = set(Base.metadata.tables[table].columns.keys())
        for column in sorted(db_columns - orm_columns):
            classification = "MIGRATION_OWNED_PHYSICAL_ATTRIBUTE" if (table, column) == ("users", "entra_object_id") else "UNCLASSIFIED"
            differences.append({"kind": "column", "object": f"{table}.{column}", "classification": classification})
        for column in sorted(orm_columns - db_columns):
            differences.append({"kind": "column", "object": f"{table}.{column}", "classification": "UNCLASSIFIED"})
    unclassified = [item for item in differences if item["classification"] == "UNCLASSIFIED"]
    result = {
        "contract_version": 1,
        "differences": differences,
        "raw_diff_count": len(differences),
        "unclassified_diff_count": len(unclassified),
        "blocking_contradiction_count": len(unclassified),
        "reference_object_drop_for_orm_count": 0,
        "classification_rules": ["users.entra_object_id=MIGRATION_OWNED_PHYSICAL_ATTRIBUTE"],
    }
    write_json(Path(args.output), result)
    print(f"ORM_{args.label.upper()}_RAW_DIFF_COUNT={result['raw_diff_count']}")
    print(f"ORM_{args.label.upper()}_UNCLASSIFIED_DIFF_COUNT={result['unclassified_diff_count']}")
    print(f"ORM_{args.label.upper()}_BLOCKING_CONTRADICTION_COUNT={result['blocking_contradiction_count']}")
    if unclassified:
        raise SystemExit("STOP_OWNER_DECISION_REQUIRED_SCHEMA_CONTRADICTION")


def manifest(args: argparse.Namespace) -> None:
    root = Path(args.directory).resolve()
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "reference-package-manifest.json"):
        entries.append({"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    value = {"manifest_version": 1, "files": entries}
    write_json(root / "reference-package-manifest.json", value)
    print(f"REFERENCE_PACKAGE_MANIFEST_SHA256={sha256(value)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--database-url", required=True)
    capture_parser.add_argument("--source-dir", required=True)
    capture_parser.add_argument("--output-dir", required=True)
    capture_parser.add_argument("--label", required=True)
    capture_parser.set_defaults(function=capture)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--output-dir", required=True)
    compare_parser.set_defaults(function=compare)
    orm_parser = sub.add_parser("orm-classify")
    orm_parser.add_argument("--source-dir", required=True)
    orm_parser.add_argument("--contract", required=True)
    orm_parser.add_argument("--output", required=True)
    orm_parser.add_argument("--label", required=True)
    orm_parser.set_defaults(function=orm_classify)
    manifest_parser = sub.add_parser("manifest")
    manifest_parser.add_argument("--directory", required=True)
    manifest_parser.set_defaults(function=manifest)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
