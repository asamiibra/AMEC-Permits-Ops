# Content Library Step 3 — Retrieval quality and consumer inventory

This evidence record is synthetic/repository-only. It does not read or write
AMEC data, Synology, Azure, Azure SQL, or an external retrieval service.

## Contracts and executable path

There are two intentionally separate read contracts:

| Concern | Canonical implementation | Current consumer path |
| --- | --- | --- |
| Master Content discovery | `canonical_master_content_read()` in `backend/app/services/master_content.py` | Dashboard, Admin, Step-2 `contentLibraryApi`, Proposal/Contract template resolvers |
| Cross-domain evidence retrieval | `RetrievalQuery` → `governed_retrieve()` → `GovernedRetrievalEnvelope` in `backend/app/services/governed_retrieval.py` | `/api/retrieval/query`, `/api/retrieval/answer`, Dashboard `GovernedDiscovery` |

The cross-domain path is: consumer → retrieval API/service → immutable access
context → canonical SQL rows → source/version/evidence lineage → deterministic
match rank → governed envelope → exact citation. No retrieval document or
search index is persisted.

## Consumer inventory

| Consumer | Classification | Decision/evidence |
| --- | --- | --- |
| Dashboard master-content lists and filters | `CURRENT_READ_CONSUMER` | Uses the Step-2 canonical discovery service; no duplicate query path added. |
| Dashboard cross-domain search | `CURRENT_READ_CONSUMER` | Uses `/api/retrieval/query`; receives domain, verification/currentness, relationship, and citation fields. |
| Proposal template/checklist and Engineering references | `CURRENT_READ_CONSUMER` | Uses `master_content_purpose()` / canonical current item and version projections. No project evidence is mixed into template truth. |
| Proposal definitions | `CURRENT_READ_CONSUMER` | Uses current canonical DefinitionEntry/DefinitionRevision projections. |
| Contract template snapshot | `CURRENT_WRITE_CONSUMER` | Resolves the canonical Admin Contract Template, then records a downstream version/hash snapshot; it does not copy canonical content as a new truth. Protected Contract commands remain authoritative. |
| Permit / Preparation-Submission | `CURRENT_READ_CONSUMER` | Current executable seam reads FormInstance and project evidence projections. No separate Master Content search implementation exists; recorded `NO_CURRENT_CONSUMER_TO_CONNECT` for an additional adapter. Final submission remains human-only. |
| Engineering advisory/review | `CURRENT_AI_ADVISORY_CONSUMER` | Existing bounded advisory reads review/regulation/domain records and emits proposed comments; no new search engine or professional approval authority was added. Engineering Works/Definitions are available through the canonical contracts where a retrieval seam exists. |
| Synthetic answer seam | `CURRENT_AI_ADVISORY_CONSUMER` | Test/proof-only `answer_from_retrieval()`; deterministic evidence report, never protected action authority. |

No candidate was classified as a duplicate retrieval engine, protected action,
or legacy replacement requiring Step-3 wiring.

## Quality harness

`backend/tests/test_retrieval_quality_step3.py` builds an isolated synthetic
SQLite corpus containing Forms, Reports, Engineering Works, Definitions,
current and historical versions, provenance, observed/verified project facts,
restricted/needs-review/inactive records, bilingual labels, unauthorized
projects, and intentionally conflicting evidence. It evaluates Q1–Q16 as
separate golden query classes and asserts exact IDs, versions, citations,
authorization, ambiguity/conflict state, no fabricated result, and consumer
resolver parity.

The pre-change focused baseline passed the Step-1/Step-2 regression tests. The
quality-specific gaps were database-order ranking, absent Definition aliases,
and absent conflict/ambiguity state. Step 3 addresses only those observed
failures inside the existing governed retrieval service.

## Performance decision

The harness uses a bounded synthetic corpus and repeated in-process reads to
record corpus size, statement count, p50/p95, and a SQLite query plan. One
observed run recorded `corpus=57`, `statements=61` across five reads,
`p50=7.836ms`, `p95=8.239ms`, and an indexed canonical-reference plan using
`ix_master_content_items_ref`. Master-content candidates and project evidence
are batch-loaded separately; no per-master-candidate N+1 pattern was observed.
This is a comparative regression guard, not a production SLA certification. No
new table, retrieval state, migration, index, vector store, or external
infrastructure is introduced.
