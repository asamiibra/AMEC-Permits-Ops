from backend.tests.test_admin_contract_owner_session import headers


def test_billing_capabilities_are_server_projection_and_fail_closed_for_ai(client):
    owner = client.get("/api/billing/capabilities", headers=headers("OWNER_SPONSOR"))
    assert owner.status_code == 200, owner.text
    body = owner.json()
    assert body["authority_source"] == "SERVER_MUTATION_POLICY"
    assert body["capabilities"]["can_issue_invoice"] is True
    assert body["frontend_only_authority_grants"] == 0
    assert body["unresolved_owner_decisions"] == []
    assert body["resolved_owner_policies"]["FINANCE_YTD_REPORTING_YEAR_BOUNDARY"] == "CALENDAR_YEAR"

    engineer = client.get("/api/billing/capabilities", headers=headers("RESPONSIBLE_ENGINEER"))
    assert engineer.status_code == 200, engineer.text
    assert engineer.json()["capabilities"]["can_issue_invoice"] is False
    assert engineer.json()["capabilities"]["can_request_billable_stage"] is True


def test_billing_bounded_read_models_keep_invoice_and_receivable_history_separate(client):
    command = client.get("/api/billing/command-center", headers=headers("OWNER_SPONSOR"))
    assert command.status_code == 200, command.text
    assert command.json()["source_of_truth"] == "CANONICAL_BILLING_EVENTS"
    assert command.json()["system_insights_only"] is True
    assert command.json()["ai_assisted"] is False

    for path in ("/api/billing/plans", "/api/billing/milestones", "/api/billing/invoices", "/api/billing/receivables", "/api/billing/payments", "/api/billing/reports", "/api/billing/controls"):
        response = client.get(path, headers=headers("OWNER_SPONSOR"))
        assert response.status_code == 200, (path, response.text)

    reports = client.get("/api/billing/reports", headers=headers("OWNER_SPONSOR")).json()
    assert "invoice_report" in reports
    assert "open_receivables" in reports
    assert reports["ytd"] is None
    assert reports["ytd_status"] == "CONFIGURATION_REQUIRED"
    assert reports["ytd_policy"] == "CALENDAR_YEAR"


def test_billing_read_models_do_not_grant_mutation_to_engineering(client):
    response = client.get("/api/billing/command-center", headers=headers("RESPONSIBLE_ENGINEER"))
    assert response.status_code == 200, response.text
    forbidden = client.post("/api/billing/financial-accounts", headers=headers("RESPONSIBLE_ENGINEER"), json={"legal_entity_ref": "SYN", "account_name": "SYN"})
    assert forbidden.status_code == 403
