# Phase 4 — Security and access proof

The proof checks authorization before content assembly:

| Caller | Scope | Expected |
|---|---|---|
| Synthetic Owner | Master and project fixture | Allowed |
| Synthetic Permit Preparer | Explicitly assigned project | Allowed for master module and project evidence |
| Synthetic unauthorized caller | No project membership | No transactional retrieval context |
| Synthetic wrong-project query | Different project ID | No transactional retrieval context |

Master role/module access follows the existing `used_in`/Owner semantics.
The HTTP adapter does not trust a browser-supplied project membership claim;
production authentication must populate `RetrievalAccessContext` from the
existing trusted RBAC boundary.

`ACCESS_ISOLATION_PASS=1`

`UNAUTHORIZED_RETRIEVAL_CONTEXT_COUNT=0`
