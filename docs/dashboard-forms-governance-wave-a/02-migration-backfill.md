# Migration and backfill

Migration `0036_dashboard_forms_governance_wave_a` creates the five tables, indexes, and deterministic governance backfill. Existing rows default to `NEEDS_REVIEW`, `UNKNOWN`, and `UNVERIFIED` unless the existing purpose binding or owner-demo seed proves AMEC ownership. No provenance, currentness, or source authority is invented.

Verified locally:

- Fresh SQLite: full Alembic chain upgrades to `0036_dashboard_forms_governance_wave_a`.
- Fresh PostgreSQL: full Alembic chain upgrades to the same head.
- Existing-state PostgreSQL upgrade from `0035_owner_decision_closure` passes after widening a legacy `alembic_version.version_num` column from 32 to 64 characters.
- Re-running `alembic upgrade head` is idempotent; the final head is `0036_dashboard_forms_governance_wave_a`.
