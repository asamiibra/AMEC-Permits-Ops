"""Audit nullable unique ORM/migration parity for the SQL Server target."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

from sqlalchemy import UniqueConstraint
from sqlalchemy.schema import Index

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATHS = tuple(sorted((ROOT / "backend/migrations/versions").glob("*.py")))
SAFE_CLASSIFICATION = "NULLABLE_UNIQUE_FILTER_REQUIRED"
NON_NULL_CLASSIFICATION = "NON_NULL_UNIQUE_NO_ACTION"
UNSAFE_CLASSIFICATION = "UNSAFE_FK_OR_SEMANTIC_REVIEW_REQUIRED"

sys.path.insert(0, str(ROOT))
from backend.app.models import Base


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value.strip()).lower()
    while normalized.startswith("(") and normalized.endswith(")"):
        normalized = normalized[1:-1].strip()
    return normalized


def _literal(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_literal(item) for item in node.elts]
    raise ValueError(f"non-literal migration argument at line {getattr(node, 'lineno', '?')}")


def _model_source_path(table) -> str | None:
    for mapper in Base.registry.mappers:
        if mapper.local_table is not table:
            continue
        module = sys.modules.get(mapper.class_.__module__)
        module_path = getattr(module, "__file__", None)
        if module_path:
            return str(Path(module_path).resolve().relative_to(ROOT))
    return None


def _foreign_key_targets() -> dict[tuple[str, tuple[str, ...]], list[str]]:
    targets: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for table in Base.metadata.tables.values():
        for constraint in table.foreign_key_constraints:
            referred_table = constraint.elements[0].column.table.name
            referred_columns = tuple(element.column.name for element in constraint.elements)
            key = (referred_table, referred_columns)
            reference = f"{table.name}({','.join(element.parent.name for element in constraint.elements)})->{referred_table}({','.join(referred_columns)})"
            targets.setdefault(key, []).append(reference)
    return {key: sorted(values) for key, values in targets.items()}


def _model_objects() -> list[dict[str, object]]:
    foreign_key_targets = _foreign_key_targets()
    objects: list[dict[str, object]] = []
    for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name):
        candidates = [
            ("INDEX", index.name, list(index.columns), index)
            for index in sorted(table.indexes, key=lambda item: item.name or "")
            if isinstance(index, Index) and index.unique
        ]
        candidates.extend(
            ("UNIQUE_CONSTRAINT", constraint.name, list(constraint.columns), constraint)
            for constraint in sorted(table.constraints, key=lambda item: item.name or "")
            if isinstance(constraint, UniqueConstraint)
        )
        for kind, name, columns, item in candidates:
            key_columns = [column.name for column in columns]
            nullable_columns = [column.name for column in columns if column.nullable]
            references = foreign_key_targets.get((table.name, tuple(key_columns)), [])
            objects.append(
                {
                    "object_name": name,
                    "object_kind": kind,
                    "table_name": table.name,
                    "ordered_key_columns": key_columns,
                    "nullable_key_columns": nullable_columns,
                    "all_key_columns_non_null": not nullable_columns,
                    "foreign_key_target_usage": bool(references),
                    "foreign_key_references": references,
                    "model_source_path": _model_source_path(table),
                    "model_filter": _normalize_filter(
                        str(item.dialect_options["mssql"].get("where"))
                        if isinstance(item, Index) and item.dialect_options["mssql"].get("where") is not None
                        else None
                    ),
                }
            )
    return sorted(objects, key=lambda item: (item["table_name"], item["object_kind"], item["object_name"] or ""))


def _migration_objects() -> list[dict[str, object]]:
    objects: list[dict[str, object]] = []
    for migration_path in MIGRATION_PATHS:
        tree = ast.parse(migration_path.read_text(encoding="utf-8"), filename=str(migration_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"create_index", "create_unique_constraint", "create_table"}:
                continue
            if node.func.attr == "create_table":
                if not node.args:
                    continue
                table_name = _literal(node.args[0])
                for child in node.args[1:]:
                    if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute) or child.func.attr != "UniqueConstraint":
                        continue
                    key_columns = [_literal(argument) for argument in child.args]
                    name = next((_literal(keyword.value) for keyword in child.keywords if keyword.arg == "name"), None)
                    objects.append(
                        {
                            "object_name": name,
                            "object_kind": "UNIQUE_CONSTRAINT",
                            "table_name": table_name,
                            "migration_key_columns": key_columns,
                            "migration_filter": None,
                            "migration_line": child.lineno,
                        }
                    )
                continue
            try:
                values = [_literal(argument) for argument in node.args]
            except ValueError:
                continue
            if node.func.attr == "create_index":
                if len(values) < 3:
                    continue
                name, table_name, key_columns = values[:3]
                unique = next((_literal(keyword.value) for keyword in node.keywords if keyword.arg == "unique"), False)
                if unique is not True:
                    continue
                kind = "INDEX"
            else:
                if len(values) < 2:
                    continue
                name, table_name = values[:2]
                key_columns = values[2:]
                kind = "UNIQUE_CONSTRAINT"
            filter_node = next((keyword.value for keyword in node.keywords if keyword.arg == "mssql_where"), None)
            filter_value = None
            if isinstance(filter_node, ast.Call) and isinstance(filter_node.func, ast.Attribute) and filter_node.func.attr == "text" and filter_node.args:
                filter_value = _literal(filter_node.args[0])
            objects.append(
                {
                    "object_name": name,
                    "object_kind": kind,
                    "table_name": table_name,
                    "migration_key_columns": list(key_columns),
                    "migration_filter": _normalize_filter(filter_value),
                    "migration_line": node.lineno,
                }
            )
    return sorted(objects, key=lambda item: (item["table_name"], item["object_kind"], item["object_name"] or ""))


def audit(mode: str) -> dict[str, object]:
    model_objects = _model_objects()
    migration_objects = _migration_objects()
    model_by_key = {(item["table_name"], tuple(item["ordered_key_columns"])): item for item in model_objects}
    migration_by_key = {(item["table_name"], tuple(item["migration_key_columns"])): item for item in migration_objects}
    logical_model_counts: dict[tuple[str, tuple[str, ...]], int] = {}
    logical_migration_counts: dict[tuple[str, tuple[str, ...]], int] = {}
    for item in model_objects:
        key = (str(item["table_name"]), tuple(item["ordered_key_columns"]))
        logical_model_counts[key] = logical_model_counts.get(key, 0) + 1
    for item in migration_objects:
        key = (str(item["table_name"]), tuple(item["migration_key_columns"]))
        logical_migration_counts[key] = logical_migration_counts.get(key, 0) + 1

    objects: list[dict[str, object]] = []
    unclassified = 0
    unsafe = 0
    parity_mismatch = 0
    duplicate_logical = sum(count - 1 for count in logical_model_counts.values() if count > 1) + sum(count - 1 for count in logical_migration_counts.values() if count > 1)
    model_nullable_unfiltered = 0
    migration_nullable_unfiltered = 0
    implemented = 0
    open_repairs = 0
    failures: list[str] = []

    for model in model_objects:
        key = (model["table_name"], tuple(model["ordered_key_columns"]))
        migration = migration_by_key.get(key)
        nullable = list(model["nullable_key_columns"])
        references = list(model["foreign_key_references"])
        expected_filter = _normalize_filter(" AND ".join(f"{column} IS NOT NULL" for column in nullable)) if nullable else None
        if model["all_key_columns_non_null"]:
            classification = NON_NULL_CLASSIFICATION
            reason = "All unique key columns are NOT NULL."
        elif references:
            classification = UNSAFE_CLASSIFICATION
            reason = "Nullable unique key is a foreign-key target."
        else:
            classification = SAFE_CLASSIFICATION
            reason = "Nullable non-FK unique key requires an MSSQL IS NOT NULL filter."
        if classification == UNSAFE_CLASSIFICATION:
            unsafe += 1
        if migration is None:
            unclassified += 1
            parity_mismatch += 1
            migration_name = None
            migration_kind = None
            migration_columns = []
            migration_filter = None
        else:
            migration_name = migration["object_name"]
            migration_kind = migration["object_kind"]
            migration_columns = migration["migration_key_columns"]
            migration_filter = migration["migration_filter"]
            if migration_kind != model["object_kind"] or migration_columns != model["ordered_key_columns"]:
                parity_mismatch += 1
        if classification == SAFE_CLASSIFICATION:
            if model["model_filter"] != expected_filter:
                model_nullable_unfiltered += 1
            if migration is None or migration_filter != expected_filter:
                migration_nullable_unfiltered += 1
            if model["model_filter"] == expected_filter and migration is not None and migration_filter == expected_filter:
                implemented += 1
            else:
                open_repairs += 1
        elif model["model_filter"] is not None or (migration is not None and migration_filter is not None):
            failures.append(f"unexpected filter on non-null/unsafe object {model['object_name']}")
        objects.append(
            {
                "object_name": model["object_name"],
                "object_kind": model["object_kind"],
                "table_name": model["table_name"],
                "ordered_key_columns": model["ordered_key_columns"],
                "nullable_key_columns": nullable,
                "all_key_columns_non_null": model["all_key_columns_non_null"],
                "foreign_key_target_usage": model["foreign_key_target_usage"],
                "foreign_key_references": references,
                "model_source_path": model["model_source_path"],
                "migration_object_name": migration_name,
                "migration_object_kind": migration_kind,
                "migration_key_columns": migration_columns,
                "model_filter": model["model_filter"],
                "migration_filter": migration_filter,
                "expected_mssql_filter": expected_filter,
                "classification": classification,
                "reason": reason,
            }
        )

    for migration in migration_objects:
        key = (migration["table_name"], tuple(migration["migration_key_columns"]))
        if key not in model_by_key:
            unclassified += 1
            parity_mismatch += 1
            failures.append(f"migration unique object has no ORM counterpart {migration['object_name']}")

    for item in objects:
        if item["classification"] == UNSAFE_CLASSIFICATION:
            failures.append(f"unsafe object {item['object_name']}")
        if item["classification"] == SAFE_CLASSIFICATION and item["model_filter"] != item["expected_mssql_filter"]:
            if mode == "post":
                failures.append(f"unfiltered ORM nullable unique object {item['object_name']}")
        if item["classification"] == SAFE_CLASSIFICATION and item["migration_filter"] != item["expected_mssql_filter"]:
            if mode == "post":
                failures.append(f"unfiltered migration nullable unique object {item['object_name']}")
    if unclassified or parity_mismatch or duplicate_logical or unsafe:
        failures.append("structural nullable unique audit failure")
    if mode == "post" and open_repairs:
        failures.append("nullable unique filter repair remains open")
    result = "PASS" if not failures else "FAIL"
    return {
        "audit_type": "PHASE4_R3R5_NULLABLE_UNIQUE_AUDIT",
        "mode": mode,
        "model_source_path": "backend/app/models/entities.py",
        "migration_source_path": [str(path.relative_to(ROOT)) for path in MIGRATION_PATHS],
        "unique_object_total_count": len(model_objects),
        "unique_object_classified_count": len(objects),
        "unclassified_unique_object_count": unclassified,
        "unsafe_fk_or_semantic_review_required_count": unsafe,
        "nullable_unique_filter_required_count": sum(item["classification"] == SAFE_CLASSIFICATION for item in objects),
        "model_nullable_unique_unfiltered_count": model_nullable_unfiltered,
        "migration_nullable_unique_unfiltered_count": migration_nullable_unfiltered,
        "model_migration_nullable_unique_parity_mismatch_count": parity_mismatch,
        "nullable_unique_filter_required_open_count": open_repairs,
        "nullable_unique_filter_implemented_count": implemented,
        "duplicate_logical_unique_object_count": duplicate_logical,
        "unsafe_objects": [item["object_name"] for item in objects if item["classification"] == UNSAFE_CLASSIFICATION],
        "fk_references": sorted(reference for item in objects for reference in item["foreign_key_references"]),
        "objects": objects,
        "failures": sorted(set(failures)),
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pre", "post"), required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.mode)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for key in (
        "unique_object_total_count",
        "unique_object_classified_count",
        "unclassified_unique_object_count",
        "unsafe_fk_or_semantic_review_required_count",
        "model_nullable_unique_unfiltered_count",
        "migration_nullable_unique_unfiltered_count",
        "model_migration_nullable_unique_parity_mismatch_count",
        "nullable_unique_filter_required_open_count",
        "nullable_unique_filter_implemented_count",
    ):
        print(f"{key.upper()}={result[key]}")
    print(f"NULLABLE_UNIQUE_AUDIT_RESULT={result['result']}")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
