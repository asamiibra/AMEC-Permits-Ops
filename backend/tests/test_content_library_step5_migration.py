from __future__ import annotations

import ast
import importlib.util

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = "backend/migrations/versions/step5_content_library_azure_sql_v1.py"


def _migration_module():
    spec = importlib.util.spec_from_file_location("content_library_step5_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_step5_migration_is_single_azure_lineage_delta_without_dml():
    module = _migration_module()
    assert module.revision == "step5_content_library_azure_sql_v1"
    assert module.down_revision == "baseline_phase4_v36_azure_sql"
    source = open(MIGRATION_PATH, encoding="utf-8").read()
    tree = ast.parse(source)
    dml_calls = {
        node.func.attr.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr.lower() in {"insert", "update", "delete", "merge", "execute"}
    }
    assert dml_calls == set()


def test_step5_migration_is_online_idempotent_for_draft_apply_shape():
    module = _migration_module()
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE form_instances (id VARCHAR(36) PRIMARY KEY)"))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            module.upgrade()
            module.upgrade()
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("form_instances")}
        indexes = {index["name"] for index in inspector.get_indexes("form_instance_apply_commands")}
        assert {
            "field_provenance_json",
            "field_citations_json",
            "field_write_metadata_json",
            "draft_revision",
            "last_applied_preview_fingerprint",
            "last_applied_by",
            "last_applied_at",
        } <= columns
        assert "form_instance_apply_commands" in inspector.get_table_names()
        assert {
            "ix_form_instance_apply_form_instance",
            "ix_form_instance_apply_commands_project_id",
        } <= indexes
