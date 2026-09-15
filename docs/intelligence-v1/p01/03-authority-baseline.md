# Prompt 01 — Authority and Non-Promotion Baseline

This certification records the authority boundaries present at the canonical baseline. Evidence is code and existing tests only; no runtime behavior was changed.

## Distinctions certified

| Boundary | Existing evidence | Result |
|---|---|---|
| AI candidate ≠ human-verified business truth | `classifier_v2.classify_document()` returns `classification_proposal.currentness=CANDIDATE_ONLY`, `review_required=true`, `auto_promotion_allowed=false`, `projection_allowed=false`, and `current_assertion_mutation=false`. `FieldObservation` is separate from `VerifiedAssertion`; the latter records `verified_by`, method, and authority rule. | PRESERVED |
| Workflow accountability ≠ professional authority | `WorkflowTask` carries owner/user/role and task-family context; engineering review routes separately enforce engineering capabilities and dispositions. `test_e5_e6_bounded_workflows.py` denies admin/AI engineering approval paths. | PRESERVED |
| Review ≠ external release | Phase 4 review decisions, proposal distribution/release, contract acceptance, invoice evidence, and handover release are separate records/commands. | PRESERVED |
| Proposal analysis ≠ proposal acceptance | Proposal services require an accepted revision, human scope/eligibility/release controls, client acceptance verification, and evidence before handoff. | PRESERVED |
| Contract analysis ≠ contract acceptance | Contract workspace acceptance is a protected domain command with maker/checker, executed evidence, current revision, and capability prerequisites. Tests assert direct acceptance and same-actor checker failures. | PRESERVED |
| Commercial eligibility ≠ invoice issue | `commercial_contract_controls.evaluate_client_delay_commercial_handover_eligibility()` returns eligibility only and explicitly sets `ai_autonomous_invoice_issue_authority=false`, `invoice_issued=false`, and `human_authorization_required=true`. `test_e5_e6_bounded_workflows.py` separately requires finance review and evidence. | PRESERVED |
| Evidence intake ≠ `VerifiedAssertion` | `bridge_intake.ingest_bridge_package()` creates `Document`, `DocumentVersion`, source/evidence/classification, and `FieldObservation`; its audit payload explicitly reports `verified_assertion_created=false` and `projection_created=false`. | PRESERVED |
| `VerifiedAssertion` ≠ protected domain action | Phase 4 has separate promotion/projection operations; projections create review work and state that protected actions remain blocked. Proposal, contract, engineering, billing, and handover commands remain separate capability-gated domain transitions. | PRESERVED |

## Specific seam proofs

1. Classifier output remains candidate/proposal-only: `backend/app/services/classifier_v2.py:90-149` and `backend/tests/test_phase5_classifier.py` cover bounded proposals, contradictions, synthetic-only references, no auto-promotion, and no projection.
2. Bridge intake does not directly create `VerifiedAssertion` or a typed projection: `backend/app/services/bridge_intake.py:187-322` creates a `DocumentVersion`, evidence/classification, and `FieldObservation`; the audit record captures both prohibited creations as false. `backend/tests/test_g10_bridge_transport.py` exercises the transport and negative boundary.
3. Master Content consumers fail closed on currentness/ambiguity: `backend/app/services/master_content.py:363-490` selects only governed/current candidates and returns `RESOLVED`, `AMBIGUOUS`, or `UNRESOLVED`; `backend/tests/test_content_library_step3_consumer_resolution.py` and `backend/tests/test_content_library_gap_closure.py` cover ambiguity and currentness failures.
4. Proposal protected transitions remain module/domain commands: `proposal_commercial_controls.py:137-254` requires current accepted revision, current scope, no active staleness, eligibility, distribution, client acceptance, and LPO reconciliation before release/handoff. `backend/tests/test_proposal_commercial_controls.py` and proposal owner-session tests cover the negative matrix.
5. Billing commercial control exposes eligibility while keeping autonomous invoice/handover authority false: `commercial_contract_controls.py:52-116` returns a projection with human authorization required and autonomous protected authority false. `backend/tests/test_e5_e6_bounded_workflows.py:95-154` verifies finance decision, issue/payment evidence, and handover approval are separate.
6. Protected capability enforcement is server-side: `backend/app/services/backend_realignment.py` owns `CAPABILITY_MATRIX` and `require_capability`; `backend/tests/test_api_auth_boundary.py` requires guarded application routes and `backend/tests/test_admin_contract_owner_session.py` checks independent capabilities and protected transition failures.

## Non-promotion rule for Intelligence v1

Future Intelligence v1 work may produce `CANDIDATE`, `ANALYSIS`, `DRAFT`, or `RECOMMENDATION` outputs and may suggest a reviewer or next action. It must not promote an observation, decide a module acceptance, mutate canonical domain state, issue/verify payment, authorize external release, or exercise professional/protected authority. Module commands and authorized human review remain the only promotion path.
