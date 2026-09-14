# Staleness and revalidation

Production direct-clear is rejected with `CAUSAL_REVALIDATION_REQUIRED`. Revalidation requires a DRAFT revision based on the latest accepted revision, PASS, and every active event ID; each event records the exact revalidation revision, reviewer, timestamp, and result. Release remains blocked while active staleness exists. The frontend now exposes only this causal flow.
