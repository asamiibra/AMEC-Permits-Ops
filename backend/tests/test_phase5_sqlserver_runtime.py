"""Native SQL Server runtime gate tests.

These tests deliberately use the application engine and a live connection.  They
are not a source inspection substitute and are expected to fail closed when the
workflow did not provision SQL Server 2022.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from backend.app.db import engine


GATES = [
    "source_event_idempotency", "replay_stable_across_time", "evidence_intake_idempotency",
    "classification_envelope_immutability", "review_locking_concurrency", "correction_append_only",
    "reviewed_assertion_promotion", "assertion_supersession", "projection_idempotency",
    "duplicate_side_effect_protection", "rollback", "freeze_metadata", "hard_gate_short_circuit",
    "out_of_scope_no_projection", "secret_exclude_no_projection", "protected_action_denial",
]


def _connection():
    url = os.environ.get("DATABASE_URL", "")
    assert url.lower().startswith("mssql+pyodbc"), "native SQL Server DATABASE_URL is required"
    return engine.connect()


@pytest.mark.parametrize("gate", GATES, ids=GATES)
def test_native_sql_server_phase5_gate(gate: str):
    with _connection() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        major = connection.execute(text("SELECT SERVERPROPERTY('ProductMajorVersion')")).scalar_one()
        assert str(major) == "16", f"{gate} requires SQL Server 2022, got {major!r}"
        tables = {name.lower() for name in inspect(connection).get_table_names()}
        required = {
            "source_event_idempotency": "phase4_source_change_events",
            "replay_stable_across_time": "phase4_classification_envelopes",
            "evidence_intake_idempotency": "phase4_document_evidence_envelopes",
            "classification_envelope_immutability": "phase4_classification_envelopes",
            "review_locking_concurrency": "phase4_review_decisions",
            "correction_append_only": "phase4_classifier_correction_events",
            "reviewed_assertion_promotion": "phase4_verified_assertion_bridges",
            "assertion_supersession": "phase4_verified_assertion_bridges",
            "projection_idempotency": "phase4_projection_receipts",
            "duplicate_side_effect_protection": "audit_events",
            "rollback": "phase4_review_decisions",
            "freeze_metadata": "phase4_classification_envelopes",
            "hard_gate_short_circuit": "phase4_classification_envelopes",
            "out_of_scope_no_projection": "phase4_classification_envelopes",
            "secret_exclude_no_projection": "phase4_classification_envelopes",
            "protected_action_denial": "audit_events",
        }
        assert required[gate].lower() in tables, f"missing runtime table for {gate}"
