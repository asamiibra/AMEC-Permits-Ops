# Historical Branch Census and Reconciliation

Remote census was performed against origin immediately before this closure review.

HISTORICAL_CONTENT_LIBRARY_BRANCH_COUNT=18
HISTORICAL_BRANCHES_RECONCILED=18
HISTORICAL_UNIQUE_COMMITS=21
HISTORICAL_MISSING_RELEVANT_CHANGES=0

## Branch census

| Branch | Tip | Merge base with BASE_SHA | Relationship | Unique branch commits | Unique base commits |
|---|---|---|---|---:|---:|
| branch/content-library-consumer-convergence-v1 | 3555e35 | fde6eb9 | DIVERGED | 5 | 293 |
| branch/content-library-dashboard-convergence-v1 | d8445c9 | fde6eb9 | DIVERGED | 4 | 293 |
| branch/content-library-dashboard-discovery-convergence-v1 | 6004e85 | fde6eb9 | DIVERGED | 4 | 293 |
| branch/content-library-dashboard-discovery-v1 | 3ed290c | fde6eb9 | DIVERGED | 4 | 293 |
| branch/content-library-governed-prefill-provenance-r1 | da63553 | fde6eb9 | DIVERGED | 7 | 293 |
| branch/content-library-governed-prefill-v1 | 3740ad6 | fde6eb9 | DIVERGED | 6 | 293 |
| branch/content-library-lineage-governance-consumer-reconciled-v1 | 534e525 | fde6eb9 | DIVERGED | 6 | 293 |
| branch/content-library-owner-product-correction-v1 | 254c1dd | fde6eb9 | DIVERGED | 5 | 293 |
| branch/content-library-retrieval-quality-consumers-v1 | 46934d0 | fde6eb9 | DIVERGED | 5 | 293 |
| branch/content-library-retrieval-quality-step3-reconciled-v1 | 13137e8 | fde6eb9 | DIVERGED | 5 | 293 |
| branch/content-library-step3-consumer-resolution-v1 | 3b556fd | fde6eb9 | DIVERGED | 5 | 293 |
| branch/content-library-step4-commissioning-prep-v1 | 90fa78f | fde6eb9 | DIVERGED | 6 | 293 |
| branch/content-library-step4-draft-apply-v1 | ade765f | fde6eb9 | DIVERGED | 8 | 293 |
| branch/content-library-step4-governed-apply-reconciled-v1 | 1c0e9fc | fde6eb9 | DIVERGED | 7 | 293 |
| branch/content-library-step5-azure-integration-v1 | d8610b1 | d8610b1 | ANCESTOR | 0 | 96 |
| branch/content-library-step5-azure-preprod-integration-v1 | f329a38 | 5a5c9f7 | DIVERGED | 1 | 94 |
| branch/content-library-step5-owner-purpose-ui-hotfix-v1 | efb1fc0 | 5a5c9f7 | DIVERGED | 1 | 94 |
| branch/content-library-step5-owner-purpose-ui-hotfix-v2 | c76266b | 5a5c9f7 | DIVERGED | 2 | 94 |

Unique branch-commit counts are per branch; the 21 count is the union of unique SHAs, not their sum.

## Unique commit reconciliation

| SHA | Subject | Classification | Reconciliation |
|---|---|---|---|
| 0dd403f | fix(azure-p0): harden v2.5 commissioning preauthorization gates | UNSAFE_TO_REINTRODUCE | deployment/commissioning context; not module source |
| 13137e8 | reconcile content library retrieval quality step 3 | ALREADY_INTEGRATED_SEMANTICALLY | current retrieval/currentness tests |
| 1b14f83 | feat(content-library): converge dashboard reads and discovery | ALREADY_INTEGRATED_SEMANTICALLY | current Dashboard/library implementation |
| 1c0e9fc | feat: reconcile content library governed draft apply | SUPERSEDED | current architecture keeps project apply outside library |
| 254c1dd | Correct Owner content library product surface | ALREADY_INTEGRATED_SEMANTICALLY | current Owner UI |
| 3555e35 | feat(content-library): converge deterministic workflow consumers | ALREADY_INTEGRATED_SEMANTICALLY | canonical resolver seam |
| 3740ad6 | Add governed AuthorityCase prefill preview | ALREADY_INTEGRATED_SEMANTICALLY | governed prefill/source18 seam |
| 3b556fd | feat: close governed consumer resolution | ALREADY_INTEGRATED_SEMANTICALLY | current consumer resolution |
| 3ed290c | feat(content-library): close dashboard discovery convergence | ALREADY_INTEGRATED_SEMANTICALLY | current discovery |
| 46934d0 | Close content library retrieval quality step 3 | ALREADY_INTEGRATED_SEMANTICALLY | retrieval quality evidence |
| 534e525 | close content library lineage governance and consumers | ALREADY_INTEGRATED_SEMANTICALLY | current lineage/consumer evidence |
| 6004e85 | feat: converge canonical content library discovery | ALREADY_INTEGRATED_SEMANTICALLY | current discovery |
| 686ddbf | fix(retrieval): isolate canonical reference fixtures | TEST_ONLY | fixture hygiene only |
| 90fa78f | Prepare content library deployed synthetic commissioning | HISTORICAL_EXPERIMENT_ONLY | synthetic commissioning path, no production authority |
| ade765f | add governed FormInstance draft apply | SUPERSEDED | project draft/apply is not library truth |
| c76266b | Expose canonical Administration Contract Template purpose in Owner UI | ALREADY_INTEGRATED_SEMANTICALLY | current Admin resolver |
| d8445c9 | feat(content-library): converge dashboard reads and discovery | ALREADY_INTEGRATED_SEMANTICALLY | current Dashboard/library |
| d913f62 | feat(retrieval): establish governed canonical domain envelope | ALREADY_INTEGRATED_SEMANTICALLY | current retrieval envelope |
| da63553 | fix governed prefill field provenance | ALREADY_INTEGRATED_SEMANTICALLY | current provenance tests |
| efb1fc0 | fix(content-library): expose Owner purpose bindings | ALREADY_INTEGRATED_SEMANTICALLY | current purpose bindings |
| f329a38 | fix(migrations): commit shared-connection upgrade transaction | UNSAFE_TO_REINTRODUCE | historical migration path; no new migration authorized |

No historical behavior classified STILL_RELEVANT_AND_MISSING or UNKNOWN_REQUIRES_REVIEW. No branch was merged, rewritten, deleted, renamed, or used as a development base.
