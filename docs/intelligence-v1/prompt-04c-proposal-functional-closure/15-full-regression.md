# P04C regression record

Deterministic and browser-backed checks executed before the final commit:

FRONTEND_BUILD=PASS
PYTHON_COMPILE=PASS
DIFF_CHECK=PASS
FRONTEND_UNIT=PASS (22 files, 126 tests)
BACKEND_FOCUSED=PASS (12 tests)
P04C_PROJECTION_TEST=PASS (1 test)
P04_CANONICAL_BROWSER=PASS (3 tests against the P04C worktree on 127.0.0.1:5174)
UI_CONFORMANCE=PASS (312/312 crawl cases plus final decision check)
BACKEND_FULL=UNRESOLVED (635 passed, 11 skipped before stall; final process interrupted after no progress at 58%)

The historical P04 test evidence is preserved. The active real-stack run was attempted against the P04C frontend and stopped at its first qualifying environment gate: the backend reported `database_dialect=sqlite`, while the active real-stack contract requires PostgreSQL. That result is recorded as a terminal qualification failure in `16-final-seal.md`; no SQLite run is represented as SQL qualification.

The full backend process also did not yield a valid completion: it reached 635 passed and 11 skipped before stalling in the existing phase-4 integration segment. The isolated owner-session failure encountered before the stall was corrected and passed independently; the full count must be rerun in a stable environment before a P04C PASS can be issued.
