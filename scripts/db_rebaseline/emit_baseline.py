"""Emit an explicit Alembic root migration from a frozen reference contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def py(value: Any) -> str:
    return repr(value)


def type_expression(type_info: dict[str, Any]) -> str:
    kind = type_info["class"].upper()
    if kind == "VARCHAR":
        length = type_info.get("length")
        return f"sa.String({length})" if length else "sa.String()"
    if kind == "TEXT":
        return "sa.Text()"
    if kind == "INTEGER":
        return "sa.Integer()"
    if kind == "BIGINT":
        return "sa.BigInteger()"
    if kind in {"SMALLINTEGER", "SMALL_INT"}:
        return "sa.SmallInteger()"
    if kind in {"DOUBLE_PRECISION", "FLOAT", "REAL"}:
        return "sa.Float()"
    if kind == "NUMERIC":
        args = []
        if type_info.get("precision") is not None:
            args.append(str(type_info["precision"]))
        if type_info.get("scale") is not None:
            args.append(str(type_info["scale"]))
        return f"sa.Numeric({', '.join(args)})" if args else "sa.Numeric()"
    if kind == "BOOLEAN":
        return "sa.Boolean()"
    if kind == "DATE":
        return "sa.Date()"
    if kind == "TIMESTAMP":
        return f"sa.DateTime(timezone={bool(type_info.get('timezone'))!r})"
    if kind == "JSON":
        return "sa.JSON()"
    if kind == "BYTEA":
        return "sa.LargeBinary()"
    if kind == "ENUM":
        values = ", ".join(py(value) for value in type_info.get("enum_values", []))
        args = f"{values}, name={py(type_info['enum_name'])}"
        schema = type_info.get("enum_schema")
        if schema and schema != "public":
            args += f", schema={py(schema)}"
        return f"sa.Enum({args})"
    raise ValueError(f"unsupported reference type: {type_info}")


def default_expression(value: str | None) -> str | None:
    if value is None:
        return None
    return f"sa.text({value!r})"


def emit_table(table: dict[str, Any]) -> list[str]:
    lines = [f"    op.create_table({table['name']!r},"]
    for column in sorted(table["columns"], key=lambda item: item["ordinal_position"]):
        options = [f"nullable={bool(column['nullable'])!r}"]
        if column.get("default") is not None:
            options.append(f"server_default={default_expression(column['default'])}")
        if column.get("comment") is not None:
            options.append(f"comment={column['comment']!r}")
        lines.append(
            f"        sa.Column({column['name']!r}, {type_expression(column['type'])}, {', '.join(options)}),"
        )
    primary_key = table.get("primary_key") or {}
    if primary_key.get("columns"):
        name = f", name={primary_key['name']!r}" if primary_key.get("name") else ""
        lines.append(f"        sa.PrimaryKeyConstraint({', '.join(py(c) for c in primary_key['columns'])}{name}),")
    for constraint in table.get("unique_constraints", []):
        name = f", name={constraint['name']!r}" if constraint.get("name") else ""
        lines.append(f"        sa.UniqueConstraint({', '.join(py(c) for c in constraint['columns'])}{name}),")
    for constraint in table.get("checks", []):
        name = f", name={constraint['name']!r}" if constraint.get("name") else ""
        lines.append(f"        sa.CheckConstraint(sa.text({constraint['sqltext']!r}){name}),")
    lines.append("    )")
    return lines


def emit_foreign_key(table: str, foreign_key: dict[str, Any]) -> str:
    args = [
        repr(foreign_key["name"]),
        repr(table),
        repr(foreign_key["referred_table"]),
        repr(foreign_key["columns"]),
        repr(foreign_key["referred_columns"]),
    ]
    options = []
    if foreign_key.get("referred_schema") and foreign_key["referred_schema"] != "public":
        options.append(f"referent_schema={foreign_key['referred_schema']!r}")
    for key in ("ondelete", "onupdate", "deferrable", "initially"):
        if foreign_key.get(key) is not None:
            options.append(f"{key}={foreign_key[key]!r}")
    suffix = ", " + ", ".join(options) if options else ""
    return f"    op.create_foreign_key({', '.join(args)}{suffix})"


def emit_index(table: str, index: dict[str, Any]) -> str:
    options = f", unique=True" if index.get("unique") else ""
    return f"    op.create_index({index['name']!r}, {table!r}, {index['columns']!r}{options})"


def emit_control(control: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for table in control.get("tables", []):
        for row in table["rows"]:
            fields = row["stable_fields"]
            names = list(fields)
            placeholders = []
            for index, name in enumerate(names):
                value = fields[name]
                if isinstance(value, dict) and value.get("__volatile__") == "CURRENT_TIMESTAMP":
                    placeholders.append("CURRENT_TIMESTAMP")
                else:
                    placeholders.append(f":value_{index}")
            lines.append("    bind = op.get_bind()")
            lines.append(
                f"    bind.execute(sa.text(\"INSERT INTO {table['table']} ({', '.join(names)}) VALUES ({', '.join(placeholders)}) ON CONFLICT DO NOTHING\"),"
            )
            params = [
                f"'value_{index}': {fields[name]!r}"
                for index, name in enumerate(names)
                if not (isinstance(fields[name], dict) and fields[name].get("__volatile__") == "CURRENT_TIMESTAMP")
            ]
            lines.append(f"        {{{', '.join(params)}}})")
        lines.append("    # Control data source: legacy revision 0055_bd_proposal_final_hardening.")
    return lines


def emit(args: argparse.Namespace) -> None:
    contract = json.loads(Path(args.contract).read_text())
    control = json.loads(Path(args.control).read_text())
    lines = [
        '"""Immutable PostgreSQL R13 reference baseline; generated from the frozen CI contract."""',
        "",
        "from alembic import op",
        "import sqlalchemy as sa",
        "",
        'revision = "baseline_r13_0059"',
        "down_revision = None",
        "branch_labels = None",
        "depends_on = None",
        "",
        f"REFERENCE_SCHEMA_CONTRACT_SHA256 = {contract['schema_sha256']!r}",
        f"REFERENCE_CONTROL_DATA_SHA256 = {control['control_data_sha256']!r}",
        "",
        "def upgrade() -> None:",
        "    # Explicit operations are emitted from reference ordinal positions.",
        "    # The reference package, not live ORM declaration order, is authoritative.",
    ]
    for table in contract["tables"]:
        lines.extend(emit_table(table))
    lines.append("")
    lines.append("    # Foreign keys are added after all tables so cyclic dependencies remain intact.")
    for table in contract["tables"]:
        for foreign_key in table.get("foreign_keys", []):
            lines.append(emit_foreign_key(table["name"], foreign_key))
    lines.append("")
    for table in contract["tables"]:
        for index in table.get("indexes", []):
            lines.append(emit_index(table["name"], index))
    control_lines = emit_control(control)
    if control_lines:
        lines.append("")
        lines.extend(control_lines)
    lines.extend(
        [
            "",
            "def downgrade() -> None:",
            '    raise RuntimeError("Canonical root baseline downgrade is intentionally unsupported")',
            "",
        ]
    )
    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"BASELINE_GENERATED_SCHEMA_SHA256={contract['schema_sha256']}")
    print(f"BASELINE_GENERATED_CONTROL_DATA_SHA256={control['control_data_sha256']}")
    print(f"BASELINE_OUTPUT={args.output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--output", required=True)
    emit(parser.parse_args())


if __name__ == "__main__":
    main()
