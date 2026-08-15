# BD / Proposal Stage 1 — History and Current State

## Entry evidence

- Branch: `main`
- Entry SHA: `01b5c3dd19a515fa88e791175f83611511e988a6`
- `origin/main`: `01b5c3dd19a515fa88e791175f83611511e988a6`
- Entry tree: pre-existing user changes were present; they are preserved and excluded from this reconciliation unless directly required.
- Alembic head/current: `0053_handover_admin_closeout`
- Evidence: current models, routers, services, frontend routes, tests, migrations, and history (`0e8c0ee`, `e28df4e`, `bcc5061`).

## Generation reconstruction

| Concept | First/current evidence | Current meaning and authority | Classification | Action |
|---|---|---|---|---|
| Opportunity / Opportunity Reference | `opportunities` table; legacy expansion routers; `Opportunity.opportunity_reference` | Storage-compatible Proposal aggregate and provisional/context reference | supporting context / compatibility | REHOME |
| Quotation / Quotation Revision | `quotations`, `quotation_revisions`, `commercial_terms`, approval/release entities | Historical commercial lineage and Contract compatibility; not the primary new Proposal UX | historical / compatibility | HIDE_FROM_PRIMARY_UX, PRESERVE_HISTORY |
| Quotation candidate values | `QuotationFieldObservation` | Candidate → verified → approved commercial observation path | historical mechanism | ADAPT |
| Commercial approval / release | quotation approval/release entities and current Proposal human Accept | Human-controlled commercial authority | canonical control principle; two generations coexist | ADAPT |
| Client response / acceptance evidence | legacy `ClientResponse` bound to quotation revision; current Proposal routes preserve response boundary | External response must bind to exact released/accepted revision | canonical boundary | REHOME |
| Proposal / Proposal Reference | `Opportunity` plus Proposal projection and `/api/bd/proposals` | One Proposal identity across BD, Engineering, client response, and Contract | current canonical UX/domain projection | KEEP |
| Proposal Revision / Accepted Proposal Revision | `ProposalAcceptedRevision`, immutable snapshots | Exact accepted commercial baseline | canonical | KEEP |
| Tender Email | `ProposalSourceEvidence.source_type=TENDER_EMAIL`, `RFQ` legacy table | Incoming source evidence; candidate extraction is not fact | canonical source family | KEEP |
| Tender Document | `TENDER_DOCUMENT`, `TenderDocument`, `DocumentVersion` | Versioned incoming tender/RFQ/client brief evidence | canonical source family | KEEP |
| Tender Photo / Image | `TENDER_PHOTO` → `TENDER_IMAGE_SOURCE` | Incoming image evidence, separate from site photo | canonical source family | RESTORE / KEEP |
| Client Information | `CLIENT_DATA` → `CLIENT_SOURCE`; ClientAccount/Party link | Capture/link client context without replacing Client master truth | canonical source family | KEEP |
| Client List | master/client import surfaces | Client master reconciliation, not Proposal intake | separate capability | HIDE_FROM_PRIMARY_UX |
| Proposal Form | governed master content and Engineering preparation | Existing Proposal/technical preparation artifact | rehomed capability | REHOME |
| Contract Form | governed Contract/admin surfaces | Eligible Contract context only | downstream capability | REHOME |
| Project / Site Photo | shared document/source model plus site context | Physical/site context, not tender evidence | canonical separate context | RESTORE / KEEP |
| Manual / Call / Meeting Notes | current AMEC Input JSON only; no typed note entity found | Human-entered source context with provenance | gap to implement without false authority | ADAPT |
| AMEC Input | `proposal_fields_json.amec_input` and Forms v2 projection | Human internal input, separate from source evidence | canonical control boundary | KEEP |
| Proceed | No current typed command found; Proposal API has CRUD/Accept/Handoff | Required explicit Intake → Engineering transition | missing lifecycle command | IMPLEMENT |
| Engineering Proposal Preparation | `/proposals/{id}/preparation`, `engineering-ready` route | Engineering-owned technical preparation | current canonical workflow | KEEP |
| Engineering → BD handoff | `engineering-ready` route and current Proposal main service | Controlled return to BD commercial review | current canonical workflow | KEEP / ADAPT |
| BD Commercial Review | Proposal revision + human Accept controls; legacy `COMMERCIAL_REVIEW` status | Human review of current Proposal revision | canonical | KEEP / REHOME |
| Proposal Accept | `/api/bd/proposals/{id}/accept` | AMEC acceptance of an exact revision; not client acceptance or Contract execution | canonical | KEEP |
| Proposal Release | legacy quotation release; current outputs are accepted-revision-bound | Controlled external release remains human-owned | canonical boundary | ADAPT |
| Ready for Contract / Contract Handoff | accepted revision → Contract service and `/handoff/contract` | Exact accepted revision becomes Contract baseline; no Project/Permit creation | canonical boundary | KEEP / RENAME |

## Current defect conclusion

The `/bd` frontend is the stale Opportunity workspace (`frontend/src/Opportunities.tsx`). It exposes `RFQ & Sources`, `Quotation`, `Contract & Setup`, raw owner identifiers, and a static first-step highlight. The mature implementation is the Proposal API plus Forms-driven v2 surfaces (`frontend/src/BDProposalOwnerSession.tsx`, `backend/app/api/bd_proposal_routers.py`, `backend/app/services/bd_proposal_forms_v2.py`). The safe repair is a Proposal-first compatibility view over the existing aggregate, with explicit source-entry/readiness/Proceed semantics and preserved historical entities.
