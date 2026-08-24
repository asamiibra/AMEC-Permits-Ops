import ast
from pathlib import Path
import re
import tomllib

import pytest
from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, text as sqlalchemy_text
from sqlalchemy.dialects import mssql, postgresql
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import Settings
from backend.app.db import validate_mssql_connection_url
from backend.app.models import (
    ConsultancyOffice,
    AuditEvent,
    FieldDefinition,
    Phase4ClassifierCorrectionEvent,
    Phase4ClassificationEnvelope,
    Phase4ProjectionReceipt,
    Phase4ReviewDecision,
    Phase4SourceChangeEvent,
    PermitApplication,
    Project,
    VerifiedAssertion,
)
from backend.app.services.phase4 import ALLOWED_DECISIONS, _review_lock_statement
from scripts.db_azure_sql.sqlserver_gates import _migration_postgresql_physical_findings, _mssql_unique_constraints


MSSQL_TARGET = (
    "mssql+pyodbc://runtime:secret@proposalops.database.windows.net:1433/"
    "proposalops?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
)


def test_azure_sql_target_connection_contract_is_encrypted():
    validate_mssql_connection_url(MSSQL_TARGET, require_encryption=True)


@pytest.mark.parametrize(
    "url",
    [
        MSSQL_TARGET.replace("Encrypt=yes", "Encrypt=no"),
        MSSQL_TARGET.replace("TrustServerCertificate=no", "TrustServerCertificate=yes"),
    ],
)
def test_azure_sql_target_rejects_unsafe_tls(url):
    with pytest.raises(ValueError):
        validate_mssql_connection_url(url, require_encryption=True)


def test_settings_accepts_only_secure_mssql_target_for_azure_preprod(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    settings = Settings(
        app_env="AZURE-PREPROD",
        database_url=MSSQL_TARGET,
        frontend_origins="https://synthetic.example",
        synthetic_only=True,
        real_data_allowed=False,
        auth_mode="ENTRA",
        entra_tenant_id="11111111-1111-4111-8111-111111111111",
        entra_api_client_id="22222222-2222-4222-8222-222222222222",
        entra_web_client_id="33333333-3333-4333-8333-333333333333",
        storage_provider="mock",
        synology_mode="SYNTHETIC",
    )
    settings.validate_environment()


def _azure_preprod_settings(database_url: str) -> Settings:
    return Settings(
        app_env="AZURE-PREPROD",
        database_url=database_url,
        frontend_origins="https://synthetic.example",
        synthetic_only=True,
        real_data_allowed=False,
        auth_mode="ENTRA",
        entra_tenant_id="11111111-1111-4111-8111-111111111111",
        entra_api_client_id="22222222-2222-4222-8222-222222222222",
        entra_web_client_id="33333333-3333-4333-8333-333333333333",
        storage_provider="mock",
        synology_mode="SYNTHETIC",
    )


def test_azure_preprod_secure_mssql_accepted(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    _azure_preprod_settings(MSSQL_TARGET).validate_environment()


def test_azure_preprod_postgresql_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="mssql\\+pyodbc"):
        _azure_preprod_settings(
            "postgresql+psycopg://runtime:secret@db.example/proposalops"
        ).validate_environment()


def test_azure_preprod_sqlite_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="mssql\\+pyodbc"):
        _azure_preprod_settings("sqlite:///synthetic.db").validate_environment()


def test_azure_preprod_encrypt_no_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="Encrypt=yes"):
        _azure_preprod_settings(
            MSSQL_TARGET.replace("Encrypt=yes", "Encrypt=no")
        ).validate_environment()


def test_azure_preprod_trust_server_certificate_yes_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="TrustServerCertificate=no"):
        _azure_preprod_settings(
            MSSQL_TARGET.replace(
                "TrustServerCertificate=no", "TrustServerCertificate=yes"
            )
        ).validate_environment()


def test_phase4_has_exactly_six_review_actions_and_no_advisory_lock():
    assert ALLOWED_DECISIONS == {
        "ACCEPT",
        "CORRECT",
        "DEFER",
        "MARK_OUT_OF_SCOPE",
        "RESOLVE_RELATIONSHIP",
        "REJECT",
    }
    source = Path("backend/app/services/phase4.py").read_text(encoding="utf-8")
    assert "pg_advisory_xact_lock" not in source


def test_active_migration_is_one_azure_sql_root_and_fails_closed_on_downgrade():
    active = sorted(Path("backend/migrations/versions").glob("*.py"))
    assert [path.name for path in active] == ["baseline_phase4_v36_azure_sql.py"]
    source = active[0].read_text(encoding="utf-8")
    assert 'revision = "baseline_phase4_v36_azure_sql"' in source
    assert "down_revision = None" in source
    assert "ON CONFLICT" not in source
    assert "Base.metadata.create_all" not in source


def test_sqlserver_driver_dependency_metadata_consistent():
    root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((root / "backend/pyproject.toml").read_text(encoding="utf-8"))
    project_dependencies = pyproject["project"]["dependencies"]
    pyproject_matches = [item for item in project_dependencies if item.startswith("pyodbc")]
    assert len(pyproject_matches) == 1
    assert pyproject_matches[0] == "pyodbc==5.3.0"

    def requirement_matches(path: Path) -> list[str]:
        return re.findall(r"^pyodbc==([^\s\\]+)", path.read_text(encoding="utf-8"), re.MULTILINE)

    requirements_matches = requirement_matches(root / "backend/requirements.txt")
    runtime_matches = requirement_matches(root / "backend/requirements-runtime.txt")
    lock_matches = requirement_matches(root / "backend/requirements-runtime.lock")
    assert requirements_matches == ["5.3.0"]
    assert runtime_matches == ["5.3.0"]
    assert lock_matches == ["5.3.0"]

    dockerfile = (root / "backend/Dockerfile").read_text(encoding="utf-8")
    assert "COPY backend/requirements-runtime.lock /tmp/requirements-runtime.lock" in dockerfile
    assert "--require-hashes -r /tmp/requirements-runtime.lock" in dockerfile
    print("PYPROJECT_PYODBC_DECLARATION_COUNT=1")
    print("PYPROJECT_PYODBC_EXACT=pyodbc==5.3.0")
    print("REQUIREMENTS_TXT_PYODBC_DECLARATION_COUNT=1")
    print("REQUIREMENTS_TXT_PYODBC_EXACT=pyodbc==5.3.0")
    print("RUNTIME_TXT_PYODBC_DECLARATION_COUNT=1")
    print("RUNTIME_TXT_PYODBC_EXACT=pyodbc==5.3.0")
    print("RUNTIME_LOCK_PYODBC_VERSION=5.3.0")
    print("SQLSERVER_DRIVER_DEPENDENCY_METADATA_PARITY=PASS")


def test_sqlserver_gate_model_constructor_keywords_match_sqlalchemy_mappers():
    source = Path("scripts/db_azure_sql/sqlserver_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="scripts/db_azure_sql/sqlserver_gates.py")
    models = {
        "ConsultancyOffice": ConsultancyOffice,
        "Project": Project,
        "PermitApplication": PermitApplication,
        "FieldDefinition": FieldDefinition,
        "VerifiedAssertion": VerifiedAssertion,
    }
    constructor_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in models
    ]
    invalid_keywords = []
    for call in constructor_calls:
        mapped_names = set(sqlalchemy_inspect(models[call.func.id]).attrs.keys())
        for keyword in call.keywords:
            if keyword.arg is None or keyword.arg not in mapped_names:
                invalid_keywords.append((call.func.id, keyword.arg, call.lineno))
    assert constructor_calls
    assert invalid_keywords == []
    print(f"SQLSERVER_GATE_MODEL_CONSTRUCTOR_CALL_COUNT={len(constructor_calls)}")
    print(f"SQLSERVER_GATE_INVALID_MODEL_CONSTRUCTOR_KWARG_COUNT={len(invalid_keywords)}")
    print("SQLSERVER_GATE_MODEL_CONSTRUCTOR_MAPPER_AUDIT=PASS")


def test_sqlserver_gate_fixture_flushes_before_verified_assertion():
    source = Path("scripts/db_azure_sql/sqlserver_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="scripts/db_azure_sql/sqlserver_gates.py")
    fixture = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_fixture"
    )
    add_all_calls = [
        node
        for node in ast.walk(fixture)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_all"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "db"
    ]
    flush_calls = [
        node
        for node in ast.walk(fixture)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "flush"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "db"
    ]
    assertion_calls = [
        node
        for node in ast.walk(fixture)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "VerifiedAssertion"
    ]
    assert add_all_calls and flush_calls and assertion_calls
    add_all = min(add_all_calls, key=lambda node: node.lineno)
    flush = min(flush_calls, key=lambda node: node.lineno)
    assertion = min(assertion_calls, key=lambda node: node.lineno)
    assert any(isinstance(node, ast.Name) and node.id == "field" for node in ast.walk(add_all))
    assert add_all.lineno < flush.lineno < assertion.lineno
    print("SQLSERVER_GATE_FIXTURE_FLUSH_BEFORE_ASSERTION=true")


def test_sqlserver_gate_text_literals_have_no_implicit_bind_parameters():
    source = Path("scripts/db_azure_sql/sqlserver_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="scripts/db_azure_sql/sqlserver_gates.py")
    literal_calls = []
    nonliteral_calls = []
    implicit_bind_parameters = []
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        is_text_call = isinstance(call.func, ast.Name) and call.func.id == "text"
        is_text_call = is_text_call or (isinstance(call.func, ast.Attribute) and call.func.attr == "text")
        if not is_text_call:
            continue
        if len(call.args) != 1 or not isinstance(call.args[0], ast.Constant) or not isinstance(call.args[0].value, str):
            nonliteral_calls.append(call.lineno)
            continue
        literal = call.args[0].value
        literal_calls.append(call.lineno)
        statement = sqlalchemy_text(literal)
        implicit_bind_parameters.extend((call.lineno, name) for name in statement._bindparams)
    assert literal_calls
    assert nonliteral_calls == []
    assert implicit_bind_parameters == []
    print(f"SQLSERVER_GATE_TEXT_LITERAL_CALL_COUNT={len(literal_calls)}")
    print("SQLSERVER_GATE_TEXT_NONLITERAL_CALL_COUNT=0")
    print("SQLSERVER_GATE_TEXT_IMPLICIT_BIND_PARAMETER_COUNT=0")
    print("SQLSERVER_GATE_TEXT_LITERAL_AUDIT=PASS")


def test_sqlserver_gate_model_attribute_references_match_sqlalchemy_mappers():
    source = Path("scripts/db_azure_sql/sqlserver_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="scripts/db_azure_sql/sqlserver_gates.py")
    models = {
        "AuditEvent": AuditEvent,
        "Phase4SourceChangeEvent": Phase4SourceChangeEvent,
        "Phase4ClassificationEnvelope": Phase4ClassificationEnvelope,
        "Phase4ReviewDecision": Phase4ReviewDecision,
        "Phase4ClassifierCorrectionEvent": Phase4ClassifierCorrectionEvent,
        "Phase4ProjectionReceipt": Phase4ProjectionReceipt,
        "VerifiedAssertion": VerifiedAssertion,
    }
    references = []
    invalid = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        model_name = node.value.id
        if model_name not in models or (model_name == "Base" and node.attr == "metadata"):
            continue
        references.append((model_name, node.attr, node.lineno))
        if node.attr not in sqlalchemy_inspect(models[model_name]).attrs:
            invalid.append((model_name, node.attr, node.lineno))
    assert references
    assert invalid == []
    print(f"SQLSERVER_GATE_MODEL_ATTRIBUTE_REFERENCE_COUNT={len(references)}")
    print("SQLSERVER_GATE_INVALID_MODEL_ATTRIBUTE_REFERENCE_COUNT=0")
    print("SQLSERVER_GATE_MODEL_ATTRIBUTE_MAPPER_AUDIT=PASS")


def test_phase4_review_lock_compiles_sqlserver_update_holdlock():
    sqlserver_statement = _review_lock_statement("envelope-1", "mssql")
    fallback_statement = _review_lock_statement("envelope-1", "postgresql")
    sqlserver_sql = str(sqlserver_statement.compile(dialect=mssql.dialect()))
    fallback_sql = str(fallback_statement.compile(dialect=postgresql.dialect()))
    upper_sqlserver = sqlserver_sql.upper()
    assert "WITH (UPDLOCK, ROWLOCK, HOLDLOCK)" in upper_sqlserver
    assert "FOR UPDATE" not in upper_sqlserver
    assert "FOR UPDATE" in fallback_sql.upper()
    assert sqlserver_statement.get_execution_options()["populate_existing"] is True
    assert fallback_statement.get_execution_options()["populate_existing"] is True
    print("PHASE4_MSSQL_REVIEW_LOCK_UPDLOCK=true")
    print("PHASE4_MSSQL_REVIEW_LOCK_ROWLOCK=true")
    print("PHASE4_MSSQL_REVIEW_LOCK_HOLDLOCK=true")
    print("PHASE4_MSSQL_REVIEW_LOCK_FOR_UPDATE=false")
    print("PHASE4_NON_MSSQL_REVIEW_LOCK_FALLBACK=true")
    print("PHASE4_REVIEW_LOCK_POPULATE_EXISTING=true")


def test_phase4_review_lock_refreshes_preloaded_identity_state(tmp_path):
    sqlite_engine = create_engine(f"sqlite:///{tmp_path / 'identity-refresh.db'}")
    Phase4ClassificationEnvelope.__table__.create(sqlite_engine)
    SessionFactory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    envelope_id = "identity-refresh-envelope"
    with SessionFactory() as seed:
        seed.add(
            Phase4ClassificationEnvelope(
                id=envelope_id,
                envelope_id="identity-refresh-envelope-key",
                root_event_id="identity-refresh-event",
                source_mode="CONTROLLED_SYNTHETIC",
                classifier_version="test-v1",
                rules_version="test-v1",
                taxonomy_revision="test-v1",
                module_truth_contract_sha="a" * 64,
                corpus_app_contract_sha="b" * 64,
                axes_json={"scope": {"scope_type": "PROJECT", "scope_id": "identity-refresh-project"}},
                immutable_result_hash="c" * 64,
                record_version=1,
                status="PENDING_REVIEW",
            )
        )
        seed.commit()

    session_a = SessionFactory()
    session_b = SessionFactory()
    try:
        preloaded = session_a.get(Phase4ClassificationEnvelope, envelope_id)
        assert preloaded is not None
        assert preloaded.record_version == 1
        changed = session_b.get(Phase4ClassificationEnvelope, envelope_id)
        assert changed is not None
        changed.record_version = 2
        session_b.commit()
        refreshed = session_a.scalar(_review_lock_statement(envelope_id, "sqlite"))
        assert refreshed is preloaded
        assert refreshed.record_version == 2
        assert preloaded.record_version == 2
    finally:
        session_a.close()
        session_b.close()
        sqlite_engine.dispose()
    print("PHASE4_PRELOADED_IDENTITY_REFRESH_REGRESSION=PASS")


def test_active_migration_provenance_text_not_counted_as_postgresql_physical_dependency():
    active = Path("backend/migrations/versions/baseline_phase4_v36_azure_sql.py").read_text(encoding="utf-8")
    active_findings = _migration_postgresql_physical_findings(active)
    docstring_only = _migration_postgresql_physical_findings(
        '"""PostgreSQL provenance includes ON CONFLICT and ::uuid historical text."""\n'
    )
    synthetic_import = _migration_postgresql_physical_findings(
        "import sqlalchemy.dialects.postgresql as postgresql\n"
    )
    synthetic_conflict = _migration_postgresql_physical_findings(
        'def upgrade():\n    op.execute("INSERT INTO t VALUES (1) ON CONFLICT (id) DO NOTHING")\n'
    )
    assert len(active_findings) == 0
    assert len(docstring_only) == 0
    assert len(synthetic_import) >= 1
    assert len(synthetic_conflict) >= 1
    print("ACTIVE_MIGRATION_POSTGRESQL_PHYSICAL_FINDING_COUNT=0")
    print("ACTIVE_MIGRATION_PROVENANCE_DOCSTRING_FINDING_COUNT=0")
    print("SYNTHETIC_POSTGRESQL_IMPORT_FINDING_COUNT_GE_1=true")
    print("SYNTHETIC_ON_CONFLICT_FINDING_COUNT_GE_1=true")
    print("ACTIVE_MIGRATION_PROVENANCE_ANALYZER_AUDIT=PASS")


def test_sqlserver_gate_reflection_methods_are_mssql_implemented():
    source = Path("scripts/db_azure_sql/sqlserver_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="scripts/db_azure_sql/sqlserver_gates.py")
    inspector_variables = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if isinstance(node.value.func, ast.Name) and node.value.func.id == "inspect":
            inspector_variables.update(target.id for target in node.targets if isinstance(target, ast.Name))

    methods = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or not node.func.attr.startswith("get_"):
            continue
        value = node.func.value
        direct_inspector = isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "inspect"
        assigned_inspector = isinstance(value, ast.Name) and value.id in inspector_variables
        if direct_inspector or assigned_inspector:
            methods.add(node.func.attr)

    expected = {"get_table_names", "get_pk_constraint", "get_foreign_keys", "get_indexes", "get_columns"}
    unsupported = []
    for method in sorted(methods):
        owner = next((candidate for candidate in mssql.dialect.mro() if method in candidate.__dict__), None)
        if owner in {Dialect, DefaultDialect} or owner is None or not owner.__module__.startswith("sqlalchemy.dialects.mssql"):
            unsupported.append((method, owner.__module__ if owner else None))
    assert methods == expected
    assert "get_unique_constraints" not in methods
    assert unsupported == []
    print("SQLSERVER_GATE_INSPECTOR_METHOD_COUNT=5")
    print("SQLSERVER_GATE_GET_UNIQUE_CONSTRAINTS_CALL_COUNT=0")
    print("SQLSERVER_GATE_UNSUPPORTED_INSPECTOR_METHOD_COUNT=0")
    print("SQLSERVER_GATE_MSSQL_REFLECTION_API_AUDIT=PASS")


def test_mssql_unique_constraint_catalog_helper_is_parameterized_and_exact():
    class FakeResult:
        def all(self):
            return [
                {"name": "uq_phase4_review_decision_idempotency", "column_name": "idempotency_key", "key_ordinal": 1},
                {"name": "uq_catalog_order", "column_name": "second", "key_ordinal": 2},
                {"name": "uq_catalog_order", "column_name": "first", "key_ordinal": 1},
            ]

    class FakeConnection:
        def __init__(self):
            self.statement = None
            self.parameters = None

        def exec_driver_sql(self, statement, parameters):
            self.statement = statement
            self.parameters = parameters
            return FakeResult()

    connection = FakeConnection()
    result = _mssql_unique_constraints(connection, "phase4_review_decisions")
    expected = {"name": "uq_phase4_review_decision_idempotency", "column_names": ["idempotency_key"]}
    assert connection.statement is not None
    assert connection.parameters == (None, "phase4_review_decisions")
    assert connection.statement.count("?") >= 2
    assert "sys.key_constraints" in connection.statement
    assert "key_ordinal" in connection.statement
    assert "phase4_review_decisions" not in connection.statement
    assert expected in result
    assert next(item for item in result if item["name"] == "uq_catalog_order")["column_names"] == ["first", "second"]
    print("MSSQL_UNIQUE_CATALOG_HELPER_UNIT=PASS")
    print("MSSQL_UQ_HELPER_USES_EXEC_DRIVER_SQL=true")
    print("MSSQL_UQ_HELPER_QMARK_PARAMETER_COUNT=2")
    print("MSSQL_UQ_HELPER_SYS_KEY_CONSTRAINTS=true")
    print("MSSQL_UQ_HELPER_PRESERVES_KEY_ORDINAL=true")


def test_sqlserver_gate_azsql025_is_deterministic_and_conflict_exact():
    source = Path("scripts/db_azure_sql/sqlserver_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="scripts/db_azure_sql/sqlserver_gates.py")
    runtime_gates = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "runtime_gates")
    decision_worker = next(node for node in ast.walk(runtime_gates) if isinstance(node, ast.FunctionDef) and node.name == "decision_worker")

    barrier_calls = [
        node
        for node in ast.walk(runtime_gates)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Barrier"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == 2
    ]
    preload_calls = [
        node
        for node in ast.walk(decision_worker)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and any(isinstance(argument, ast.Name) and argument.id == "Phase4ClassificationEnvelope" for argument in node.args)
    ]
    barrier_waits = [
        node
        for node in ast.walk(decision_worker)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "wait"
    ]
    service_calls = [
        node
        for node in ast.walk(decision_worker)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "record_review_decision"
    ]
    assert barrier_calls
    assert preload_calls and barrier_waits and service_calls
    assert min(node.lineno for node in preload_calls) < min(node.lineno for node in barrier_waits) < min(node.lineno for node in service_calls)

    def has_len_equals(name: str, expected: int) -> bool:
        return any(
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "len"
            and node.left.args
            and isinstance(node.left.args[0], ast.Name)
            and node.left.args[0].id == name
            and any(isinstance(comparator, ast.Constant) and comparator.value == expected for comparator in node.comparators)
            for node in ast.walk(runtime_gates)
        )

    def has_name_equals(name: str, expected: object) -> bool:
        return any(
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Name)
            and node.left.id == name
            and any(isinstance(comparator, ast.Constant) and comparator.value == expected for comparator in node.comparators)
            for node in ast.walk(runtime_gates)
        )

    constants = {node.value for node in ast.walk(runtime_gates) if isinstance(node, ast.Constant)}
    assert "CLASSIFICATION_RECORD_VERSION_CONFLICT" in constants
    assert 409 in constants
    assert has_len_equals("successes", 1)
    assert has_len_equals("conflicts", 1)
    assert has_len_equals("stored_decisions", 1)
    assert has_name_equals("final_envelope_record_version", 2)
    print("AZSQL025_SOURCE_SHAPE_REGRESSION=PASS")
