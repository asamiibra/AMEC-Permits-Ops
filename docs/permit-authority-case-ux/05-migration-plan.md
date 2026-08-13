# Migration and compatibility plan

## Decision

No Permit-specific migration is required. The implementation is a read-model/API/UI layer over existing canonical tables and relationships. Alembic head remains the Preparation + Submission Loop head unless a pre-existing canonical model gap is separately approved.

## Compatibility

- Existing `/proposals-contracts`, `/permit`, and `/authority-cases` behavior remains reachable while `/permits` becomes the Owner-facing portfolio.
- Existing canonical creation and submission commands remain the only write paths for authority cases, findings, forms, documents, drawings, preparation, and submissions.
- No data is copied into a Permit namespace.
- Exports are generated in memory and do not write to `mock-systems/excel` or create export tables.
- Existing migration round-trip and regression tests remain required after the UX layer is added.

## Deferred model gaps

The current engineering model does not expose a canonical `EngineeringReviewCategory` distinct from discipline. The UX records this as a documented gap and does not synthesize one. A future domain migration, if approved, must be owned by Engineering and separately backfilled with lineage.

## Rollback

The route layer can be disabled or reverted without data rollback because no new source-of-truth rows are created by the read model. Any future approved schema change must have an explicit forward migration, downgrade/round-trip proof, and separate data-retention decision.
