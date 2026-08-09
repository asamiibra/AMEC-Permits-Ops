# E5/E6 owner requirement traceability

| Requirement | Stage 2 disposition | Implementation/evidence | Status |
|---|---|---|---|
| OWN-NEW-16 | UNDECIDED_STAGE2 | ContractRevision → InvoiceRevision lineage; E6 focused test | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-17 | UNDECIDED_STAGE2 | Invoice/FinanceEvidence and follow-up projection | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-18 | UNDECIDED_STAGE2 | Generic Finance Handoff / WorkflowTask | PASS_WITH_SAFE_DEFAULT |
| OWN-NEW-19 | UNDECIDED_STAGE2 | InvoiceRequiredDecision and evidence-separated statuses | PASS_WITH_SAFE_DEFAULT |
| OWN-NEW-20 | UNDECIDED_STAGE2 | Invoice draft/render + HUMAN_SEND communication | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-26 | UNDECIDED_STAGE2 | Deterministic handover readiness/form/approval/release | PASS_WITH_SAFE_DEFAULT |
| OWN-NEW-27 | UNDECIDED_STAGE2 | Drawing input/version pinning and engineering review | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-28 | UNDECIDED_STAGE2 | Controlled NFPA/Qatar source/version metadata | PASS_WITH_SAFE_DEFAULT |
| OWN-NEW-29 | UNDECIDED_STAGE2 | Authorized Engineer boundary | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-30 | UNDECIDED_STAGE2 | Compliance Review Sheet | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-31 | UNDECIDED_STAGE2 | Numbered Comment Sheet and block-time projection | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |
| OWN-NEW-32 | UNDECIDED_STAGE2 | Drawing V2 invalidation and re-review | PASS_AT_SYNTHETIC_IMPLEMENTATION_DEPTH |

APIs are in `backend/app/api/e5_e6_routers.py`, UI is `frontend/src/EngineeringCloseout.tsx`, focused evidence is `backend/tests/test_e5_e6_bounded_workflows.py`, and the Golden Paths are under `artifacts/expansion/`. No ambiguous owner label is treated as signed authority.
