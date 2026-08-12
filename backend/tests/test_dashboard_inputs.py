from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, DashboardInputItem


REQUIRED_KEYS = {
    "DASHBOARD_CATEGORY_TAXONOMY",
    "DASHBOARD_CATEGORY_SEMANTICS",
    "DASHBOARD_REFERENCE_NUMBERING",
    "DASHBOARD_ENGINEERING_SOURCE_TYPES",
    "DASHBOARD_ENGINEERING_DISCIPLINES",
    "DASHBOARD_FORM_REFERENCE_POLICY",
    "DASHBOARD_REPORT_REFERENCE_POLICY",
    "DASHBOARD_ENGINEERING_REFERENCE_POLICY",
    "DASHBOARD_DEFINITION_REFERENCE_POLICY",
    "DASHBOARD_MODULE_USAGE_POLICY",
    "DASHBOARD_ENGINEERING_ACTIVATION_POLICY",
    "DASHBOARD_REPORT_SCOPE_POLICY",
    "DASHBOARD_MASTER_WRITE_PERMISSIONS",
    "DASHBOARD_OFFICIAL_PROPOSAL_TEMPLATE",
    "DASHBOARD_OFFICIAL_PROPOSAL_CHECKLIST",
    "DASHBOARD_OFFICIAL_CONTRACT_TEMPLATE",
    "DASHBOARD_FORMS_CONTENT_READINESS",
    "DASHBOARD_REPORTS_CONTENT_READINESS",
    "DASHBOARD_ENGINEERING_CONTENT_READINESS",
    "DASHBOARD_DEFINITIONS_CONTENT_READINESS",
    "DASHBOARD_SYNOLOGY_CONNECTION",
    "DASHBOARD_FILE_POLICY",
    "DASHBOARD_DEFINITION_ARABIC_ALIASES",
}


def test_dashboard_inputs_are_persistent_and_context_specific(client):
    first = client.get("/api/dashboard-inputs")
    assert first.status_code == 200
    payload = first.json()
    assert {item["key"] for item in payload["items"]} == REQUIRED_KEYS
    assert payload["summary"]["technical_remaining"] == 1
    assert any(item["current"].get("patterns") == ["F-0001", "R-0001", "E-0001", "D-0001"] for item in payload["items"] if item["key"] == "DASHBOARD_REFERENCE_NUMBERING")
    definitions = next(item for item in payload["items"] if item["key"] == "DASHBOARD_DEFINITIONS_CONTENT_READINESS")
    assert definitions["current"]["confirmed_production"] == 0

    second = client.get("/api/dashboard-inputs").json()
    assert len(second["items"]) == len(payload["items"])
    with SessionLocal() as db:
        assert db.scalar(select(func.count(DashboardInputItem.id)).where(DashboardInputItem.context_key == "DASHBOARD_MASTER_CONTENT")) == len(REQUIRED_KEYS)

    changed = client.patch("/api/dashboard-inputs/DASHBOARD_REFERENCE_NUMBERING", json={"action": "confirm"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert changed.status_code == 200
    assert changed.json()["status"] == "CONFIRMED"
    persisted = client.get("/api/dashboard-inputs").json()
    assert next(item for item in persisted["items"] if item["key"] == "DASHBOARD_REFERENCE_NUMBERING")["status"] == "CONFIRMED"
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.entity_type == "DashboardInputItem")) >= 1


def test_dashboard_inputs_owner_boundary(client):
    assert client.patch("/api/dashboard-inputs/DASHBOARD_FILE_POLICY", json={"action": "confirm"}, headers={"X-Dev-Role": "COMMERCIAL_APPROVER"}).status_code == 403
    assert client.patch("/api/dashboard-inputs/DASHBOARD_FILE_POLICY", json={"action": "confirm"}, headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}).status_code == 403
    assert client.patch("/api/dashboard-inputs/DASHBOARD_SYNOLOGY_CONNECTION", json={"action": "confirm"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"}).status_code == 409
