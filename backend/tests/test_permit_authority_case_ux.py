from backend.app.db import SessionLocal
from backend.app.models import AuthorityCase, Project, RegulatoryJourney


def test_owner_permit_ux_portfolio_and_empty_workspace_contract(client):
    portfolio = client.get("/api/permit-ux/portfolio", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert portfolio.status_code == 200, portfolio.text
    payload = portfolio.json()
    assert {"items", "total", "lanes"}.issubset(payload)
    if payload["items"]:
        item = payload["items"][0]
        assert item["permit_identifier"] is None or "value" in item["permit_identifier"]
        assert item["end_date"] is None
        workspace = client.get(f"/api/permit-ux/cases/{item['case_id']}", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
        assert workspace.status_code == 200, workspace.text
        assert "project_details" in workspace.json()


def test_non_member_cannot_deep_link_permit_case(client):
    with SessionLocal() as db:
        row = db.query(AuthorityCase, RegulatoryJourney, Project).join(RegulatoryJourney, RegulatoryJourney.id == AuthorityCase.regulatory_journey_id).join(Project, Project.id == RegulatoryJourney.project_id).first()
    if not row:
        return
    case = row[0]
    response = client.get(f"/api/permit-ux/cases/{case.id}", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER", "X-Dev-Actor": "unassigned-engineer"})
    assert response.status_code == 404
