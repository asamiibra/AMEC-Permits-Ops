# b47 → current-main semantic delta disposition

Base is current protected `main` `594b313a15cc6ade3f0505de395a5817c6337268`
(tree `73d6781640bc774b577a6eb8e938868ef3fb83c3`). Reference is
`next/module-integration` b47 `b47f33369d5a9f8daca42564c2eab6212948c8ed`
(tree `5e366d3bc4b286363e9257f1fec66c0f22bfeec1`). The disposition is based on
file-level comparison and current-main behavior, not on wholesale branch
merging.

| b47 delta | disposition | rationale against current main |
|---|---|---|
| `backend/app/services/source18_form_projection.py` | `REPLAY_SEMANTIC_FIX` | Current main has no typed Source18 projection; official-form authority would otherwise remain mixed with ordinary Content Library. |
| Source18 projection API additions in `master_content_routers.py` | `REPLAY_SEMANTIC_FIX` | Current main has no Source18-owned read-only listing/resolver. |
| Source18 exact-currentness checks in `source18.py` | `REPLAY_SEMANTIC_FIX` | Current main only checks metadata currentness in the relevant path; exact source, document pointer, supersession, and approval must remain required. |
| Source18 official-form promotion checks in `source18_routers.py` | `REPLAY_SEMANTIC_FIX` | Current main can accept a non-Source18 DocumentVersion and does not bind the document current pointer. |
| whole-document-lineage guard in `master_content.py` | `REPLAY_SEMANTIC_FIX` | Current main has no central Source18 history guard; moving a pointer could otherwise reopen mutation. |
| ordinary resolver external-authority exclusion | `REPLAY_SEMANTIC_FIX` | Current main ordinary resolver does not exclude Source18/external authority classes. |
| consumer resolution matrix | `REPLAY_SEMANTIC_FIX` | Current main consumers do not expose one explicit deterministic resolution matrix. |
| FORME synthetic fixture reclassification | `REPLAY_SEMANTIC_FIX` | Current main treats synthetic reference-package official numbers as external official; Source18 must remain the official authority. |
| Source18 synthetic owner-demo fixture | `REPLAY_SEMANTIC_FIX` | Current main seed has no complete synthetic Source18 transaction → case → exact DocumentVersion path for acceptance. |
| Source18 persisted authority regression tests | `REPLAY_SEMANTIC_FIX` | Current main needs adversarial proof of exact identity/currentness and no mutation. |
| Content Library projection/browser acceptance tests | `REPLAY_SEMANTIC_FIX` | Current main lacks exact projection/hash/currentness browser coverage. |
| historical acceptance files changed on b47 | `REJECT` | Historical bytes are immutable provenance; do not replay changes to current-main closure. |
| `docs/integration/*` acceptance/evidence additions | `EVIDENCE_ONLY` | Carry only after being recomputed for the closure candidate; never copy stale exact-head claims. |
| b47 `baseline_phase4_v36_azure_sql.py` bytes | `MAIN_WINS` | Current-main SQL parameter typing is a later accepted migration correction; preserve hash `b705b19d…`. |
| b47 `source18_regulatory_current_state_v1.py` index name | `MAIN_WINS` | Current-main index name is later accepted migration history; preserve hash `c46642ca…`. |
| `source18_committee_implementation_v1.py` | `MAIN_WINS` | Byte-identical on main and b47; no change required. |
| `step5_content_library_azure_sql_v2.py` | `MAIN_WINS` | Byte-identical on main and b47; no change required. |
| b47 frontend Content Library UI changes | `REPLAY_SEMANTIC_FIX` | Current main retains the integrated UI but not all exact Source18 projection contract; replay only verified UI contract pieces. |
| b47 universal UI generated artifacts | `EVIDENCE_ONLY` | Recompute against closure branch; old hashes do not qualify new source. |
| b47 unrelated billing/proposal/contract deletions and edits | `REJECT` | Current main contains later accepted work and is the release base; no wholesale rollback or import. |
| b47 unrelated migration deletions | `REJECT` | Main-only migration lineage is protected. |
| b47 unrelated test edits | `TEST_ONLY` | Reuse only where a test directly covers a replayed semantic fix; preserve current-main tests otherwise. |

## Required forward-port rule

Only rows marked `REPLAY_SEMANTIC_FIX`, `FORWARD_REPAIR`, `EVIDENCE_ONLY`, or
directly relevant `TEST_ONLY` may change the closure branch. Every replayed code
change must be requalified on the closure branch. No historical migration is
rewritten; any schema change must be a new migration descending from the live
head `17c6ebd99c4a`.
