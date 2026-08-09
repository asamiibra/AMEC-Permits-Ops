# Week 11 implementation plan

1. Add typed monitoring policy/run/check/state-observation records.
2. Execute only policy-allowed synthetic reads through versioned contracts.
3. Compare trusted snapshots; persist `NO_CHANGE` and route material changes to Week 7 findings.
4. Pause and fall back to assisted capture on contract drift, identity mismatch, auth blocks, or failure budget exhaustion.
5. Add external-mutation evidence, notification delivery-attempt history, timing records, focused console views, and synthetic report metrics.
6. Re-run the Week 10 Golden Path and clean PostgreSQL/UI checks.

Production polling cadence, production credentials, scheduler deployment, and final submission remain outside this build.
