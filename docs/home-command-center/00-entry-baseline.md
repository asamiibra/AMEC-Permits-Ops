# Home command center entry baseline

- Starting implementation revision: `4467c5532fc8aa19d48181e1debe1c109b643311`.
- Branch: `branch/ui-productionization`; remote branch existed at the same SHA at entry.
- The entry sidebar exposed Dashboard, AMEC Work, BD, Engineering, Construction, Completion / As-Built, Permit, Authority Cases, Issues, and Notifications. About PermitOps was a separate footer action.
- `/work` remains the canonical AMEC Work workspace. `/issues`, `/billing`, `/dashboard`, and `/notifications` remain canonical direct routes.
- `/dashboard` is the full Master Content / Content Library workspace; `/billing` is the full Finance workspace.
- Canonical workbook integrity was preserved: `3eb887e87bf0d5695a570e8aa1e6c917d646176c77e1b978d6387681d58f1be0`.

This wave changes presentation and navigation only. No backend, schema, domain model, workflow, filter, or canonical record source was changed.
