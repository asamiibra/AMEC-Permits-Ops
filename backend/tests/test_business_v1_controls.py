from backend.app.services.business_v1_controls import (
    advance_payment_gate,
    architecture_first_gate,
    commercial_reconciliation,
    maker_checker_gate,
    operations_control_projection,
    project_history_controls,
)


def test_commercial_reconciliation_blocks_lpo_variance_and_accepts_exact_terms():
    proposal = {"price": "QAR 250000", "currency": "QAR", "duration": "90 days", "scope_of_work": "Permit design"}
    contract = {"amount": "QAR 250000", "currency": "QAR", "duration": "90 days", "scope": "Permit design"}
    assert commercial_reconciliation(proposal, contract)["status"] == "PASS"
    mismatch = commercial_reconciliation(proposal, contract, {"amount": "QAR 250001", "currency": "QAR", "duration": "90 days", "scope": "Permit design"})
    assert mismatch["status"] == "BLOCKED"
    assert "amount" in mismatch["order_to_proposal"]["mismatches"]


def test_maker_checker_is_distinct_and_explicit():
    assert maker_checker_gate({"maker_checker": {"preparer": "prep", "checker": "check", "proposal_reconciled": True}}, enforce=True)["status"] == "PASS"
    blocked = maker_checker_gate({"maker_checker": {"preparer": "same", "checker": "same", "proposal_reconciled": False}}, enforce=True)
    assert blocked["status"] == "BLOCKED"
    assert "MAKER_CHECKER_MUST_BE_DISTINCT" in blocked["blockers"]


def test_advance_gate_fails_closed_only_when_enabled():
    assert advance_payment_gate({}, [])["status"] == "NOT_ASSERTED"
    blocked = advance_payment_gate({"required": True}, [])
    assert blocked["status"] == "BLOCKED"
    passed = advance_payment_gate({"required": True}, [{"source_role": "ADVANCE_PAYMENT", "status": "VERIFIED", "metadata": {"objective_bank_evidence": True}}])
    assert passed["status"] == "PASS"


def test_operations_projection_contains_each_owner_control_state():
    incomplete = operations_control_projection({"project_reference": "PRJ-1"})
    assert incomplete["status"] == "INCOMPLETE"
    complete = {key: "configured" for key in ("project_reference", "start_date", "expected_end_date", "stage", "blocker", "risk", "next_action", "schedule", "delay_state", "extension_state", "aged_missing_document_state", "invoice_due_state", "earned_not_invoiced_state")}
    assert operations_control_projection(complete)["status"] == "PASS"


def test_architecture_first_gate_blocks_uncoordinated_detailed_work():
    blocked = architecture_first_gate({"required": True, "architecture_revision": "A1"})
    assert blocked["status"] == "BLOCKED"
    passed = architecture_first_gate({"required": True, "architecture_revision": "A1", "structure_precoordination": "S1", "mep_precoordination": "M1", "safety_precoordination": "F1", "detailed_work_unlock": True})
    assert passed["status"] == "PASS"


def test_source11_history_controls_preserve_identity_roles_and_evidence():
    blocked = project_history_controls({"project_id": "P1", "owner_person_id": "P1", "owner_company_id": "P1"})
    assert blocked["status"] == "BLOCKED"
    passed = project_history_controls({"project_id": "P1", "owner_person_id": "PERSON-1", "owner_company_id": "COMPANY-1", "operational_contact_role": "FACILITY_MANAGER", "operational_contact_organization": "CLIENT-ORG", "contract_period": "90 days", "authority_period": "permit cycle", "case_history_events": ["event-1"], "technical_report_evidence_links": ["doc-1"], "authorization_evidence": ["poa-1"], "missing_document_contact_route": "contact-1", "location_context": {"plot": "1"}, "onboarding_cohort": ["P1"], "operational_actor_is_engineer": False})
    assert passed["status"] == "PASS"
