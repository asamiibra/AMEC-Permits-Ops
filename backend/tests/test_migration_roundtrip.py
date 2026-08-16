"""Opt-in PostgreSQL regression for cross-revision FK downgrade ownership."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_POSTGRES_MIGRATION_REGRESSION") != "1"
    or not DATABASE_URL.startswith("postgresql"),
    reason="opt-in PostgreSQL migration regression",
)


def _alembic(*args: str) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "."
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=environment,
        check=True,
    )


def _inbound_constraint_names(connection) -> set[str]:
    rows = connection.execute(
        text(
            """
            SELECT con.conname
            FROM pg_constraint AS con
            JOIN pg_class AS referenced_table
              ON referenced_table.oid = con.confrelid
            JOIN pg_namespace AS referenced_schema
              ON referenced_schema.oid = referenced_table.relnamespace
            WHERE con.contype = 'f'
              AND referenced_schema.nspname = 'public'
              AND referenced_table.relname = 'authority_case_findings'
            ORDER BY con.conname
            """
        )
    )
    return {row[0] for row in rows}


def _table_constraint_names(connection, table_name: str) -> set[str]:
    rows = connection.execute(
        text(
            """
            SELECT con.conname
            FROM pg_constraint AS con
            JOIN pg_class AS table_class ON table_class.oid = con.conrelid
            JOIN pg_namespace AS table_schema ON table_schema.oid = table_class.relnamespace
            WHERE table_schema.nspname = 'public'
              AND table_class.relname = :table_name
            """
        ),
        {"table_name": table_name},
    )
    return {row[0] for row in rows}


def test_later_finding_foreign_keys_unwind_before_revision_0044() -> None:
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT to_regclass('public.authority_case_findings')"
                )
            ).scalar_one() == "authority_case_findings"
            assert _inbound_constraint_names(connection) == {
                "authority_finding_responses_finding_id_fkey",
                "construction_issues_authority_case_finding_id_fkey",
                "engineering_authority_finding_links_authority_finding_id_fkey",
            }

        _alembic("downgrade", "0046_engineering_drawing_review_reconciliation")
        with engine.connect() as connection:
            assert "party_role_assignments_party_id_fkey" not in _table_constraint_names(
                connection, "party_role_assignments"
            )
        _alembic("upgrade", "0047_prebilling_regulatory_context")
        with engine.connect() as connection:
            assert "party_role_assignments_party_id_fkey" in _table_constraint_names(
                connection, "party_role_assignments"
            )
        _alembic("upgrade", "head")

        _alembic("downgrade", "0049_billing_v2_communication_due_events")
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT to_regclass('public.authority_case_findings')"
                )
            ).scalar_one() == "authority_case_findings"
            assert _inbound_constraint_names(connection) == {
                "authority_finding_responses_finding_id_fkey",
                "engineering_authority_finding_links_authority_finding_id_fkey",
            }

        _alembic("downgrade", "0045_admin_contract_owner_sketch_reconciliation")
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT to_regclass('public.authority_case_findings')"
                )
            ).scalar_one() == "authority_case_findings"
            assert _inbound_constraint_names(connection) == {
                "authority_finding_responses_finding_id_fkey",
            }
            assert connection.execute(
                text("SELECT to_regclass('public.engineering_internal_review_comments')")
            ).scalar_one() == "engineering_internal_review_comments"
            assert not {
                "engineering_internal_review_comments_review_id_fkey",
                "engineering_internal_review_comments_revision_id_fkey",
            } & _table_constraint_names(connection, "engineering_internal_review_comments")

        _alembic("downgrade", "0043_project_engineering_approved_design_baseline")
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT to_regclass('public.authority_case_findings')"
                )
            ).scalar_one() is None

        _alembic("downgrade", "0003_phase0_week3_decision_layer")
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT to_regclass('public.parties')")
            ).scalar_one() is None

        _alembic("upgrade", "head")
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT to_regclass('public.parties')")
            ).scalar_one() == "parties"
            assert "party_role_assignments_party_id_fkey" in _table_constraint_names(
                connection, "party_role_assignments"
            )
    finally:
        _alembic("upgrade", "head")
        engine.dispose()
