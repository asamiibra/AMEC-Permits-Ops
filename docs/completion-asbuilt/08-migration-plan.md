# Migration Plan

Before adding tables, the actual head was verified as `0051_construction_inspection_idempotency`. Prior migrations will not be edited. A new forward-only migration will add only the missing canonical Completion/As-Built objects and constraints: immutable/versioned AsBuiltBaseline and members, AS_BUILT BuildingSnapshot support, deterministic AsBuiltComparisonRun, first-class AsBuiltVariance, and any minimal generic relationship/read-model fields required after implementation review.

Constraints will enforce project/execution scope, baseline/member uniqueness, immutable version references, comparison idempotency, and safe current-version behavior. No historical As-Built, Completion case, outcome, or Handover records will be backfilled from filenames, folders, latest drawings, or dates.
