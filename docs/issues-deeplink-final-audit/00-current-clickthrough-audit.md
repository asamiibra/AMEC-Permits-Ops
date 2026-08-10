# Current clickthrough audit

The Issues homepage is a routing and context surface. It does not open dedicated Issue Detail pages. Each canonical Finding-backed Issue now deep-links to the existing Proposal, Contract, or Permit workspace with `issue=<canonical_issue_id>`.

The five owner-demo paths are Proposal Technical, Proposal Commercial, Contract, Permit Technical, and Authority. The target fetches entity state and focus context from the backend, so refresh, copied URLs, back, and forward do not depend on the prior list object.

Evidence: `artifacts/issues-deeplink-final-audit/issue-route-matrix.json`, `browser-result.json`.
