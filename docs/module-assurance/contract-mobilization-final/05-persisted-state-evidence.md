# Persisted-state evidence

The Contract and Handover tests use a fresh `SessionLocal` after each material API mutation to read the exact revision/evidence/service/closure row and related `AuditEvent` rows. The covered durable transitions are review, checker, acceptance, executed evidence, client-copy distribution, Operations handoff, activation, service engagement, readiness, billing context, schedule revisions, Handover receipt/acceptance/service close, and canonical administrative close.

For denied mutations the tests verify the request is denied and the Contract, revision, evidence, activation, and closure rows remain unchanged. Version tests verify current-version pinning and reject superseded, arbitrary, cross-Contract, and wrong-purpose references.
