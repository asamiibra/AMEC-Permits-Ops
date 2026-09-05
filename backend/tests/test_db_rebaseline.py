from __future__ import annotations

import ast
import importlib.util
import subprocess
from pathlib import Path

import pytest

from backend.app import db as database
from scripts.release.verify_a1_release_manifest import verify as verify_release_manifest


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "backend/migrations/versions/baseline_phase4_v36_azure_sql.py"
PHASE4 = ROOT / "backend/migrations/history/postgresql_accepted_v5_phase4_v35r1/phase4_corpus_app_integration.py"
ARCHIVE = ROOT / "backend/migrations/history/postgresql_r13_0001_0059"
SOURCE_SHA = "96c4b90968754efd8e5998cd1b1793b67c23d2bc"


def test_active_graph_and_legacy_archive_are_exact():
    assert sorted(path.name for path in (ROOT / "backend/migrations/versions").glob("*.py")) == [
        "baseline_phase4_v36_azure_sql.py",
        "step5_content_library_azure_sql_v2.py",
    ]
    phase4_source = PHASE4.read_text(encoding="utf-8")
    assert 'revision = "phase4_corpus_app_integration_v1"' in phase4_source
    assert 'down_revision = "baseline_r13_0059"' in phase4_source
    archived = sorted(ARCHIVE.glob("*.py"))
    assert len(archived) == 59
    for path in archived:
        source_path = f"{SOURCE_SHA}:backend/migrations/versions/{path.name}"
        expected = subprocess.check_output(["git", "rev-parse", source_path], cwd=ROOT, text=True).strip()
        actual = subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()
        assert actual == expected


def test_baseline_is_explicit_and_fail_closed():
    source = BASELINE.read_text(encoding="utf-8")
    assert 'revision = "baseline_phase4_v36_azure_sql"' in source
    assert "down_revision = None" in source
    assert "Azure SQL canonical root downgrade is intentionally unsupported" in source
    for marker in (
        "backend.app.models",
        "Base.metadata.create_all",
        "Base.metadata.drop_all",
        "sqlalchemy.dialects.postgresql",
        "CREATE TABLE",
        "DROP TABLE",
        " psql",
    ):
        assert marker not in source


def test_main_py_uses_only_dynamic_migration_readiness():
    source = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert "0059_entra_user_identity" not in source
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "verify_database_migration_head"
    ]
    assert len(calls) == 1
    assert '"failure_class": "MIGRATION_NOT_READY"' in source
    assert "MSSQL_SQLALCHEMY_SCHEME = \"mssql+pyodbc\"" in (ROOT / "backend/app/db.py").read_text(encoding="utf-8")


def _predeploy_manifest(head: str) -> dict:
    return {
        "repository": "asamiibra/AMEC-Permits-Ops",
        "source_sha": SOURCE_SHA,
        "stage": "PREDEPLOY",
        "azure": {"subscription_id": "61080f8b-16cb-4abc-bb8c-5d8e59ab15bf", "region": "qatarcentral"},
        "database": {"engine": "azure_sql", "major": 16, "migration_head": head},
        "entra": {"required_scope": "access_as_user", "requested_access_token_version": 2},
        "safety": {
            "app_env": "AZURE-PREPROD",
            "synthetic_only": True,
            "real_data_allowed": False,
            "storage_provider": "mock",
            "synology_mode": "SYNTHETIC",
            "azure_to_synology": False,
        },
    }


def test_release_contract_accepts_new_head_and_rejects_old_head():
    verify_release_manifest(_predeploy_manifest("baseline_phase4_v36_azure_sql"), SOURCE_SHA)
    with pytest.raises(ValueError, match="migration head"):
        verify_release_manifest(_predeploy_manifest("0059_entra_user_identity"), SOURCE_SHA)


def test_old_0059_database_head_fails_closed(monkeypatch):
    monkeypatch.setattr(database, "repository_migration_head", lambda: "step5_content_library_azure_sql_v2")
    monkeypatch.setattr(database, "database_migration_heads", lambda: ("baseline_phase4_v36_azure_sql",))
    with pytest.raises(RuntimeError, match="step5_content_library_azure_sql_v2"):
        database.verify_database_migration_head()


def test_root_downgrade_is_not_destructive():
    spec = importlib.util.spec_from_file_location("baseline_r13_0059", BASELINE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    with pytest.raises(RuntimeError, match="Azure SQL canonical root downgrade"):
        module.downgrade()
