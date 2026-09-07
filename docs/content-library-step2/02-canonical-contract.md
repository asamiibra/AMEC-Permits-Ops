# Content Library Step 2 — Canonical Discovery Contract

All master-content reads converge on `canonical_master_content_read` in
`backend/app/services/master_content.py`. The Admin Forms route and Dashboard
v2 Forms route use that same service, so search, category/module/governance,
applicability, owner-status, detail, and history filters remain composable.

The response is a projection of one `MasterContentItem` and its current
`DocumentVersion`, with immutable versions available for history. Governance,
automation, and applicability fields are overlays; they do not create a
`DashboardContent` or other second persistence model.

Owner status is normalized to `CURRENT`, `NEEDS_REVIEW`, or `INACTIVE`.
Inactive items are discoverable through the explicit inactive filter. Basic
discovery is deterministic SQL-backed filtering and does not depend on AI,
embeddings, external search, or vector infrastructure.
