import ast
import inspect
from types import SimpleNamespace

import pytest

from backend.app.seed import cli as seed_cli


def _settings(
    *,
    app_env: str = "AZURE-PREPROD",
    synthetic_only: bool = True,
    real_data_allowed: bool = False,
):
    return SimpleNamespace(
        app_env=app_env,
        synthetic_only=synthetic_only,
        real_data_allowed=real_data_allowed,
    )


def _install_settings(monkeypatch, **kwargs):
    settings = _settings(**kwargs)
    monkeypatch.setattr(
        seed_cli,
        "get_settings",
        lambda: settings,
    )
    return settings


def test_seed_safe_mode_signature_defaults_are_preserved():
    signature = inspect.signature(seed_cli.seed)

    assert signature.parameters["initialize_schema"].default is True
    assert signature.parameters["reset_existing"].default is True
    assert signature.parameters["clean_fixtures"].default is True


def test_prod_seed_is_forbidden_before_schema_or_session_side_effects(
    monkeypatch,
):
    _install_settings(
        monkeypatch,
        app_env="PROD",
    )

    monkeypatch.setattr(
        seed_cli,
        "init_db",
        lambda: pytest.fail("init_db must not run in PROD"),
    )
    monkeypatch.setattr(
        seed_cli,
        "SessionLocal",
        lambda: pytest.fail("SessionLocal must not open in PROD"),
    )

    with pytest.raises(
        RuntimeError,
        match="forbidden in PROD",
    ):
        seed_cli.seed()


@pytest.mark.parametrize(
    (
        "settings_kwargs",
        "call_kwargs",
        "message",
    ),
    [
        (
            {"synthetic_only": False},
            {
                "initialize_schema": False,
                "reset_existing": False,
                "clean_fixtures": False,
            },
            "SYNTHETIC_ONLY",
        ),
        (
            {"real_data_allowed": True},
            {
                "initialize_schema": False,
                "reset_existing": False,
                "clean_fixtures": False,
            },
            "REAL_DATA_ALLOWED",
        ),
        (
            {},
            {
                "initialize_schema": True,
                "reset_existing": False,
                "clean_fixtures": False,
            },
            "initialize_schema=False",
        ),
        (
            {},
            {
                "initialize_schema": False,
                "reset_existing": True,
                "clean_fixtures": False,
            },
            "reset_existing=False",
        ),
        (
            {},
            {
                "initialize_schema": False,
                "reset_existing": False,
                "clean_fixtures": True,
            },
            "clean_fixtures=False",
        ),
    ],
)
def test_azure_preprod_rejects_every_unsafe_seed_mode(
    monkeypatch,
    settings_kwargs,
    call_kwargs,
    message,
):
    _install_settings(
        monkeypatch,
        **settings_kwargs,
    )

    monkeypatch.setattr(
        seed_cli,
        "init_db",
        lambda: pytest.fail("init_db must not run for rejected Azure mode"),
    )
    monkeypatch.setattr(
        seed_cli,
        "SessionLocal",
        lambda: pytest.fail("SessionLocal must not open for rejected Azure mode"),
    )

    with pytest.raises(
        RuntimeError,
        match=message,
    ):
        seed_cli.seed(**call_kwargs)


@pytest.mark.parametrize(
    "app_env",
    [
        "DEV",
        "TEST",
    ],
)
def test_non_destructive_mode_is_not_available_outside_azure_preprod(
    monkeypatch,
    app_env,
):
    _install_settings(
        monkeypatch,
        app_env=app_env,
    )

    with pytest.raises(
        RuntimeError,
        match="restricted to AZURE-PREPROD",
    ):
        seed_cli.seed(
            initialize_schema=False,
            reset_existing=False,
            clean_fixtures=False,
        )


def test_delete_helper_is_noop_when_disabled():
    class FakeDb:
        def execute(self, statement):
            pytest.fail("delete must not execute when disabled")

    seed_cli._delete_seed_models(
        FakeDb(),
        [seed_cli.User],
        enabled=False,
    )


def test_delete_helper_executes_only_when_enabled():
    calls = []

    class FakeDb:
        def execute(self, statement):
            calls.append(statement)

    seed_cli._delete_seed_models(
        FakeDb(),
        [seed_cli.User],
        enabled=True,
    )

    assert len(calls) == 1


def _function_ast(name: str) -> ast.FunctionDef:
    module = ast.parse(
        inspect.getsource(seed_cli)
    )

    for node in module.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == name
        ):
            return node

    raise AssertionError(
        f"Function {name} was not found"
    )


def _calls_named(
    function: ast.FunctionDef,
    name: str,
):
    matches = []

    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue

        called = node.func

        if (
            isinstance(called, ast.Name)
            and called.id == name
        ):
            matches.append(node)

    return matches


def _keyword_is_name(
    call: ast.Call,
    keyword: str,
    expected_name: str,
) -> bool:
    for item in call.keywords:
        if item.arg != keyword:
            continue

        return (
            isinstance(item.value, ast.Name)
            and item.value.id == expected_name
        )

    return False


def test_seed_propagates_reset_flag_to_week2_and_week3():
    function = _function_ast("seed")

    week2 = _calls_named(
        function,
        "seed_week2",
    )
    week3 = _calls_named(
        function,
        "seed_week3",
    )

    assert len(week2) == 1
    assert len(week3) == 1

    assert _keyword_is_name(
        week2[0],
        "reset_existing",
        "reset_existing",
    )
    assert _keyword_is_name(
        week3[0],
        "reset_existing",
        "reset_existing",
    )


def test_week2_and_week3_destructive_resets_are_guarded():
    for function_name in (
        "seed_week2",
        "seed_week3",
    ):
        function = _function_ast(
            function_name
        )

        guarded = _calls_named(
            function,
            "_delete_seed_models",
        )

        assert len(guarded) == 1
        assert _keyword_is_name(
            guarded[0],
            "enabled",
            "reset_existing",
        )


def test_seed_passes_clean_flag_to_fixture_builder():
    function = _function_ast("seed")
    calls = _calls_named(
        function,
        "create_fixtures",
    )

    assert len(calls) == 1
    assert _keyword_is_name(
        calls[0],
        "clean",
        "clean_fixtures",
    )


def test_create_fixtures_cleanup_is_guarded_by_clean_flag():
    function = _function_ast(
        "create_fixtures"
    )

    rmtree_calls = []

    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "rmtree"
        ):
            rmtree_calls.append(node)

    assert len(rmtree_calls) == 1

    rmtree = rmtree_calls[0]

    guarded = False

    for node in ast.walk(function):
        if not isinstance(node, ast.If):
            continue

        if not (
            isinstance(node.test, ast.Name)
            and node.test.id == "clean"
        ):
            continue

        guarded = any(
            child is rmtree
            for child in ast.walk(node)
        )

    assert guarded


def test_azure_safe_seed_validates_migration_baseline_before_inserting():
    function = _function_ast("seed")

    source = ast.unparse(function)

    validator = "validate_preprod_migration_baseline(db)"
    assert validator in source
    assert "office = ConsultancyOffice" in source
    office_position = source.index(
        "office = ConsultancyOffice"
    )
    assert source.index(validator) < office_position


def test_seed_module_retains_all_canonical_helper_functions():
    expected = {
        "seed",
        "ensure_primary_proposal_sources",
        "ensure_proposals_contracts_demo_state",
        "ensure_contract_center_golden_state",
        "create_fixtures",
        "seed_week2",
        "seed_week3",
        "seed_week4",
        "seed_week45",
        "seed_week7",
        "seed_week8",
        "seed_week9",
        "seed_week10",
        "seed_reconciliation",
        "seed_week11",
        "seed_week12",
        "seed_week13",
        "seed_week14",
    }

    missing = {
        name
        for name in expected
        if not hasattr(seed_cli, name)
    }

    assert not missing


def test_week2_and_week3_reset_defaults_remain_destructive_for_dev_test():
    for function in (
        seed_cli.seed_week2,
        seed_cli.seed_week3,
    ):
        signature = inspect.signature(
            function
        )

        assert (
            signature.parameters[
                "reset_existing"
            ].default
            is True
        )


def test_create_fixtures_clean_default_remains_true():
    signature = inspect.signature(
        seed_cli.create_fixtures
    )

    assert (
        signature.parameters[
            "clean"
        ].default
        is True
    )
