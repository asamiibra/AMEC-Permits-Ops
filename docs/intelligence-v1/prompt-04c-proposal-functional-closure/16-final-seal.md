# P04C final seal

P04C_STATUS=FAILURE
P04C_ZERO_CAPABILITY_LOSS=PASS (server action projection and focused role coverage)
P04C_FUNCTIONAL_INTEGRATION=PASS (focused backend lifecycle and frontend/browser closure)
P04C_REAL_STACK_BROWSER_ACCEPTANCE=FAILURE
P04C_SQL_PERSISTENCE_READBACK=FAILURE
P04C_LPO_REVISION_LOOP=PASS (focused mismatch and stale-revision regression)
P04C_RBAC_NEGATIVE_MATRIX=PASS (focused role denial and existing security coverage)
P04C_UI_CONFORMANCE=PASS (312/312 crawl cases plus final decision check)
P04C_BACKEND_REGRESSION=UNRESOLVED (635 passed, 11 skipped before stall; no complete exit)

Terminal gate: `frontend/browser-real-stack/bd-proposal-forms-driven-v2.spec.ts` received a backend health response with `database_dialect=sqlite`; the real-stack contract requires `postgresql`. The run therefore cannot prove real-stack browser acceptance or SQL persistence readback against the qualifying database.

Root cause: no PostgreSQL-backed runtime was available at the tested local API/frontend pair; the available runtime is the synthetic SQLite environment.

Separate regression gate: the full backend run stalled in the phase-4 integration segment after 635 passed and 11 skipped; the prior isolated owner-session failure was fixed and passed. Exact next action for that gate is a stable rerun of `PYTHONPATH=. APP_ENV=TEST SYNTHETIC_ONLY=true python3 -m pytest -q backend/tests` and capture of a complete exit.

Exact next action for the real-stack gates: provide a qualifying PostgreSQL-backed `BASE_URL` and `API_BASE_URL`, run `npm run browser-real-stack -- --reporter=line`, then rerun the SQL persistence/readback proof and update this seal. The current branch remains implementation-complete for the synthetic stack but is not a P04C PASS.

This seal intentionally does not self-reference its final commit or tree.
