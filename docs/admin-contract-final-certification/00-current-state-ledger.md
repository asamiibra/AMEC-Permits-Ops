# Current State Ledger

Certification was run from the current `main` tree, not from a historical Administration SHA. The current implementation is software-complete for the tested synthetic scope and is frozen at this certification point. The native PostgreSQL run used `admin_contract_final_cert_20260815`, PostgreSQL 16.14, Alembic `0055_bd_proposal_final_hardening`, and the real Vite/uvicorn stack.

| Capability | Evidence | Classification | Remaining dependency | Software gap |
|---|---|---|---|---|
| Administration IA | `AdministrationOwner.tsx`; 7 owner browser checks; full browser suite | VERIFIED_BROWSER / CODE_FROZEN | Owner content only | None found |
| Contract register and lanes | `contract_workspace_routers.py`; owner session tests; browser register checks | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | None for synthetic policy | None found |
| Accepted Proposal → Contract | proposal/contract services and owner model tests | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | standalone-contract policy remains owner-owned | None found |
| Contract detail delta | `ContractPageDelta`; 2 browser checks; 32 targeted PG tests | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | Owner policy for LPO/PIN/content | None found |
| Revisions, authority, acceptance | Contract workspace routes and idempotency assertions | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | official authority policy | None found |
| Project Activation / ServiceEngagement | activation and closeout suites | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | project-code/start-date semantics | None found |
| Billing / invoices / receivables | billing full suite and Billing V2 browser check | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | official finance policy and external delivery | None found |
| Dashboard template lineage | Dashboard V2 and master-content browser checks | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | official templates/content | None found |
| RBAC / isolation / recovery | full backend plus browser persona and route matrix | VERIFIED_POSTGRESQL / VERIFIED_BROWSER | production identity provider | None found in tested scope |

Historical evidence remains historical: Admin reconciliation was local/browser verified and did not claim PostgreSQL; Contract-page delta was local/synthetic-real-stack verified and did not claim PostgreSQL.

