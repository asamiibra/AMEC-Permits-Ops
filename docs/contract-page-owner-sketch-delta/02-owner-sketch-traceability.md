# Owner-Sketch Traceability

| Owner element | Implementation | Evidence |
|---|---|---|
| Client Document | `Document` + `DocumentVersion` + `ContractAdminEvidence`, current/history/read-back | Contract detail payload and focused backend test |
| LPO | Same versioned seam, separate `LPO` source role and policy state | Contract detail payload and download test |
| Client Name / Company / CR / Mobile / PIN / Email | Explicit field cards with source badges and prospective revision edits | `client_fields`, `field_lineage`, focused backend/browser tests |
| Field lineage | Canonical Client/Contact or accepted Proposal fallback; Contract revision divergence is explicit | `source`, `source_label`, `diverged`, snapshot/read-only fields |
| Accept Contract | Owner-only current-revision command, readiness guarded, audited, idempotent | `POST /accept`, `ACCEPTED`/`ALREADY_ACCEPTED` test |
| Documents & Sources | Compact six-entry source panel | `source_panel` payload and browser assertion |
| Documents Needed | `ContractClientInputRequirement`, separate from regulatory requirements | `documents_needed` and existing add route |
| Deliverables | `ContractDeliverableCommitment`, separate from engineering deliverables | `deliverable_commitments` and existing add route |
| Project Activation / Invoice | Remain separate actions; acceptance creates neither | acceptance test and visible page boundary copy |
