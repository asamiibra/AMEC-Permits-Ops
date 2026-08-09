# E1 exit gate

`READY_FOR_EXPANSION_GATE_E2`

## Governance

- A12: 20 unique rows, preserved and passing.
- A12B: 40 unique owner-session rows, passing.
- A15: 18 unique controlled clarifications with safe defaults, passing.
- Four assistant IDs exactly; no fifth autonomous assistant.
- Stage 2 disposition state is typed and remains `UNDECIDED_STAGE2`; no owner or production approval is claimed.

## Domain

The shared AMEC foundation exists for opportunity/RFQ/tender, client account/contact, quotation/revision/terms/approval, contract/revision/milestone/approval, checklist/document requests, reference/project administration, communication draft/approval/delivery, invoice/revision/milestone/approval/finance handoff, project handover, engineering review/run/regulation/applicability/comment/drawing cycle, templates/rendered artifacts, and assistant capability metadata.

Shared `DocumentVersion`, `EvidenceArtifact`, `Approval`, `WorkflowTask`, `NotificationEvent`, `AuditEvent`, `LineageEdge`, `MaterialChangeEvent`, `TargetRenderingRule`, and `DocumentValidity` controls are reused. No assistant-specific authoritative stores were added.

## Fixture

Successor `PermitOps_Synthetic_MVP_Dataset_v1` v1.2.0 records predecessor v1.1.1 and manifest hash `b91e8377a06ffa96733a66361b3228b1114c7f4a7a687a198cce65fc22d436b7`. It includes eight source families and three coherent scenarios, while the original permit cases remain authoritative for permit regressions.

## Runtime evidence

The generated expansion regression artifact reports PASS for SQLite, PostgreSQL 16, clean migration/seed, canonical fixture, Golden Paths v1/v2, focused E0/E1 tests, frontend tests/build, browser E2E, and safety. The PostgreSQL E1 migration was also downgraded to `0015_week14_acceptance` and re-upgraded to `0016_stage1_v2_6_expansion_foundation` successfully.

## Deferred boundary

E2+ remains responsible for quotation generation/release, client acceptance runtime, contract workflow, document-request sending, expanded Excel writes, engineering AI/retrieval/adjudication, invoice workflow, finance operations, handover release, real Outlook/Teams, accounting writes, authority integration, autosend, and new government automation.
