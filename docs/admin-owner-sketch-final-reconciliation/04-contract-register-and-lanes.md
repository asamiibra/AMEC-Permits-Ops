# Contract register and lanes

The register uses `/api/admin/contracts` with `filter=ALL|NEEDS_ACTION|AUTHORITY_REVIEW|READY_CLOSE` and `q` search. Each lane count is the response count for that same backend predicate; the UI does not count a partial client page. `Need Action` is readiness/blocker-derived. `Authority Review` is Contract authority, not government authority. `Ready / Close` is a derived operational lane and is not equivalent to Project activation, financial settlement, or archive.
