from backend.app.services.golden_service_pack import candidate_golden_service_pack, validate_candidate_pack


def test_golden_service_candidate_is_complete_without_claiming_owner_selection():
    pack = candidate_golden_service_pack()
    result = validate_candidate_pack(pack)

    assert result["status"] == "PASS"
    assert pack["selected"] is False
    assert pack["production_approved"] is False
    assert pack["owner_dependent_fields"]
    assert pack["components"]["submission_boundary"]["machine_submit"] is False


def test_golden_service_validator_rejects_missing_components_and_inferred_approval():
    pack = candidate_golden_service_pack()
    pack["components"].pop("outputs")
    pack["production_approved"] = True
    result = validate_candidate_pack(pack)

    assert result["status"] == "FAIL"
    assert "outputs" in result["missing_components"]
    assert result["checks"]["production_approval_not_inferred"] is False
