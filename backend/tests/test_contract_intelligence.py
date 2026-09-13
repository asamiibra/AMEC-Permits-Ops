from backend.app.ai.contract_skills import CONTRACT_SKILL_REGISTRY_VERSION, contract_skill_catalogue


def test_contract_skill_catalogue_is_governed_and_zero_authority():
    payload = contract_skill_catalogue(contract_id="contract-1", role="SYSTEM_ADMIN")

    assert payload["architecture"]["registry_version"] == CONTRACT_SKILL_REGISTRY_VERSION
    assert payload["runtime"]["real_content_allowed"] is False
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
    assert all(skill["canonical_write_authority"] == "ZERO" for skill in payload["skills"])
    assert all(skill["protected_action_authority"] == "ZERO" for skill in payload["skills"])
    assert all(skill["human_review_required"] is True for skill in payload["skills"])
    assert all(skill["status"] == "DISABLED_BY_POLICY" for skill in payload["skills"])
    assert all(skill["release_state"] == "RELEASED_FOR_CATALOGUE_ONLY" for skill in payload["skills"])
    assert all(skill["input_schema"]["contract_id"] == "string" for skill in payload["skills"])
    assert all(skill["output_schema"]["findings"] == "array of advisory candidates" for skill in payload["skills"])
    assert all(skill["allowed_tools"] == [] for skill in payload["skills"])
    assert all(skill["model_policy"] == "NO_MODEL_INVOCATION_WHILE_DISABLED_BY_POLICY" for skill in payload["skills"])
    assert all(skill["evaluation_suite_version"] == "CONTRACT-INTELLIGENCE-EVAL-1.0" for skill in payload["skills"])
