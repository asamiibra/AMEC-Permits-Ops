# Test report

Passing validation:

- Focused backend Proposal, Content Library, form, hardening, and reconciliation suites: `28 passed` in the final focused run set (including the three commercial-control tests; the preceding focused run had 27 passed before the final idempotency/fixture additions).
- Frontend production build: PASS.
- Frontend Vitest: `21 files, 114 tests passed`.
- Python compileall for backend application and migrations: PASS.
- `git diff --check`: PASS.
- SQL Server clean migration and persistence proof: PASS.

The attempted entire sparse-clone backend sweep reached 546 passed and 11 skipped before being stopped after 16 failures caused by omitted `infra/`, `config/`, and unrelated baseline-exact migration fixtures in the intentionally sparse clone. Those failures are not Proposal module failures; the module-specific suites are the release evidence.
