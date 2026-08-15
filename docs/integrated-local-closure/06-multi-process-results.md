# Multi-process results

The two-process run produced one batch, one canonical master, one outbox event, one final version, and one winner for each claim/recovery race. Duplicate masters, immutable-target overwrites, lost events, and process-local lock requirements were all zero.

See `artifacts/integrated-local-closure/multi-process-results.json`.
