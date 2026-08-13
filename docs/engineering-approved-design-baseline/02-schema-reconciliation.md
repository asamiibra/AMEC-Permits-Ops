# Schema reconciliation

## Required invariants

1. `Project` remains the only project identity and every new engineering row is project-scoped.
2. `EngineeringDeliverable` is stable across revisions.
3. `EngineeringDeliverableRevision` is distinct from `DocumentVersion`.
4. Renditions pin exact canonical `DocumentVersion` rows and retain native/published distinction.
5. Approved revisions and approved baseline membership are immutable; changes require a new revision/baseline.
6. Review, professional approval, technical checks, calculation records, material tests, and lab evidence are separate evidence states.
7. Baseline manifests enumerate exact revision/rendition/approval/rule references and are reproducible.
8. Foreign keys and project/status/approval/baseline/document indexes support list and validation paths.
9. No new visible role is introduced; authorization uses existing capability conventions.

## Migration strategy

Additive migration only. New tables and indexes are introduced without rewriting or mass-backfilling existing Project, DocumentVersion, Party, Property, Dashboard, BD, Admin Contract, Requirement, or Technical Rule records. Existing rows remain valid and can be adopted by explicit project-scoped engineering actions.
