# Proposals Main typed contract

`ProposalMainResponse` is the backend response model. The frontend validates required arrays, KPI objects, row fields, persona metadata, and lineage before rendering. Incomplete, null, wrong-type, 500, and non-JSON responses produce a controlled error with Retry; no malformed response becomes fake zero or an empty register.
