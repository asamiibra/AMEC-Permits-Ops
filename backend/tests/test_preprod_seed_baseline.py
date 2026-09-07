from types import SimpleNamespace

import pytest

from backend.app.seed import cli as seed_cli


def _baseline_row(**overrides):
    values = {
        **seed_cli.PREPROD_MIGRATION_BASELINE_SEQUENCE,
        "created_at": "migration-time-a",
        "updated_at": "migration-time-b",
        **overrides,
    }
    return SimpleNamespace(**values)


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class _Session:
    def __init__(self, sequence_rows, occupied_table=None):
        self.sequence_rows = sequence_rows
        self.occupied_table = occupied_table

    def scalars(self, statement):
        return _Result(self.sequence_rows)

    def execute(self, statement):
        table_name = statement.get_final_froms()[0].name
        rows = (
            [object()]
            if table_name == self.occupied_table
            else []
        )
        return _Result(rows)


def test_exact_baseline_passes_and_timestamps_are_ignored():
    seed_cli.validate_preprod_migration_baseline(
        _Session(
            [
                _baseline_row(
                    created_at="different-created-at",
                    updated_at="different-updated-at",
                )
            ]
        )
    )


@pytest.mark.parametrize(
    "change",
    [
        {"id": "wrong-id"},
        {"content_type": "OTHER"},
        {"prefix": "WRONG"},
        {"padding": 3},
        {"scope": "LOCAL"},
        {"active": False},
        {"current_value": 1},
    ],
)
def test_mutated_baseline_fields_fail_closed(change):
    with pytest.raises(
        RuntimeError,
        match="migration baseline",
    ):
        seed_cli.validate_preprod_migration_baseline(
            _Session([_baseline_row(**change)])
        )


def test_missing_baseline_fails_closed():
    with pytest.raises(RuntimeError, match="migration baseline"):
        seed_cli.validate_preprod_migration_baseline(
            _Session([])
        )


def test_extra_sequence_row_fails_closed():
    with pytest.raises(RuntimeError, match="migration baseline"):
        seed_cli.validate_preprod_migration_baseline(
            _Session(
                [
                    _baseline_row(),
                    _baseline_row(
                        id="second-sequence",
                        content_type="OTHER",
                    ),
                ]
            )
        )


def test_unrelated_application_row_fails_closed():
    with pytest.raises(RuntimeError, match="unexpected application data"):
        seed_cli.validate_preprod_migration_baseline(
            _Session(
                [_baseline_row()],
                occupied_table="audit_events",
            )
        )
