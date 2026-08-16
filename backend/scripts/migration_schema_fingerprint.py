"""Capture a deterministic PostgreSQL schema fingerprint for roundtrip evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text


def fingerprint(database_url: str) -> dict:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        tables = {
            row["table_name"]: {"columns": [], "constraints": [], "indexes": []}
            for row in connection.execute(
                text(
                    """
                    SELECT c.relname AS table_name
                    FROM pg_class AS c
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
                    ORDER BY c.relname
                    """
                )
            ).mappings()
        }
        for row in connection.execute(
            text(
                """
                SELECT c.relname AS table_name, a.attname AS name,
                       format_type(a.atttypid, a.atttypmod) AS type,
                       a.attnotnull AS not_null,
                       pg_get_expr(d.adbin, d.adrelid) AS default,
                       a.attidentity AS identity,
                       a.attgenerated AS generated,
                       col_description(a.attrelid, a.attnum) AS comment
                FROM pg_attribute AS a
                JOIN pg_class AS c ON c.oid = a.attrelid
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                LEFT JOIN pg_attrdef AS d
                  ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE n.nspname = 'public'
                  AND c.relkind IN ('r', 'p')
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY c.relname, a.attnum
                """
            )
        ).mappings():
            tables[row["table_name"]]["columns"].append({
                "name": row["name"],
                "type": row["type"],
                "nullable": not row["not_null"],
                "default": row["default"],
                "identity": row["identity"],
                "generated": row["generated"],
                "comment": row["comment"],
            })

        constraint_rows = connection.execute(
            text(
                """
                SELECT con.conname AS name, src.relname AS table_name,
                       con.contype AS type,
                       pg_get_constraintdef(con.oid, true) AS definition,
                       con.condeferrable AS deferrable,
                       con.condeferred AS initially_deferred,
                       ARRAY(
                         SELECT a.attname
                         FROM unnest(con.conkey) WITH ORDINALITY AS keys(attnum, ord)
                         JOIN pg_attribute AS a
                           ON a.attrelid = con.conrelid AND a.attnum = keys.attnum
                         ORDER BY keys.ord
                       ) AS constrained_columns,
                       dst.relname AS referred_table,
                       dst_ns.nspname AS referred_schema,
                       ARRAY(
                         SELECT a.attname
                         FROM unnest(con.confkey) WITH ORDINALITY AS keys(attnum, ord)
                         JOIN pg_attribute AS a
                           ON a.attrelid = con.confrelid AND a.attnum = keys.attnum
                         ORDER BY keys.ord
                       ) AS referred_columns
                FROM pg_constraint AS con
                JOIN pg_class AS src ON src.oid = con.conrelid
                JOIN pg_namespace AS src_ns ON src_ns.oid = src.relnamespace
                LEFT JOIN pg_class AS dst ON dst.oid = con.confrelid
                LEFT JOIN pg_namespace AS dst_ns ON dst_ns.oid = dst.relnamespace
                WHERE src_ns.nspname = 'public'
                  AND con.contype IN ('p', 'u', 'f', 'c', 'x')
                ORDER BY src.relname, con.conname
                """
            )
        ).mappings()
        for row in constraint_rows:
            item = {
                "name": row["name"],
                "type": row["type"],
                "definition": row["definition"],
                "deferrable": row["deferrable"],
                "initially_deferred": row["initially_deferred"],
                "constrained_columns": list(row["constrained_columns"] or []),
            }
            if row["type"] == "f":
                item.update({
                    "referred_schema": row["referred_schema"],
                    "referred_table": row["referred_table"],
                    "referred_columns": list(row["referred_columns"] or []),
                })
            tables[row["table_name"]]["constraints"].append(item)

        for row in connection.execute(
            text(
                """
                SELECT table_rel.relname AS table_name, index_rel.relname AS name,
                       idx.indisunique AS unique, idx.indisprimary AS primary,
                       idx.indisvalid AS valid, idx.indpred IS NOT NULL AS partial,
                       pg_get_indexdef(index_rel.oid) AS definition,
                       pg_get_expr(idx.indpred, idx.indrelid, true) AS predicate
                FROM pg_index AS idx
                JOIN pg_class AS table_rel ON table_rel.oid = idx.indrelid
                JOIN pg_namespace AS table_ns ON table_ns.oid = table_rel.relnamespace
                JOIN pg_class AS index_rel ON index_rel.oid = idx.indexrelid
                WHERE table_ns.nspname = 'public'
                ORDER BY table_rel.relname, index_rel.relname
                """
            )
        ).mappings():
            tables[row["table_name"]]["indexes"].append({
                "name": row["name"],
                "unique": row["unique"],
                "primary": row["primary"],
                "valid": row["valid"],
                "partial": row["partial"],
                "definition": row["definition"],
                "predicate": row["predicate"],
            })

        domains = [dict(row) for row in connection.execute(
            text(
                """
                SELECT n.nspname AS schema_name, t.typname AS name,
                       format_type(t.typbasetype, t.typtypmod) AS base_type,
                       t.typnotnull AS not_null,
                       pg_get_expr(t.typdefaultbin, 0) AS default
                FROM pg_type AS t
                JOIN pg_namespace AS n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public' AND t.typtype = 'd'
                ORDER BY t.typname
                """
            )
        ).mappings()]
        sequences = [dict(row) for row in connection.execute(
            text(
                """
                SELECT n.nspname AS schema_name, c.relname AS name,
                       s.seqstart AS start, s.seqincrement AS increment,
                       s.seqmin AS min, s.seqmax AS max, s.seqcache AS cache,
                       s.seqcycle AS cycle,
                       owner_ns.nspname AS owner_schema,
                       owner_table.relname AS owner_table,
                       owner_column.attname AS owner_column
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                JOIN pg_sequence AS s ON s.seqrelid = c.oid
                LEFT JOIN pg_depend AS dep
                  ON dep.objid = c.oid AND dep.deptype = 'a'
                LEFT JOIN pg_class AS owner_table ON owner_table.oid = dep.refobjid
                LEFT JOIN pg_namespace AS owner_ns ON owner_ns.oid = owner_table.relnamespace
                LEFT JOIN pg_attribute AS owner_column
                  ON owner_column.attrelid = dep.refobjid AND owner_column.attnum = dep.refobjsubid
                WHERE n.nspname = 'public' AND c.relkind = 'S'
                ORDER BY c.relname
                """
            )
        ).mappings()]
        schemas = [row[0] for row in connection.execute(
            text("SELECT nspname FROM pg_namespace WHERE nspname = 'public'")
        )]
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        enums = connection.execute(
            text(
                """
                SELECT n.nspname AS schema_name, t.typname AS name,
                       array_agg(e.enumlabel ORDER BY e.enumsortorder) AS labels
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE n.nspname = 'public'
                GROUP BY n.nspname, t.typname
                ORDER BY t.typname
                """
            )
        )
        enum_rows = [dict(row._mapping) for row in enums]
        for table in tables.values():
            table["columns"].sort(key=lambda item: item["name"])
            table["constraints"].sort(key=lambda item: (item["type"], item["name"]))
            table["indexes"].sort(key=lambda item: item["name"])
    engine.dispose()
    return {
        "schemas": sorted(schemas),
        "alembic_version": version,
        "table_count": len(tables),
        "tables": tables,
        "enums": sorted(enum_rows, key=lambda item: (item["schema_name"], item["name"])),
        "domains": sorted(domains, key=lambda item: (item["schema_name"], item["name"])),
        "sequences": sorted(sequences, key=lambda item: (item["schema_name"], item["name"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--compare")
    args = parser.parse_args()
    database_url = os.environ["DATABASE_URL"]
    result = fingerprint(database_url)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    if args.compare:
        before = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        comparable_before = {key: value for key, value in before.items() if key != "alembic_version"}
        comparable_after = {key: value for key, value in result.items() if key != "alembic_version"}
        foreign_key_changes = []
        for table in sorted(set(before.get("tables", {})) | set(result.get("tables", {}))):
            before_fks = {json.dumps(item, sort_keys=True, default=str) for item in before.get("tables", {}).get(table, {}).get("foreign_keys", [])}
            after_fks = {json.dumps(item, sort_keys=True, default=str) for item in result.get("tables", {}).get(table, {}).get("foreign_keys", [])}
            removed = sorted(before_fks - after_fks)
            added = sorted(after_fks - before_fks)
            if removed or added:
                foreign_key_changes.append({
                    "table": table,
                    "removed": [json.loads(item) for item in removed],
                    "added": [json.loads(item) for item in added],
                })
        diff = {
            "parity": comparable_before == comparable_after,
            "before_alembic_version": before.get("alembic_version"),
            "after_alembic_version": result.get("alembic_version"),
            "before_table_count": before.get("table_count"),
            "after_table_count": result.get("table_count"),
            "changed": [] if comparable_before == comparable_after else ["schema fingerprint differs"],
            "foreign_key_changes": foreign_key_changes,
        }
        diff_path = Path(os.environ.get("SCHEMA_DIFF_OUTPUT", "artifacts/migration-roundtrip-repair/schema-diff.json"))
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(
            json.dumps(diff, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise SystemExit(0 if diff["parity"] and result.get("alembic_version") == before.get("alembic_version") else 1)
    print(json.dumps({"table_count": result["table_count"], "alembic_version": result["alembic_version"]}, sort_keys=True))


if __name__ == "__main__":
    main()
