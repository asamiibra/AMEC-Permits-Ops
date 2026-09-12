# Original CM-G01..CM-G17 definitions

These meanings preserve the original Contract/Mobilization Owner program; the prior production-closure table is provenance, not a substitute acceptance namespace.

| ID | Original requirement / terminal predicate | Authority and persistence | Producers / consumers |
|---|---|---|---|
| CM-G01 | Review state is distinct from final Contract acceptance and execution. | Protected human authority; revision/audit state survives reopen. | Contract workspace; Project, Billing, Operations. |
| CM-G02 | Review authority and final Contract acceptance authority are independently governable. | Server capability decision and distinct audit events persist. | Contract API; owner workflow. |
| CM-G03 | Maker and checker are distinct authenticated actors. | Revision snapshot and audit persist. | Contract checker API; acceptance gate. |
| CM-G04 | Exact accepted Proposal, PO/LPO, and Contract commercial identity reconciles fail-closed. | Explicit outcome and source lineage persist. | Business control; Contract readiness. |
| CM-G05 | Executed Contract evidence is exact-revision, versioned, human-recorded, and idempotent. | Evidence row, hash, audit, and reopen read-back. | Executed-evidence API; activation/handoff. |
| CM-G06 | Client-copy distribution and Operations handoff are separate durable steps. | Prepared/delivered/received/accepted evidence and audit. | Handoff API; Operations projection. |
| CM-G07 | Contract-derived start prerequisites are source-derived, typed, traceable, and fail-closed when mandatory. | Read-only prerequisite projection persists source references. | Start-prerequisite gate; activation. |
| CM-G08 | Project Activation is a separate protected human action after exact Contract readiness. | Activation row, exact revision, audit, idempotency. | Activation API; Project. |
| CM-G09 | ServiceEngagement is canonical, exact Contract/Project/revision scoped, assigned, idempotent, and auditable. | Service row and audit survive reopen. | Handover/service APIs; closeout. |
| CM-G10 | Commercial, design, authority-submission, and service-execution readiness remain independent. | Criteria, dossier, evidence, authority, blockers are read back. | Readiness API; downstream work. |
| CM-G11 | Operations control is a canonical projection with dates, clock, risk, blockers, contacts, and billing signals. | Read-only projection from canonical rows. | Operations/API/UI. |
| CM-G12 | Event eligibility, invoice acceptance, invoice issue, and payment are separate. | Billing lineage, idempotency, audit, and human issue authority. | Billing; Operations. |
| CM-G13 | Original/current Contract periods, actual dates, amendments, authority/service periods, and extensions retain provenance. | Revision/amendment history persists. | Schedule and Operations. |
| CM-G14 | Handover, service closure, Contract administrative closure, finance, regulatory, and archive remain separate; Contract close has one canonical predicate. | Closure rows and audit; all negative prerequisites block. | Handover close service; Contract API. |
| CM-G15 | Where required, governed Form master/version binds to Contract/Service context, human review/authorization, delivery, and audit; checklist remains a Form. | Exact FormVersion pin persists. | Forms and Contract. |
| CM-G16 | Operational contacts are purpose-specific, current, verified, scoped, and never generic-mobile fallback. | Assignment/history and routing audit persist. | Contact resolver; missing-document work. |
| CM-G17 | DocumentVersion references require authorized current Contract/revision, accepted Proposal, or governed-master lineage; no cross-scope leakage. | Exact version and lineage survive reopen. | Payment terms, deliverables, client inputs, evidence. |

Original source provenance: `docs/module-assurance/contract-mobilization-production-closure/01-final-gap-rescore.md`, `08-document-escalation.md`, `09-contract-clock-and-operations.md`, `10-billing-readiness.md`, `11-handover-and-close.md`, and the executable Contract/Handover tests on the baseline commit.
