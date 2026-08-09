# Acceptance rehearsal plan

Command: `make acceptance-rehearsal`.

The runner creates isolated TEST state, executes Golden Path v1 and v2, verifies canonical fixture/config hashes, runs monitoring/drift, recurrence/preventive checks, P1 hold/release, TEST restore, role and variant checks, acceptance metrics, zero-tolerance safety, and emits `artifacts/week13-14-acceptance-result.json`.
