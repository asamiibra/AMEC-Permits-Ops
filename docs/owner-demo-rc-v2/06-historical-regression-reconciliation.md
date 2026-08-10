# Historical Regression Reconciliation

Protected current suites pass: backend SQLite `99 passed`, backend PostgreSQL `99 passed`, frontend unit `24 passed`, build passed, and selected real-stack browser `15 passed`.

Six historical browser failures are superseded assertions, not current-scope regressions: two accessibility tests and visual QA still require `.global-language-switch`; three owner-rehearsal tests still require `Resume permit work` and a `Role` selector. The current scope intentionally uses English/LTR and persona selection, and the AMEC Work Axe smoke test passes with no serious or critical violations.
