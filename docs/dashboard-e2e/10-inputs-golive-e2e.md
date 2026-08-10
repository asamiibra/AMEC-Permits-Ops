# Inputs & Go-Live

The Dashboard-specific route is `/dashboard/inputs-go-live`; it is distinct from the legacy `/admin/go-live-readiness` checklist. It derives categories, reference numbering, module policy, engineering activation policy, report scope, permissions, four-library counts, SOR state, and file policy from current backend metadata. Owner confirmation is persisted; proposed defaults and optional items are not represented as production confirmation.

The clean browser screenshot is `artifacts/dashboard-e2e/screenshots/inputs-and-go-live.png`.

Results: `DASHBOARD_INPUTS_E2E_PASS`, `DASHBOARD_INPUTS_DERIVED_STATE_PASS`, `DASHBOARD_INPUTS_PERSISTENCE_E2E_PASS`, `DASHBOARD_INPUTS_NO_DUPLICATE_TRUTH_PASS`.
