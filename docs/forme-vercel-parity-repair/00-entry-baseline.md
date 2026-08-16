# FORME/Vercel parity repair — entry baseline

The primary worktree entered on `branch/owner-form-simple-dashboard` at
`47468e0ea517e2ce1e1f130e92e8056873b398ce`, with only the pre-existing
`mock-systems/excel/permit_tracker.xlsx` modification. The preserved stash is
`2f072fce8eb6f31851a8233e054a88a0f17eca6c`; it was not popped, dropped, or
rewritten.

Current `origin/main` is `ba5089e40a9259dcc4a4d92cddf34bf5ccde0b29`.
The required branch still exists and was not recreated. The repair worktree
was based directly on current `origin/main` using
`fix/vercel-forme-master-parity`.

Alembic repository head is `0058_source_intake_ledger`; the deployed backend
reported the same single version. The current Vercel frontend and backend
deployments are READY at main SHA `ba5089e...`; the backend runtime still
reported `RELEASE_SHA=202728cb...`, so exact release-variable parity was not
yet true at entry.

`PREEXISTING_EXCEL_CHANGE_PRESERVED=1`.
