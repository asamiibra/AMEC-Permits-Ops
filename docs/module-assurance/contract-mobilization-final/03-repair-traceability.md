# Repair traceability

| Defect | Repair | Executable evidence |
|---|---|---|
| CM-G02 | Replaced the common capability with independently assignable `CONTRACT_REVIEW_AUTHORITY`, `CONTRACT_ACCEPT_AUTHORITY`, `CONTRACT_EXECUTION_EVIDENCE`, and `CONTRACT_HANDOFF`; review and acceptance routes emit distinct events. Retired the legacy recovery approval/execution endpoints with an explicit canonical-workspace response so they cannot form a second authority path. | `test_cm_g02_review_and_acceptance_capabilities_are_independently_governable`; `test_legacy_contract_approval_and_execution_surfaces_cannot_bypass_canonical_workspace`; existing authority/acceptance flow tests. |
| CM-G04 | Added explicit `BLOCKED_MISSING_SOURCE`, `BLOCKED_UNSTRUCTURED_SOURCE`, `BLOCKED_AMBIGUOUS_SOURCE`, `MISMATCH`, `NOT_APPLICABLE_WITH_REASON`, and source-state outcomes. Readiness selects only current PO/LPO sources and requires explicit applicability/reason. | `test_cm_g04_explicit_order_outcomes_fail_closed`; `test_business_v1_controls.py`; Contract reconciliation flow. |
| CM-G14 | Generic stage closure now requires close capability and rejects with `CONTRACT_ADMIN_CLOSE_CANONICAL_REQUIRED`; a single `contract_administrative_close()` service enforces service closure, handover receipt/ack, exact revision, executed evidence, idempotency, and audit. | `test_cm_g14_generic_stage_cannot_create_contract_closure`; Handover closeout tests. |
| CM-G17 | Added purpose-aware current/scoped lineage validation for Contract evidence, accepted Proposal source links, and governed current master content, including Contract/client/project scope checks. | `test_cm_g17_source_bindings_require_current_scoped_lineage`; existing exact-document tests. |

No migration was added: the repair uses existing columns and tables.
