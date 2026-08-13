# Full regression adjudication

The exact repository-root invocation was used for both isolated PostgreSQL runs:

`env APP_ENV=TEST DATABASE_URL=postgresql+psycopg://... SYNTHETIC_ONLY=true pytest -q backend/tests`

| Suite | Result | Classification | Action |
|---|---:|---|---|
| Pre-Wave-A baseline at `0ccb61a2b7ac483a17590c27eca594b16b505bb7` | 146 passed, 0 failed, 0 skipped | PASS | None |
| Wave A before final migration repair | 151 passed, 0 failed, 0 skipped | PASS | None |
| Wave A after final migration repair | 151 passed, 0 failed, 0 skipped | PASS | None |

The earlier `pytest -q` launch from `backend` produced three path-resolution failures because tests resolve repository-root `config/` and `mock-systems/` paths. This was classified as `TEST_HARNESS_FAILURE`; the canonical root invocation passed without changing product behavior or test expectations.

The closure-specific baseline-state migration run found one actionable defect: an existing `alembic_version.version_num VARCHAR(32)` could not record the 38-character Wave A revision. Migration `0036` now widens that legacy column to 64 characters before recording the head. Clean and existing-state upgrades pass after the repair.

No `WAVE_A_REGRESSION`, `PRE_EXISTING_CODE_FAILURE`, `ENVIRONMENT_CONFIGURATION_FAILURE`, `FLAKY_NONDETERMINISTIC`, `OBSOLETE_TEST_EXPECTATION`, `DEPENDENCY_EXTERNAL`, or `UNKNOWN` full-suite failure remains.
