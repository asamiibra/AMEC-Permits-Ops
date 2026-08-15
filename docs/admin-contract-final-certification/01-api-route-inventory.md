# API Route Inventory

The current route surface is implemented in `backend/app/api/contract_workspace_routers.py`, the Administration routers, billing routers, handover routers, and shared master-content/dashboard routers. The certification exercised the route families rather than treating a UI label as proof: `/api/admin/contracts`, `/api/admin/contracts/{id}`, history, authority, accept, client-fields, documents, download, commercial terms, inputs, deliverables, activate-project, billing-context; `/api/billing/*`; `/api/handover/*`; `/api/dashboard-v2/*`; `/api/master-content/*`; `/api/projects/*`; `/api/my-work`, `/api/issues/*`, `/api/notifications/*`, and `/api/audit`.

Read paths return typed controlled errors and browser surfaces preserve retry/context. Write paths are role-checked, revision-scoped where required, audited, and use idempotency or append-only semantics where the domain requires it. The full backend run found no route failures.

