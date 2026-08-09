# Workflow-first UX refactor entry audit

Baseline observed in `frontend/src/App.tsx`: 31 architecture-led sidebar entries, Dashboard as the landing page, and a large reconciliation/control surface embedded in the landing page. Operator work was split across Projects, Documents, Conflicts, Package, Municipality, Findings, Lineage, Attachments, and implementation-wave pages.

The refactor keeps the domain/control services and APIs unchanged while projecting them into My Work, Permits, Reviews, Issues, Notifications, permit workspaces, and privileged Administration. The normal operator shell no longer exposes implementation-wave labels.

No satisfaction or productivity metric is fabricated. The only measured click-path improvement is structural: a preparer can resume from My Work, open a permit, and land on the projected current stage/next action without discovering an internal module.
