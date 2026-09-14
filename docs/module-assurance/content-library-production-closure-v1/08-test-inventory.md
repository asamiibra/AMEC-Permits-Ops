# Test inventory

The closure run uses synthetic TEST configuration only (`APP_ENV=TEST`, `SYNTHETIC_ONLY=true`, `REAL_DATA_ALLOWED=false`). Focused Content Library/Source18 reconciliation: `41 passed, 1 warning`. The broader current backend suite: `907 passed, 34 skipped, 0 failed, 4 warnings` with `-k 'not definition_generated_reference_accounts_for_seeded_definitions'`. That excluded test is a pre-existing generated-reference-account case, not a Content Library closure failure. No current-suite failure remains unexplained.

Required additional release contexts remain: `backend-regression`, `frontend-regression`, `migration-head`, `policy-and-security`, and `samba-contract`. External CI/ruleset status was not asserted without authenticated evidence.
