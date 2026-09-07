from types import SimpleNamespace

import pytest

from backend.app import bootstrap_preprod


def _settings(
    *,
    app_env: str = "AZURE-PREPROD",
    synthetic_only: bool = True,
    real_data_allowed: bool = False,
    storage_provider: str = "mock",
    synology_mode: str = "SYNTHETIC",
):
    return SimpleNamespace(
        app_env=app_env,
        synthetic_only=synthetic_only,
        real_data_allowed=real_data_allowed,
        storage_provider=storage_provider,
        synology_mode=synology_mode,
    )


def _complete_anchors():
    return bootstrap_preprod.BootstrapAnchors(
        office_present=True,
        users=(
            bootstrap_preprod
            .EXPECTED_USER_EMAILS
        ),
        projects=(
            bootstrap_preprod
            .EXPECTED_PROJECT_NUMBERS
        ),
        applications=(
            bootstrap_preprod
            .EXPECTED_APPLICATION_NUMBERS
        ),
    )


def _empty_anchors():
    return bootstrap_preprod.BootstrapAnchors(
        office_present=False,
        users=frozenset(),
        projects=frozenset(),
        applications=frozenset(),
    )


class _Context:
    def __init__(self):
        self.db = object()

    def __enter__(self):
        return self.db

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


def _session_factory():
    return _Context()


def _install_base(
    monkeypatch,
    *,
    anchors,
    baseline_validator=None,
):
    monkeypatch.setattr(
        bootstrap_preprod,
        "get_settings",
        lambda: _settings(),
    )

    monkeypatch.setattr(
        bootstrap_preprod,
        "verify_database_migration_head",
        lambda: "0059_entra_user_identity",
    )

    monkeypatch.setattr(
        bootstrap_preprod,
        "SessionLocal",
        _session_factory,
    )

    anchor_values = iter(
        anchors
    )

    monkeypatch.setattr(
        bootstrap_preprod,
        "_bootstrap_anchors",
        lambda db: next(
            anchor_values
        ),
    )

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "validate_preprod_migration_baseline",
        baseline_validator or (lambda db: None),
    )


def test_anchor_completeness_requires_exact_sets():
    assert _complete_anchors().complete

    partial = (
        bootstrap_preprod.BootstrapAnchors(
            office_present=True,
            users=frozenset(),
            projects=(
                bootstrap_preprod
                .EXPECTED_PROJECT_NUMBERS
            ),
            applications=(
                bootstrap_preprod
                .EXPECTED_APPLICATION_NUMBERS
            ),
        )
    )

    assert not partial.complete
    assert partial.any_present


def test_bootstrap_rejects_non_preprod(
    monkeypatch,
):
    monkeypatch.setattr(
        bootstrap_preprod,
        "get_settings",
        lambda: _settings(
            app_env="TEST"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="restricted",
    ):
        bootstrap_preprod.run_preprod_bootstrap()


def test_bootstrap_requires_synthetic_only(
    monkeypatch,
):
    monkeypatch.setattr(
        bootstrap_preprod,
        "get_settings",
        lambda: _settings(
            synthetic_only=False
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="SYNTHETIC_ONLY",
    ):
        bootstrap_preprod.run_preprod_bootstrap()


def test_bootstrap_rejects_real_data_allowed(
    monkeypatch,
):
    monkeypatch.setattr(
        bootstrap_preprod,
        "get_settings",
        lambda: _settings(
            real_data_allowed=True
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="REAL_DATA_ALLOWED",
    ):
        bootstrap_preprod.run_preprod_bootstrap()


@pytest.mark.parametrize(
    (
        "storage_provider",
        "synology_mode",
    ),
    [
        (
            "smb",
            "SYNTHETIC",
        ),
        (
            "mock",
            "REAL",
        ),
    ],
)
def test_bootstrap_rejects_external_storage_modes(
    monkeypatch,
    storage_provider,
    synology_mode,
):
    monkeypatch.setattr(
        bootstrap_preprod,
        "get_settings",
        lambda: _settings(
            storage_provider=storage_provider,
            synology_mode=synology_mode,
        ),
    )

    with pytest.raises(
        RuntimeError
    ):
        bootstrap_preprod.run_preprod_bootstrap()


def test_empty_database_uses_non_destructive_seed_flags(
    monkeypatch,
):
    _install_base(
        monkeypatch,
        anchors=[
            _empty_anchors(),
            _complete_anchors(),
        ],
    )

    calls = []

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "seed",
        lambda **kwargs: calls.append(
            kwargs
        ),
    )

    assert (
        bootstrap_preprod
        .run_preprod_bootstrap()
        == "BOOTSTRAPPED"
    )

    assert calls == [
        {
            "initialize_schema": False,
            "reset_existing": False,
            "clean_fixtures": False,
        }
    ]


def test_first_bootstrap_invokes_shared_seed_baseline_validator(
    monkeypatch,
):
    calls = []

    _install_base(
        monkeypatch,
        anchors=[
            _empty_anchors(),
            _complete_anchors(),
        ],
        baseline_validator=lambda db: calls.append(db),
    )

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "seed",
        lambda **kwargs: None,
    )

    assert (
        bootstrap_preprod.run_preprod_bootstrap()
        == "BOOTSTRAPPED"
    )
    assert len(calls) == 1


def test_existing_complete_bootstrap_is_idempotent(
    monkeypatch,
):
    _install_base(
        monkeypatch,
        anchors=[
            _complete_anchors(),
            _complete_anchors(),
        ],
    )

    seed_calls = []
    repair_calls = []

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "seed",
        lambda **kwargs: seed_calls.append(
            kwargs
        ),
    )

    monkeypatch.setattr(
        bootstrap_preprod,
        "_repair_idempotent_post_seed_state",
        lambda: repair_calls.append(
            "repair"
        ),
    )

    assert (
        bootstrap_preprod
        .run_preprod_bootstrap()
        == "ALREADY_BOOTSTRAPPED"
    )

    assert seed_calls == []
    assert repair_calls == [
        "repair"
    ]


def test_partial_anchor_state_fails_closed(
    monkeypatch,
):
    partial = (
        bootstrap_preprod.BootstrapAnchors(
            office_present=True,
            users=frozenset(),
            projects=frozenset(),
            applications=frozenset(),
        )
    )

    _install_base(
        monkeypatch,
        anchors=[
            partial
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="partial",
    ):
        bootstrap_preprod.run_preprod_bootstrap()


def test_unrelated_existing_data_fails_closed(
    monkeypatch,
):
    def reject_unrelated_data(db):
        raise RuntimeError(
            "Synthetic preprod migration baseline is accompanied "
            "by unexpected application data; refusing seed."
        )

    _install_base(
        monkeypatch,
        anchors=[
            _empty_anchors()
        ],
        baseline_validator=reject_unrelated_data,
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected application data",
    ):
        bootstrap_preprod.run_preprod_bootstrap()


def test_final_anchor_verification_is_required(
    monkeypatch,
):
    _install_base(
        monkeypatch,
        anchors=[
            _empty_anchors(),
            _empty_anchors(),
        ],
    )

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "seed",
        lambda **kwargs: None,
    )

    with pytest.raises(
        RuntimeError,
        match="required canonical anchors",
    ):
        bootstrap_preprod.run_preprod_bootstrap()


def test_repair_uses_non_destructive_fixture_mode(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "create_fixtures",
        lambda root, *, clean: calls.append(
            (
                "fixtures",
                clean,
            )
        ),
    )

    monkeypatch.setattr(
        bootstrap_preprod,
        "synthetic_workspace_root",
        lambda: "/synthetic",
    )

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "ensure_primary_proposal_sources",
        lambda: calls.append(
            (
                "primary",
                None,
            )
        ),
    )

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "ensure_proposals_contracts_demo_state",
        lambda: calls.append(
            (
                "proposal",
                None,
            )
        ),
    )

    monkeypatch.setattr(
        bootstrap_preprod.seed_cli,
        "ensure_contract_center_golden_state",
        lambda: calls.append(
            (
                "contract",
                None,
            )
        ),
    )

    bootstrap_preprod._repair_idempotent_post_seed_state()

    assert calls[0] == (
        "fixtures",
        False,
    )
    assert len(calls) == 4


def test_main_failure_is_nonzero_and_redacted(
    monkeypatch,
    capsys,
):
    secret = "secret-value"

    def fail():
        raise RuntimeError(
            secret
        )

    monkeypatch.setattr(
        bootstrap_preprod,
        "run_preprod_bootstrap",
        fail,
    )

    assert (
        bootstrap_preprod.main()
        == 1
    )

    output = capsys.readouterr()

    assert '"status": "FAILED"' in output.err
    assert secret not in output.err
