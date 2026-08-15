# API Reconciliation

The active Dashboard uses canonical `/api/master-content` and `/api/definitions` list/write/history contracts. The `/api/dashboard-v2` router is retained only as the shared governance facade for applicability, lineage, readiness, and automation detail; it does not own master content or expose a second Owner page.

`DASHBOARD_UI_VERSION_BUSINESS_BRANCH_COUNT=0` in active Dashboard code. The only remaining `dashboard-v2` strings are compatibility paths, governance-facade calls, and historical test/evidence names.
