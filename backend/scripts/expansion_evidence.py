"""Generate machine-readable E0/E1 evidence from executed commands.

The result records return codes and output tails; status is never supplied as
an asserted constant.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from backend.app.expansion.fixture import expanded_fixture_metadata
from backend.app.expansion.governance import validate_governance
from backend.app.fixtures.canonical import fixture_metadata

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def run(label: str, args: list[str], env_overrides: dict[str, str] | None = None, cwd: Path | None = None) -> dict:
    env = os.environ.copy()
    env.update({"PYTHONPATH": ".", "APP_ENV": "TEST", "SYNTHETIC_ONLY": "true"})
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(args, cwd=cwd or ROOT, env=env, capture_output=True, text=True)
    return {"label": label, "command": " ".join(args), "returncode": result.returncode, "status": "PASS" if result.returncode == 0 else "FAIL", "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-1000:]}


def main() -> None:
    pg_url = os.environ.get("EXPANSION_PG_URL", "postgresql+psycopg://ahmedsami@localhost:5432/permitops_expansion_e1")
    sqlite_url = f"sqlite:////tmp/permitops_expansion_evidence_{os.getpid()}.db"
    golden_v1_url = f"sqlite:////tmp/permitops_golden_path_v1_{os.getpid()}.db"
    sqlite_migration = run("SQLite migration", [PYTHON, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], {"DATABASE_URL": sqlite_url})
    pg_migration = run("PostgreSQL migration", [PYTHON, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], {"DATABASE_URL": pg_url})
    pg_seed = run("PostgreSQL clean synthetic seed", [PYTHON, "-m", "backend.app.seed.cli", "seed"], {"DATABASE_URL": pg_url})
    core = run("permit-core SQLite regression", [PYTHON, "-m", "pytest", "-q", "backend/tests", "--ignore=backend/tests/test_expansion_e0_e1.py"], {"DATABASE_URL": sqlite_url})
    e1_sqlite = run("full SQLite regression", [PYTHON, "-m", "pytest", "-q", "backend/tests"], {"DATABASE_URL": sqlite_url})
    e1_pg = run("PostgreSQL regression", [PYTHON, "-m", "pytest", "-q", "backend/tests"], {"DATABASE_URL": pg_url})
    fixture = run("expanded fixture check", [PYTHON, "backend/scripts/expansion_fixture_check.py"], {"DATABASE_URL": pg_url})
    canonical = run("canonical permit fixture", [PYTHON, "backend/scripts/canonical_fixture_check_runner.py"], {"DATABASE_URL": sqlite_url})
    golden_v1 = run("Golden Path v1", [PYTHON, "backend/scripts/golden_path_v1.py"], {"DATABASE_URL": golden_v1_url})
    golden_v2 = run("Golden Path v2", [PYTHON, "backend/scripts/golden_path_v2.py"], {"DATABASE_URL": sqlite_url})
    acceptance = run("Weeks 13-14 acceptance rehearsal", [PYTHON, "backend/scripts/acceptance_rehearsal.py"], {"DATABASE_URL": sqlite_url})
    e3_e4 = run("E3/E4 Golden Path 0", [PYTHON, "backend/scripts/e3_e4_golden_path.py"], {"DATABASE_URL": sqlite_url})
    e5_e6 = run("E5/E6 bounded Golden Paths", [PYTHON, "backend/scripts/e5_e6_golden_paths.py"], {"DATABASE_URL": sqlite_url})
    e5_e6_tests = run("E5/E6 focused contract tests", [PYTHON, "-m", "pytest", "-q", "backend/tests/test_e5_e6_bounded_workflows.py"], {"DATABASE_URL": sqlite_url})
    e7_e8 = run("E7/E8 unified acceptance", [PYTHON, "backend/scripts/e7_e8_acceptance.py"], {"DATABASE_URL": sqlite_url})
    e7_e8_tests = run("E7/E8 focused contract tests", [PYTHON, "-m", "pytest", "-q", "backend/tests/test_e7_e8_unified_acceptance.py"], {"DATABASE_URL": sqlite_url})
    frontend_test = run("frontend component tests", ["npm", "test", "--", "--run"], cwd=ROOT / "frontend")
    frontend_build = run("frontend production build", ["npm", "run", "build"], cwd=ROOT / "frontend")
    browser = run("browser E2E", ["npm", "run", "browser-e2e"], cwd=ROOT / "frontend")
    safety = run("registry and safety", [PYTHON, "backend/scripts/registry_and_safety_check.py"], {"DATABASE_URL": sqlite_url})
    migration = run("Alembic head", [PYTHON, "-m", "alembic", "heads"], {"DATABASE_URL": pg_url})
    results = [sqlite_migration, pg_migration, pg_seed, core, e1_sqlite, e1_pg, fixture, canonical, golden_v1, golden_v2, acceptance, e3_e4, e5_e6, e5_e6_tests, e7_e8, e7_e8_tests, frontend_test, frontend_build, browser, safety, migration]
    all_pass = all(item["status"] == "PASS" for item in results)
    fixture_meta = expanded_fixture_metadata()
    governance = validate_governance()
    safety_json = json.loads(safety["stdout_tail"])
    safety_counters = safety_json["safety"]["counters"]
    fixture_json = json.loads(fixture["stdout_tail"])
    artifact = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all_pass else "FAIL",
        "migration_head": migration["stdout_tail"].strip().split()[0] if migration["stdout_tail"].strip() else "UNKNOWN",
        "fixture_name": fixture_meta["fixture_set"],
        "fixture_version": fixture_meta["fixture_version"],
        "fixture_hash": fixture_meta["fixture_manifest_hash"],
        "a12_count": len(yaml.safe_load((ROOT / "config/recording_fidelity_requirements_v2_5.yaml").read_text(encoding="utf-8"))["requirements"]),
        "a12b_count": governance["a12b_count"],
        "a15_count": governance["a15_count"],
        "commands": results,
        "safety": safety_counters,
    }
    Path("artifacts/expansion").mkdir(parents=True, exist_ok=True)
    canonical_meta = fixture_metadata()
    e0_artifact = {**artifact, "phase": "E0_BASELINE_PROTECTED", "migration_head": "0015_week14_acceptance", "fixture_name": canonical_meta["fixture_set"], "fixture_version": canonical_meta["fixture_version"], "fixture_hash": canonical_meta["fixture_manifest_hash"], "permit_core_regression": core, "commands": [core, canonical, golden_v1, golden_v2, acceptance, frontend_test, frontend_build, browser, safety]}
    Path("artifacts/expansion/e0-baseline-regression.json").write_text(json.dumps(e0_artifact, indent=2, sort_keys=True), encoding="utf-8")
    Path("artifacts/expansion/e1-regression-result.json").write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    Path("artifacts/expansion/e1-expanded-fixture-result.json").write_text(json.dumps(fixture_json, indent=2, sort_keys=True), encoding="utf-8")
    Path("artifacts/expansion/e1-safety-counters.json").write_text(json.dumps({"status": safety_json["safety"]["status"], "counters": safety_counters, "machine_final_submit_capability": safety_json["safety"]["machine_final_submit_capability"], "forbidden_routes": safety_json["safety"]["forbidden_routes"], "secret_hits": safety_json["safety"]["secret_hits"], "source_hits": safety_json["safety"]["source_hits"]}, indent=2, sort_keys=True), encoding="utf-8")
    Path("artifacts/expansion/e8-final-regression-result.json").write_text(json.dumps({"status": "PASS" if all_pass else "FAIL", "commands": results, "backend_focus": e7_e8_tests, "browser": browser, "build": frontend_build, "timestamp": artifact["timestamp"]}, indent=2, sort_keys=True), encoding="utf-8")
    Path("artifacts/expansion/e8-final-browser-acceptance.json").write_text(json.dumps({"status": browser["status"], "command": browser["command"], "meaningful_scenarios_minimum": 24, "browser_run": browser, "timestamp": artifact["timestamp"]}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
