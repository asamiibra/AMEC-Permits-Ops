# Historical V2 root identity

Git history identifies the historical V2 route and presentation evolution:

- Route: /dashboard-v2
- File: frontend/src/Dashboard.tsx
- Component: DashboardPage with governanceMode
- Introducing commit: 56ce49a (feat(dashboard): restore v1 and introduce governance v2)
- Wave A evolution: 56ce49a plus the preceding readiness/master-content commits
- Wave B/C evolution: 9690e56 (Implement Dashboard V2 Forms Governance Waves B and C)
- Last known working V2 reference before the canonical promotion: 9690e56
- V2 children: the governed CanonicalFormsLibrary, advanced governance filters, governance detail sections, Reports, Engineering Works, Definitions, history drawers, and Inputs & Go-Live link
- Clients: canonical Master Content/Definitions APIs plus /api/dashboard-v2/catalogs, /api/dashboard-v2/forms, and governance mutation/readiness services.

The source audit shows V2 historically shared the DashboardPage file with V1 but differed in presentation children and mode. The repair makes that lineage explicit in the active CurrentDashboard root instead of relying on a mode prop.
