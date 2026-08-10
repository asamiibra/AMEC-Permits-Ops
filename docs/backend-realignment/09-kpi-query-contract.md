# KPI and list query contract

`KPI_PREDICATES` is the single registry for summary and list filters. The
canonical summary is `GET /api/proposals-contracts/summary`; list APIs are
`/api/proposals-contracts/proposals` and `/api/proposals-contracts/contracts`.
Filters `open`, `handover`, `in_process`, `needs_action`, `ready` and `closed`
use the same state sets as the six summary fields. Counts are computed from
all backend rows, never from a partial frontend page.
