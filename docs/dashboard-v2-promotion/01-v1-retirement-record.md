# V1 Retirement Record

Owner decision superseded the earlier simplified-V1 presentation decision on 2026-08-15.

- Last V1 route: `/dashboard` in the pre-promotion `DashboardPage` default presentation.
- Last V1 presentation branches: `DashboardPage` and `CanonicalFormsLibrary` with `governanceMode=false`; the default Inputs projection.
- V1 API clients: canonical `/api/master-content`, `/api/definitions`, and `/api/dashboard-inputs`; there was no separate V1 data model.
- Retired behavior: simplified Dashboard presentation hid Wave A/B/C governance controls and exposed a second live `/dashboard-v2` surface.
- Replacement: `/dashboard` now renders the governance-capable current Dashboard over canonical Master Content APIs.
- Compatibility: `/dashboard-v2` and `/dashboard-v2/inputs-go-live` rewrite to the canonical routes in the SPA.
- Retirement SHA: recorded in `artifacts/dashboard-v2-promotion/final-result.json` after commit.
- Historical evidence: prior split tests, screenshots, and docs remain in Git history; this record is marked `SUPERSEDED_BY_OWNER_DECISION_2026_08_15`.
