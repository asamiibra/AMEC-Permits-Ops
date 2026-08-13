# API contract

Status: `IMPLEMENTED_AND_VERIFIED`

The router exposes project-scoped work-package, deliverable/revision/rendition, review/finding, professional approval, technical-check/calculation, material-test, baseline/manifest, and design-change routes under `/api/projects/{project_id}/engineering/...`.

Retries use idempotency for work packages and revisions; exact project, deliverable, revision, rendition, rule-set, and baseline membership checks reject cross-project references. Raw storage paths are not returned as API payloads.
