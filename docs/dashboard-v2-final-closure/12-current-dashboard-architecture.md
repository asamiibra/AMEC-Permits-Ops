# Current Dashboard architecture

- Product label: Dashboard
- Owner route: /dashboard
- Implementation lineage: Historical Dashboard V2 → evolved current Dashboard
- Compatibility: /dashboard-v2 → /dashboard
- Retired: Dashboard V1 runtime

The root is CurrentDashboard. Its V2 presentation components are DashboardGovernanceOverview, DashboardLibraryNavigation, CanonicalFormsLibrary, governed Form detail/history/editor surfaces, Reports, Engineering Works, and Definitions.

Canonical data remains MasterContentItem, Document, DocumentVersion, DefinitionEntry/Revision, bindings, audit, RBAC, storage, and Source Intake.

Business status remains Current, Needs Review, and Inactive.
