# Full regression

Canonical isolated PostgreSQL comparison:

- Pre-Wave-A baseline `0ccb61a2b7ac483a17590c27eca594b16b505bb7`: `146 passed, 0 failed, 0 skipped`.
- Wave A pre-repair: `151 passed, 0 failed, 0 skipped`.
- Wave A final: `151 passed, 0 failed, 0 skipped`.

The detailed comparison and closure repair classification are in [09-full-regression-adjudication.md](09-full-regression-adjudication.md). The final PostgreSQL suite is green; deployment and freeze gates remain separate.
