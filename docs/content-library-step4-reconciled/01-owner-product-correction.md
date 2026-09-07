# Owner product correction

The Owner Dashboard is the simple `AMEC · CONTENT LIBRARY` surface:

- Forms
- Reports
- Engineering Works
- Definitions

Search and filters call the canonical master-content and definition APIs. The
Dashboard does not call `/api/retrieval/query`, does not show transactional
evidence, and does not expose governance/debug terminology. Current, Needs
Review, Inactive, Open, Modify/Edit, History, Upload New Version, Used In,
current source/version, simple details, and Inputs & Go-Live remain available.

Governed retrieval remains preserved for downstream governed assist and
evidence use cases. Form preparation and draft Apply live only in the
AuthorityCase workspace, not in the master-management Dashboard.
