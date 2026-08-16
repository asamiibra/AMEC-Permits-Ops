# Admin system boundary

The Admin landing surface is now explicitly system administration:

- Users & Access and role/capability visibility
- Notification rules and follow-up defaults
- Reference, numbering, template, and policy configuration
- Integrations, storage/connectivity, and integration health
- Environment/readiness and Inputs & Go-Live
- System security, retention, audit, and diagnostics

The landing page renders a system boundary statement and configuration controls. It no longer loads Contract registers, Invoice registers, Project Activation workspaces, business record previews, or operational billing data.

The Admin Contract Configuration page is configuration-only. References to Contract or Invoice numbering are retained as legitimate system configuration; record creation, revision, activation, invoice issue, receivable, and payment work are not Admin capabilities.

The notification inbox remains `/notifications`; Admin owns notification rules/defaults, not notification records. Business record history remains with Contract & Mobilization or Finance; Admin exposes system activity only.
