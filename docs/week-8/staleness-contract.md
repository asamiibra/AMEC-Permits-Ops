# Staleness Contract

Allowed explicit states are `CURRENT`, `STALE`, `NEEDS_REVALIDATION`, and `SUPERSEDED`. `StaleReason` links the affected target to the material-change event and records a stable reason code, explanation, and optional replacement target. A stale package cannot be approved or used to create a new revision.
