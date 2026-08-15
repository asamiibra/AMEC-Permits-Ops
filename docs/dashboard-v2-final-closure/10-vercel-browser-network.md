# Vercel browser and network acceptance

The exact runtime source SHA c2a7551d1304ab43b6d8148ad9861d7b2f9dd19a was deployed to both Vercel projects. Backend health reports PostgreSQL, durable database, migration 0058_source_intake_ledger, and the same full SHA. The structured request trace is in artifacts/dashboard-v2-final-closure/vercel-network-trace.json; the browser result is in artifacts/dashboard-v2-final-closure/vercel-browser-results.json.

Acceptance covers /dashboard, the CurrentDashboard root marker, governance overview/source panel, four library navigation, advanced governance filters, form detail, /dashboard-v2 redirect, and /dashboard-v2/inputs-go-live redirect. No V1-only Dashboard endpoint is called.
