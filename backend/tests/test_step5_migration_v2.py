import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[2]
V2_PATH = ROOT / "backend/migrations/versions/step5_content_library_azure_sql_v2.py"


def _load_v2():
    spec = importlib.util.spec_from_file_location("step5_content_library_azure_sql_v2", V2_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _CatalogResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return list(self.values)


class _FakeBind:
    class _Preparer:
        def quote_schema(self, value):
            return f"[{value}]"

        def quote(self, value):
            return f"[{value}]"

    dialect = SimpleNamespace(name="mssql", identifier_preparer=_Preparer())

    def __init__(self, catalog_values):
        self.catalog_values = iter(catalog_values)
        self.executed = []

    def execute(self, statement, params):
        assert params["schema_name"] == "dbo"
        assert params["table_name"] == "form_instances"
        return _CatalogResult(next(self.catalog_values))

    def exec_driver_sql(self, statement):
        self.executed.append(statement)


def test_mssql_default_constraint_drop_requires_exactly_one_and_reproves_zero():
    v2 = _load_v2()
    bind = _FakeBind([["DF_form_instances_field"], []])

    v2._drop_mssql_temporary_default(bind, "field_provenance_json")

    assert bind.executed == [
        "ALTER TABLE [dbo].[form_instances] DROP CONSTRAINT [DF_form_instances_field]"
    ]


def test_mssql_default_constraint_drop_fails_closed_on_ambiguous_catalog():
    v2 = _load_v2()
    bind = _FakeBind([["DF_one", "DF_two"]])

    with pytest.raises(RuntimeError, match="STEP5_MSSQL_DEFAULT_CONSTRAINT_COUNT_INVALID"):
        v2._drop_mssql_temporary_default(bind, "field_provenance_json")

    assert bind.executed == []


def test_upgrade_rejects_preexisting_partial_state_before_any_ddl(monkeypatch):
    v2 = _load_v2()

    class Inspector:
        def get_table_names(self, schema=None):
            return ["form_instances"]

        def get_columns(self, table_name, schema=None):
            return [{"name": "field_provenance_json"}]

    bind = _FakeBind([])
    monkeypatch.setattr(v2.sa, "inspect", lambda _bind: Inspector())
    monkeypatch.setattr(v2.op, "get_bind", lambda: bind)

    with pytest.raises(RuntimeError, match="STEP5_PREEXISTING_PARTIAL_SCHEMA_STATE"):
        v2.upgrade()

    assert bind.executed == []


def test_sqlite_structural_migration_has_exact_step5_objects_and_indexes():
    v2 = _load_v2()
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE form_instances (id VARCHAR(36) PRIMARY KEY)")
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            v2.upgrade()

        database = inspect(connection)
        columns = {item["name"] for item in database.get_columns("form_instances")}
        assert columns >= {name for name, _type, _default in v2.FORM_INSTANCE_COLUMNS}
        assert "form_instance_apply_commands" in database.get_table_names()
        indexes = {item["name"] for item in database.get_indexes("form_instance_apply_commands")}
        assert indexes == {
            "ix_form_instance_apply_form_instance",
            "ix_form_instance_apply_commands_project_id",
        }
        constraints = database.get_unique_constraints("form_instance_apply_commands")
        assert {item["name"] for item in constraints} == {
            "uq_form_instance_apply_idempotency"
        }
        foreign_keys = database.get_foreign_keys("form_instance_apply_commands")
        assert len(foreign_keys) == 1
        assert foreign_keys[0]["referred_table"] == "form_instances"
