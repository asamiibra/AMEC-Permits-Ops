# Migration and backfill plan

## Plan

- Add the Project Engineering tables, foreign keys, uniqueness rules, and query indexes in one additive Alembic revision after `0042_bd_proposal_forms_driven_v2`.
- Do not mass-create work packages, deliverables, approvals, or baselines from historical files.
- Preserve existing data and allow downgrade/re-upgrade in disposable verification databases where repository policy permits.
- Use deterministic IDs, idempotency keys, and append-only audit/lineage writes for retry-safe actions.
- Keep stored file paths server-side; APIs expose IDs, hashes, and safe metadata only.

## Backfill status at entry

No Engineering backfill has run. Existing Dashboard Engineering Works and bounded E5/E6 records remain in their current domains until an explicit Project Engineering action references them.
