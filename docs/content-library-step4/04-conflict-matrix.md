# Deployment-lineage conflict matrix

The matrix compares semantic surfaces without modifying either lane.

| Surface | Classification | Future rule |
| --- | --- | --- |
| `backend/app/main.py` and API router registration | `MANUAL_INTEGRATION_REQUIRED` | retain Azure auth/readiness wiring and apply Step 1–3 routes explicitly |
| `master_content_routers.py`, `dashboard_v2_routers.py` | `CONTENT_LIBRARY_SUPERSEDES_ONLY_IN_SCOPE` | preserve canonical discovery behavior; re-check Azure dependencies |
| `master_content.py`, `source_intake.py`, `governed_retrieval.py` | `CONTENT_LIBRARY_SUPERSEDES_ONLY_IN_SCOPE` | carry canonical lineage, citations, ranking, and access semantics |
| models and migration metadata | `COMPATIBLE_BOTH_REQUIRED` | preserve Azure schema/runtime migration head; Step 3 adds no migration |
| `backend/app/auth/*`, settings, DB/session | `DEPLOYMENT_LINEAGE_MUST_GOVERN` | Azure managed identity, Entra, SQL, and environment behavior wins |
| health/readiness, storage, Docker/build/IaC | `DEPLOYMENT_LINEAGE_MUST_GOVERN` | use accepted deployed contract; do not transplant local assumptions |
| Dashboard, Master Content UI, API client | `CONTENT_LIBRARY_SUPERSEDES_ONLY_IN_SCOPE` | preserve current UI behavior and Azure auth/bootstrap/build behavior |
| Proposal/Contract/Permit/Engineering seams | `COMPATIBLE_BOTH_REQUIRED` | preserve protected domain commands and canonical content/evidence IDs |

`MANUAL_INTEGRATION_REQUIRED_COUNT=8` and
`UNKNOWN_CONFLICT_COUNT=0`. No conflict is resolved by blindly selecting ours
or theirs. The integration target and exact function-level patch must be chosen
after the Azure lane supplies its accepted immutable baseline.
