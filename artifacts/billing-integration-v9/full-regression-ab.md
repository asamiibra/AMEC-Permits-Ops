# Full-regression A/B causality

Fresh control and candidate worktrees ran the identical `pytest -q backend/tests` command with the same Python executable, environment, working-directory convention, and bounded 600-second timeout.

Both runs advanced through the same progress sequence: 7%, 15%, 23%, 31%, 39%, 47%, and 55%, then became quiescent and were killed at 600 seconds. The quiet output does not expose a single test name, but the shared stop is the known `scripts/phase5/source_preflight.py` subprocess region from the same harness. There was no control/candidate divergence.

Result:

- `CONTROL_FULL_REGRESSION_RESULT=SHARED_HARNESS_TIMEOUT_AT_55_PERCENT`
- `CANDIDATE_FULL_REGRESSION_RESULT=SHARED_HARNESS_TIMEOUT_AT_55_PERCENT`
- `FULL_REGRESSION_HARNESS_BLOCKER=source_preflight.py subprocess hang/timeout`
- `FULL_REGRESSION_BLOCKER_PREEXISTING=true`
- `FULL_REGRESSION_CAUSED_BY_BILLING_DELTA=false`
