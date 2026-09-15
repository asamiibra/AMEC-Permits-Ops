from backend.app.ai.contract_skills import CONTRACT_SKILL_REGISTRY_VERSION, contract_skill_catalogue


def test_contract_skill_catalogue_is_governed_and_zero_authority():
    payload = contract_skill_catalogue(contract_id="contract-1", role="SYSTEM_ADMIN")

    assert payload["architecture"]["registry_version"] == CONTRACT_SKILL_REGISTRY_VERSION
    assert payload["catalogue_state"] == "RELEASED"
    assert payload["execution_state"] == "EXECUTABLE_WHEN_ELIGIBLE"
    assert payload["eligibility_state"] == "CONTEXT_INELIGIBLE"
    assert payload["runtime"]["real_content_allowed"] is False
    assert payload["runtime"]["external_inference_enabled"] is False
    assert payload["runtime"]["runtime_ready"] is False
    assert len(payload["skills"]) == 11
    assert {skill["skill_id"] for skill in payload["skills"]} == {
        "contract.document-understand",
        "contract.compare-to-proposal",
        "contract.compare-to-po-lpo",
        "contract.revision-impact",
        "contract.executed-copy-review",
        "contract.review-brief",
        "contract.payment-terms-extract",
        "contract.deliverables-extract",
        "contract.client-inputs-extract",
        "contract.communication-draft",
        "contract.operations-brief",
    }
    assert all(skill["human_review_required"] is True for skill in payload["skills"])
    assert all(skill["status"] == "CONTEXT_INELIGIBLE" for skill in payload["skills"])
    assert all(skill["runtime_state"] == "EXECUTABLE_WHEN_ELIGIBLE" for skill in payload["skills"])
    assert all(skill["runtime_ready"] is False for skill in payload["skills"])
    assert all(skill["canonical_write_authority"] == "NONE" for skill in payload["skills"])
    assert all(skill["protected_action_authority"] == "NONE" for skill in payload["skills"])
    assert all(skill["advisory_only"] is True for skill in payload["skills"])
    assert {skill["skill_id"]: skill["required_context"] for skill in payload["skills"]} == {
        "contract.document-understand": ["current_revision"],
        "contract.compare-to-proposal": ["current_revision", "accepted_proposal_revision"],
        "contract.compare-to-po-lpo": ["current_revision", "po_or_lpo_document"],
        "contract.revision-impact": ["at_least_two_revisions"],
        "contract.executed-copy-review": ["accepted_revision", "executed_copy_candidate"],
        "contract.review-brief": ["current_revision"],
        "contract.payment-terms-extract": ["commercial_document"],
        "contract.deliverables-extract": ["commercial_document"],
        "contract.client-inputs-extract": ["commercial_document"],
        "contract.communication-draft": ["missing_document_workflow"],
        "contract.operations-brief": ["operations_context"],
    }
