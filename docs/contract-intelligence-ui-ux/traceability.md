# Contract Intelligence UI/UX traceability

This feature preserves the canonical Contract services and adds projections and a governed, zero-authority Intelligence registry. The source trace below is intentionally a coverage map; source-native IDs and exact locators remain authoritative in the preserved Source 1–18 reconciliation artifacts.

| Owner source | Contract-relevant requirement family | CM coverage | UI surface | Canonical producer / test | Result |
|---|---|---|---|---|---|
| Sources 1–3 | Proposal origin, client context, commercial baseline | CM01, CM07 | Overview, Contract & Sources, Commercial | Contract read model; existing Contract API suite | CROSS_MODULE_PASS |
| Sources 4–6 | Revision, template, maker/checker, authority review | CM02–CM05 | Review & Acceptance, History | Contract revision/authority/checker endpoints; existing owner hardening tests | PASS |
| Sources 7–9 | Executed evidence, client delivery, contacts | CM06, CM17 | Contract & Sources, Review & Acceptance, Operations & Billing | DocumentVersion and evidence endpoints; existing Contract tests | PASS |
| Source 10 | Proposal / PO-LPO reconciliation and Contract controls | CM01, CM05, CM07 | Commercial | `commercial_contract_controls` and readiness projection; existing regression | PASS |
| Source 11 | Mobilization, advance gate, Project Activation | CM09–CM12 | Mobilization | Readiness and activation endpoints; existing activation tests | PASS |
| Sources 12–14 | Finance boundary, service scope, downstream handoff | CM12–CM16 | Operations & Billing | Billing, ServiceEngagement, and Handover owning routes | CROSS_MODULE_PASS |
| Sources 15–16 | Forms, authorizations, operational responsibilities | CM15, CM17 | Contract & Sources, Operations & Billing | Canonical Content Library and contact projections | CROSS_MODULE_PASS |
| Source 17 | Engineering Module 1 Contract obligations | CM01–CM17 | All workspace groups | Preserved reconciliation plus typed workspace projections | PASS |
| Source 18 | Engineering Module 2 final Contract obligations | CM01–CM17 | All workspace groups | Preserved source18 reconciliation and current Contract services | PASS |

## AI governance

The registry is exposed by `GET /api/admin/contracts/{contract_id}/intelligence`. All catalogue entries declare `canonical_write_authority=ZERO`, `protected_action_authority=ZERO`, and `human_review_required=true`. With the current runtime flags, the API returns `DISABLED_BY_POLICY`; no fake result, document content, external model call, or canonical write is generated.

Synology remains a classification/routing hint into canonical DocumentVersion lineage. The Contract Intelligence layer never reads a source solely because a browser supplied an ID.
