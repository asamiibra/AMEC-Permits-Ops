# Dashboard v3 owner UX

Implemented and verified on the deployed Dashboard.

- Forms, Reports, Engineering Works, and Definitions use the requested six primary columns: S/N, Reference, name/term, Category, Description/Meaning, and Actions.
- Open exposes a details drawer with version/status, Used In, purpose bindings, source classification, and current-source download.
- Edit remains Owner-only; History remains available as an immutable version/revision surface.
- Engineering editing separates Category, Source Type, and Discipline. Additional authority, edition, effective-date, clause/section, and applicability notes remain in the governed metadata payload.
- AI Assist remains visibly advisory and disabled; no generation path was added.

Evidence: browser inspection of `https://amec-permits-ops.vercel.app/dashboard`, frontend build, and 29 frontend tests.

`DASHBOARD_V3_OWNER_UX_PASS`
