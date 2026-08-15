# Dashboard V2 Promotion / V1 Retirement — Entry Baseline

Captured 2026-08-15 before the promotion edits.

- Branch: `branch/owner-form-simple-dashboard`
- HEAD and remote HEAD: `e3b488f122ea82b15e7572e8be375e165c3207c7`
- Working tree: only the pre-existing `mock-systems/excel/permit_tracker.xlsx` modification; it is preserved and not staged.
- Local Alembic: SQLite fallback has no initialized `alembic_version`; migration graph head is `0058_source_intake_ledger`.
- Deployed backend: `https://amec-permits-ops-backend.vercel.app/health` reports PostgreSQL, `0058_source_intake_ledger`, synthetic-only mode, and release SHA `e3b488f122ea82b15e7572e8be375e165c3207c7`.
- Deployed frontend: current production browser proof still showed the pre-promotion split; promotion deployment is required.
- Frontend routes before promotion: `/dashboard` simplified mode, `/dashboard-v2` governance mode, `/dashboard/inputs-go-live`, and `/dashboard-v2/inputs-go-live`.
- Canonical data: `MasterContentItem → Document → DocumentVersion → configured binary store`; Source Intake uses the same promotion path.

The supplied FORME package is treated as read-only audit evidence. It is not re-imported for this task.
