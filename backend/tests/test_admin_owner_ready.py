"""Owner-facing Administration projection and authorization coverage."""

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, ConfigurationArtifact


def test_owner_admin_landing_reclassifies_internal_console(client):
    response = client.get("/api/admin/summary", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200
    payload = response.json()
    labels = {item["label"] for item in payload["categories"]}
    assert {"People & Access", "Data & Connections", "Project & Folder Setup", "Proposal Setup", "Contract Setup", "Permit Workflow Setup", "Templates & Documents", "Notifications & Follow-up", "Data, Security & Retention", "Integration Health", "Audit History", "Advanced Diagnostics"} <= labels
    assert not labels.intersection({"Expansion foundation", "RAID log", "Tier 1 decisions", "Tier 2 backlog", "Test extraction", "Business case"})
    assert payload["go_live"]["route"] == "/admin/go-live-readiness"


def test_global_admin_is_denied_to_bd_and_engineering(client):
    for role in ("COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"):
        assert client.get("/api/admin/summary", headers={"X-Dev-Role": role}).status_code == 403
        assert client.get("/api/admin/users", headers={"X-Dev-Role": role}).status_code == 403


def test_admin_connections_are_safe_and_testable(client):
    response = client.get("/api/admin/connections", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["connections"]
    assert all("password" not in str(item).lower() and "token" not in str(item).lower() for item in payload["connections"])
    assert all(item["status"] in {"Simulator Ready", "Simulator Check Failed"} for item in payload["connections"])
    assert all(item["production_status"] == "Production Not Connected" for item in payload["connections"])
    tested = client.post("/api/admin/connections/test", headers={"X-Dev-Role": "SYSTEM_ADMIN"}, json={"name": payload["connections"][0]["name"]})
    assert tested.status_code == 200
    assert tested.json()["tested_at"]


def test_bounded_admin_setting_persists_and_audits(client):
    response = client.put("/api/admin/notifications/follow-up", headers={"X-Dev-Role": "SYSTEM_ADMIN"}, json={"follow_up_hours": 36})
    assert response.status_code == 200
    with SessionLocal() as db:
        item = db.query(ConfigurationArtifact).filter(ConfigurationArtifact.stable_id == "ADMIN_RUNTIME_SETTINGS:AMEC").one()
        assert item.semantic_payload_json["follow_up_hours"] == 36
        assert db.query(AuditEvent).filter(AuditEvent.event_type == "ADMIN_CONFIGURATION_UPDATED", AuditEvent.entity_id == item.id).count() == 1
    refreshed = client.get("/api/admin/notifications", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert refreshed.status_code == 200
    assert refreshed.json()["settings"]["follow_up_hours"] == 36


def test_owner_admin_projections_use_business_terms_and_share_runtime_truth(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    for route in ["users", "project-setup", "proposal-setup", "contract-setup", "permit-setup", "templates", "notifications", "security", "integration-health", "audit", "advanced-diagnostics"]:
        response = client.get(f"/api/admin/{route}", headers=headers)
        assert response.status_code == 200, (route, response.text)
    users = client.get("/api/admin/users", headers=headers).json()
    assert users["permissions"]
    assert "persona" not in str(users).lower()
    permit = client.get("/api/admin/permit-setup", headers=headers).json()
    assert permit["requirements"]
    assert "SUBMIT" not in str(permit["municipality"]).upper()
    contract = client.get("/api/admin/contract-setup", headers=headers).json()
    assert "existing downstream Permit" not in contract["permit_readiness"]
    security = client.get("/api/admin/security", headers=headers).json()
    assert security["secrets"]["exposed"] is False
    assert all(isinstance(item, dict) for item in [security["environment"], security["mfa"], security["backup_recovery"]])
