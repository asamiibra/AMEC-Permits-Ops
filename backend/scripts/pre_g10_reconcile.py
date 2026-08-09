"""Native pre-G10 integrity and evidence reconciliation runner."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from backend.app.fixtures.canonical import CANONICAL_FIXTURE_ID, CANONICAL_FIXTURE_MANIFEST_HASH, CANONICAL_FIXTURE_VERSION


ROOT = Path(__file__).resolve().parents[2]
PG_DB = "permitops_pre_g10"
PG_URL = f"postgresql+psycopg://ahmedsami@localhost:5432/{PG_DB}"


def environment(database_url: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update({"APP_ENV": "TEST", "SYNTHETIC_ONLY": "true", "PYTHONPATH": "."})
    if database_url:
        env["DATABASE_URL"] = database_url
    return env


def run(label: str, args: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT) -> dict:
    result = subprocess.run(args, cwd=cwd, env=env or environment(), capture_output=True, text=True)
    payload = {"label": label, "status": "PASS" if result.returncode == 0 else "FAIL", "returncode": result.returncode, "stdout_tail": result.stdout[-2500:], "stderr_tail": result.stderr[-1200:]}
    if result.returncode:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def fresh_sqlite(path: Path) -> str:
    path.unlink(missing_ok=True)
    url = f"sqlite:///{path}"
    env = environment(url)
    run(f"sqlite migrate {path.name}", ["python3", "-m", "alembic", "upgrade", "head"], env=env)
    run(f"sqlite seed {path.name}", ["python3", "-m", "backend.app.seed.cli", "seed"], env=env)
    return url


def fresh_postgres() -> None:
    subprocess.run(["psql", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", f"DROP DATABASE IF EXISTS {PG_DB} WITH (FORCE)"], cwd=ROOT, capture_output=True, text=True, check=True)
    subprocess.run(["psql", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", f"CREATE DATABASE {PG_DB}"], cwd=ROOT, capture_output=True, text=True, check=True)
    env = environment(PG_URL)
    run("postgres zero-to-head migration", ["python3", "-m", "alembic", "upgrade", "head"], env=env)
    run("postgres canonical seed", ["python3", "-m", "backend.app.seed.cli", "seed"], env=env)


def main() -> dict:
    steps: list[dict] = []
    sqlite_url = fresh_sqlite(ROOT / "pre_g10_reconcile.db")
    sqlite_env = environment(sqlite_url)
    steps.append(run("canonical fixture check", ["python3", "backend/scripts/canonical_fixture_check.py"], env=sqlite_env))
    steps.append(run("supported field/grid/rendering coverage", ["python3", "backend/scripts/supported_coverage_check.py"], env=sqlite_env))
    steps.append(run("SQLite backend regression", ["python3", "-m", "pytest", "-q", "backend/tests"], env=environment()))
    steps.append(run("Week 9 independent execution", ["python3", "backend/scripts/week9_independent_reconciliation.py"], env=environment()))

    gp1_url = fresh_sqlite(ROOT / "pre_g10_golden_path_v1.db")
    steps.append(run("Golden Path v1", ["python3", "backend/scripts/golden_path_v1.py"], env=environment(gp1_url)))
    steps.append(run("Golden Path v2", ["python3", "backend/scripts/golden_path_v2.py"], env=environment()))

    w11_url = fresh_sqlite(ROOT / "pre_g10_week11_12.db")
    steps.append(run("Weeks 11-12 independent execution", ["python3", "backend/scripts/week11_12_demo.py"], env=environment(w11_url)))
    steps.append(run("Weeks 13-14 acceptance rehearsal", ["python3", "backend/scripts/acceptance_rehearsal.py"], env=environment()))
    steps.append(run("frontend component tests", ["npm", "test", "--", "--run"], env=environment(), cwd=ROOT / "frontend"))
    steps.append(run("frontend production build", ["npm", "run", "build"], env=environment(), cwd=ROOT / "frontend"))
    steps.append(run("browser E2E", ["npm", "run", "browser-e2e"], env=environment(), cwd=ROOT / "frontend"))
    steps.append(run("registry and safety audit", ["python3", "backend/scripts/registry_and_safety_check.py"], env=environment()))

    fresh_postgres()
    pg_env = environment(PG_URL)
    steps.append(run("PostgreSQL canonical fixture check", ["python3", "backend/scripts/canonical_fixture_check.py"], env=pg_env))
    steps.append(run("PostgreSQL supported coverage", ["python3", "backend/scripts/supported_coverage_check.py"], env=pg_env))
    steps.append(run("PostgreSQL backend regression", ["python3", "-m", "pytest", "-q", "backend/tests"], env=pg_env))
    steps.append(run("PostgreSQL migration roundtrip downgrade", ["python3", "-m", "alembic", "downgrade", "base"], env=pg_env))
    steps.append(run("PostgreSQL migration roundtrip re-upgrade", ["python3", "-m", "alembic", "upgrade", "head"], env=pg_env))
    steps.append(run("PostgreSQL reseed after roundtrip", ["python3", "-m", "backend.app.seed.cli", "seed"], env=pg_env))
    steps.append(run("PostgreSQL fixture check after roundtrip", ["python3", "backend/scripts/canonical_fixture_check.py"], env=pg_env))

    result = {
        "status": "PASS",
        "evidence_class": "RETROACTIVE_EXECUTION_EVIDENCE",
        "track": "SYNTHETIC_DEVELOPMENT_PROTOTYPE",
        "postgresql": {"version": "16", "database": PG_DB, "url": PG_URL, "clean_migration": True, "roundtrip": True},
        "fixture": {"name": CANONICAL_FIXTURE_ID, "version": CANONICAL_FIXTURE_VERSION, "manifest_hash": CANONICAL_FIXTURE_MANIFEST_HASH},
        "steps": steps,
        "machine_final_submit": False,
        "live_ministry_write": False,
        "formal_g10": False,
    }
    Path("artifacts").mkdir(parents=True, exist_ok=True)
    Path("artifacts/pre-g10-reconciliation-result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
