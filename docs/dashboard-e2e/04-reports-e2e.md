# Reports E2E

Reports use canonical `R-xxxx` identity, verified source/version history, metadata-only edits without a new source version, and material revision propagation through the shared dependency contract. `REPORTS` binding/filter behavior and generated-report dependency revalidation are covered. No duplicate DashboardReport or ReportsModuleReport entity exists in the current model.

Results: `REPORT_CREATE_E2E_PASS`, `REPORT_METADATA_MODIFY_E2E_PASS`, `REPORT_VERSION_E2E_PASS`, `REPORT_REPORTS_MODULE_CANONICAL_E2E_PASS`, `DUPLICATE_REPORT_TRUTH_ZERO`.
