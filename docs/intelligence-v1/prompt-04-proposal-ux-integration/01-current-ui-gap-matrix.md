# Current Proposal UI gap matrix

This matrix is based on the live code in `frontend/src/App.tsx`, `BDProposalOwnerSession.tsx`, `ProposalWorkspaceStageAware.tsx`, `ProposalsContracts.tsx`, and the existing Proposal API routes. It records the current surface and the P04 disposition.

| Concept | Current route/component | Current support/state | Owner requirement | Intelligence relevance | Disposition |
| --- | --- | --- | --- | --- | --- |
| Proposal register | `/opportunities`, `BDProposalOwnerSession.tsx` | Backend register exists; visible as legacy Intake & Opportunity table | Proposal-centric worklist with next action and attention | Future read projection | REDESIGN |
| New Proposal | `/opportunities/new`, monolith workbench | Generic form plus optional upload | Source-first intake | Candidate source observations only | REDESIGN |
| Proposal detail | `/opportunities/:id`, `BDProposalOwnerSession.tsx` → `ProposalWorkspaceStageAware` | Large lifecycle page with mixed stages | Stage-aware workspace | Contextual outputs only | REDESIGN |
| Canonical `/proposals` routes | `/proposals*` currently maps to `ProposalsContractsPage` | Route collision | One canonical Proposal UI | Shared route adapter | ADD |
| Legacy routes | `/bd`, `/bd/proposals`, `/opportunities*` | Independent/ambiguous mappings | Compatibility without duplicate UI | None | MOVE |
| Primary navigation | `App.tsx` | “Intake & Opportunity” | “Proposals” | None | REDESIGN |
| Client and contact | Workbench fields/forms v2 | Persisted through existing endpoints | Client context and Proposal contact | Evidence lineage where present | KEEP/REDESIGN |
| Source evidence | Presence cards and upload controls | `ProposalSourceEvidence`, links, documents | Actual records, currentness, provenance | Candidate/verified boundaries | REDESIGN |
| Site/property | Workbench fields and site context | Existing backend support | Explicit area basis and site evidence | Candidate observations only | REDESIGN |
| Notes/conversations | Inline note list | Human notes persisted | Chronological human context | Not documentary truth | KEEP/REDESIGN |
| Unknowns/conflicts | Inline lists | Existing hardening records | Distinct, material, prominent | Context dependency | KEEP/REDESIGN |
| Intake readiness | Readiness panel | Backend deterministic readiness | Exact blockers and Proceed action | AI cannot decide | REDESIGN |
| Engineering preparation | Mixed monolith section | Existing field patch and handoff endpoint | Technical scope, assessment, confirmation | Evidence/context view | REDESIGN |
| Service eligibility | Opaque service code input | Existing protected endpoint | Governed service choice/reason | Canonical decision distinct from AI | REDESIGN |
| Commercial review | “Review / Authority” and config panels | Existing validation, templates, checklist | Business-facing content and acceptance | Consistency output when real | REDESIGN |
| Proposal acceptance | Generic `Accept Proposal` | Backend human authority | Exact revision confirmation | No AI authority | REDESIGN |
| Commercial release | Protected controls panel | Existing endpoint | Authorize exact accepted revision | No AI authority | REDESIGN |
| Distribution | Evidence textbox | Existing endpoint | Channel, recipient, timestamp, evidence | Citation/evidence surface | REDESIGN |
| Client response | Inline form | Existing endpoint and revision path | Accepted/rejected/change requested distinction | Evidence summary only | REDESIGN |
| Acceptance verification | Evidence textbox | Existing endpoint | Human verification against released revision | No AI authority | REDESIGN |
| LPO reconciliation | Free-text variance | Existing deterministic result | Structured comparison and revision path | Candidate comparison later | REDESIGN |
| Contract handoff | Preview/record controls | Existing eligibility and handoff endpoint | Preflight, no Contract/Project mutation | Recommendation beside gate only | REDESIGN |
| History | Audit-first rows and IDs | Existing stage/revision data | Business timeline with details secondary | AI history separate | REDESIGN |
| Intelligence UI | None in Proposal workspace | Shared P01–P03 contracts exist; no Proposal skill | Truthful empty state and future renderer | Candidate/current/stale/invalid/citations | ADD |
| Global Content Library | Dashboard configuration panel | Read-only configuration projection | View canonical masters, no edit | Master context only | REDESIGN |
| Client List | Combined legacy surface | Existing legacy action | Master reconciliation, not Proposal creation | None | MOVE |
| Proposal Form | Combined legacy action | Legacy context | Attach to eligible Proposal | Evidence record | MOVE |
| Contract Form | Combined legacy action | Legacy context | Contract module ownership | None | MOVE |
| Responsive behavior | Shared dashboard styles | Existing general layout | 1440/1024/390 useful journeys | None | REDESIGN |
| Accessibility | Existing app-wide checks | Partial | Keyboard, labelled controls, dialogs, Axe | None | REDESIGN |

Canonical active Proposal UI after P04: one feature package under `frontend/src/features/proposals/`. Legacy Proposal routes are adapters to that package; the combined Contract surface remains available only for Contract-owned behavior.
