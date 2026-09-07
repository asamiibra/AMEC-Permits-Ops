"""Deterministic active database-engine coupling inventory for V3.6R1."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(
    r"postgres|postgresql|psycopg|pg_advisory|pg_roles|sslmode|PGSSL|"
    r"5432|postgres\.database\.azure\.com|sqlalchemy\.dialects\.postgresql|"
    r"JSONB|ARRAY|\bUUID\s*\(|nextval|RETURNING|ILIKE|ON CONFLICT|"
    r"mssql|pyodbc|odbc|sql server|azure sql",
    re.IGNORECASE,
)

ROOTS = (
    "backend/app",
    "backend/migrations/versions",
    "backend/migrations/history",
    "backend/tests",
    "backend/requirements.txt",
    "backend/requirements-runtime.txt",
    "backend/Dockerfile",
    "backend/Dockerfile.dockerignore",
    "scripts/release",
    "release",
    "docs/database",
)


def classify(path: str) -> str:
    if path.startswith("backend/migrations/history/"):
        return "HISTORICAL_PROVENANCE_KEEP"
    if path.startswith("backend/tests/"):
        return "POSTGRES_REFERENCE_TEST_KEEP"
    if path in {"backend/app/db.py", "backend/app/config/settings.py", "backend/app/migrate.py"}:
        return "ACTIVE_RUNTIME_MUST_PORT"
    if path.startswith("backend/migrations/versions/"):
        return "ACTIVE_MIGRATION_MUST_PORT"
    if path in {"backend/requirements.txt", "backend/requirements-runtime.txt", "backend/Dockerfile", "backend/Dockerfile.dockerignore"}:
        return "ACTIVE_RUNTIME_MUST_PORT"
    if path.startswith("scripts/release/") or path.startswith("release/"):
        return "ACTIVE_RUNTIME_MUST_PORT"
    if path.startswith("docs/database/"):
        return "DOCUMENTATION_SUPERSEDED"
    return "FALSE_POSITIVE_OR_ENGINE_NEUTRAL"


def build() -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for root_name in ROOTS:
        root = ROOT / root_name
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file() or ".git" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, 1):
                if PATTERN.search(line):
                    matches.append({
                        "path": rel,
                        "line": line_number,
                        "match": line.strip()[:240],
                        "classification": classify(rel),
                    })
    return {
        "schema_version": "v3.6r1",
        "candidate_base_sha": "fcc4aa8fdabaea14495d7724227120bcf48c87e0",
        "source_engine": "PostgreSQL 16",
        "target_engine": "Azure SQL / SQL Server 2022",
        "matches": matches,
        "unclassified_database_engine_coupling_count": sum(
            item["classification"] == "UNCLASSIFIED" for item in matches
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"PORT_INVENTORY_MATCH_COUNT={len(result['matches'])}")
        print(f"UNCLASSIFIED_DATABASE_ENGINE_COUPLING_COUNT={result['unclassified_database_engine_coupling_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
