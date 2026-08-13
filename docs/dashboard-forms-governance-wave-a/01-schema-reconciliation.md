# Schema reconciliation

Wave A adds five governance entities without changing the four Dashboard libraries or canonical master-content models:

- `MasterContentGovernanceProfile`
- `MasterContentSourceProvenance`
- `MasterContentQualityFlag`
- `MasterContentSourceSection`
- `MasterContentReadinessAssessment`

The entities bind to `MasterContentItem` and exact immutable `DocumentVersion` records. The migration is `0036_dashboard_forms_governance_wave_a` and reaches head on fresh SQLite and PostgreSQL chains.

The API exposes governance metadata and filters while keeping source bytes out of ordinary list/search projections.
